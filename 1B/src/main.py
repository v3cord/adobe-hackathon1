import fitz  # PyMuPDF
import json
import time
import os
import statistics
import re
from collections import defaultdict
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# --- 1. Load the pre-trained model from a local directory ---
MODEL_PATH = './models/all-MiniLM-L6-v2'
print(f"Loading sentence-transformer model from: {MODEL_PATH}")
MODEL = SentenceTransformer(MODEL_PATH)
print("Model loaded successfully.")

# --- Final Parser with Intelligent Section Merging ---
def parse_documents(doc_paths):
    all_sections = []
    INSTRUCTION_VERBS = {'mix', 'combine', 'add', 'serve', 'preheat', 'cook', 'sauté', 'stir', 'bake', 'roast', 'garnish', 'drain', 'rinse', 'set', 'layer', 'top', 'spread', 'roll', 'place'}

    for doc_path in doc_paths:
        doc_name = os.path.basename(doc_path)
        try:
            doc = fitz.open(doc_path)
        except Exception as e:
            print(f"--> [Warning] Could not open or read '{doc_name}'. Skipping. Error: {e}")
            continue

        print(f"Analyzing layout for: {doc_name}")
        style_counts = defaultdict(int)
        for page in doc:
            for b in page.get_text("dict")["blocks"]:
                if b['type'] == 0:
                    for l in b['lines']:
                        for s in l['spans']:
                            style = (round(s['size']), s['font'])
                            style_counts[style] += len(s['text'].strip())
        
        if not style_counts: continue
        body_style = max(style_counts, key=style_counts.get)
        
        # --- NEW LOGIC: Process document as a continuous stream ---
        current_text = ""
        current_title = f"{doc_name} - Introduction" # A default for the very first section if no header is found
        start_page = 1

        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if b['type'] == 0:
                    for l in b['lines']:
                        if not l['spans']: continue
                        line_text = "".join(s['text'] for s in l['spans']).strip()
                        if not line_text: continue
                        
                        span = l['spans'][0]
                        line_style = (round(span['size']), span['font'])
                        
                        is_stylistically_different = (line_style != body_style)
                        first_word = line_text.split(' ')[0].lower()
                        is_instruction = first_word in INSTRUCTION_VERBS
                        is_list_item = re.match(r'^\s*([o•*✓-]|[a-zA-Z0-9][.)])\s+', line_text)
                        is_ingredient = re.match(r'^\s*([0-9½¼¾⅓⅔⅛⅜⅝⅞]|one|two|three)\s+', line_text.lower())
                        has_enough_words = len(line_text.split()) > 1
                        
                        # Check if the line is a header
                        if is_stylistically_different and has_enough_words and not is_instruction and not is_list_item and not is_ingredient:
                            # If a header is found, save the previous section...
                            if current_text.strip():
                                all_sections.append({"document": doc_name, "page_number": start_page, "section_title": current_title, "text": current_text.strip()})
                            
                            # ...and start a new one.
                            current_title = line_text.replace('\n', ' ').strip()
                            current_text = ""
                            start_page = page_num + 1
                        else:
                            # If not a header, it's body text. Append it to the current section.
                            current_text += line_text + "\n"
        
        # Add the very last section being built
        if current_text.strip():
            all_sections.append({"document": doc_name, "page_number": start_page, "section_title": current_title, "text": current_text.strip()})
    
    return all_sections

def get_refined_text(section_text, query_embedding, num_sentences=5):
    sentences = []
    for line in section_text.split('\n'):
        sentences.extend(s.strip() for s in line.split('.') if s.strip())
    if not sentences: return section_text.replace('\n', ' ').strip()[:1000]
    sentence_embeddings = MODEL.encode(sentences)
    similarities = cosine_similarity(query_embedding, sentence_embeddings)[0]
    top_indices = np.argsort(similarities)[-num_sentences:][::-1]
    top_indices.sort()
    refined_text = " ".join([sentences[i] for i in top_indices])
    return refined_text.replace('\n', ' ').strip()

def clean_text(text):
    return text.replace('\u00e9', 'e') # remove 'é'

def process_collection(collection_dir):
    start_time = time.time()
    input_json_path = os.path.join(collection_dir, "challenge1b_input.json")
    if not os.path.exists(input_json_path):
        print(f"--> [ERROR] Skipping '{os.path.basename(collection_dir)}'. Reason: 'challenge1b_input.json' file not found.")
        return
    pdfs_dir = os.path.join(collection_dir, "PDFs")
    if not os.path.isdir(pdfs_dir):
        print(f"--> [ERROR] Skipping '{os.path.basename(collection_dir)}'. Reason: 'PDFs' subfolder not found.")
        return

    with open(input_json_path, 'r') as f:
        input_data = json.load(f)
    
    persona = input_data["persona"]["role"]
    job_to_be_done = input_data["job_to_be_done"]["task"]
    contextual_query = (f"An expert {persona} needs to accomplish the following task: {job_to_be_done}. To do this, they are looking for the most relevant sections...")
    print(f"Generated Contextual Query: {contextual_query}")

    doc_paths = [os.path.join(pdfs_dir, f) for f in os.listdir(pdfs_dir) if f.lower().endswith(".pdf")]
    all_sections = parse_documents(doc_paths)
    if not all_sections:
        print("--> [Warning] No text could be extracted from any valid PDFs in this collection.")
        return

    print("Generating embeddings and ranking...")
    query_embedding = MODEL.encode([contextual_query])
    section_texts = [sec["text"] for sec in all_sections]
    section_titles = [sec["section_title"] for sec in all_sections]
    content_embeddings = MODEL.encode(section_texts)
    title_embeddings = MODEL.encode(section_titles)
    content_similarities = cosine_similarity(query_embedding, content_embeddings)[0]
    title_similarities = cosine_similarity(query_embedding, title_embeddings)[0]
    
    CONTENT_WEIGHT, TITLE_WEIGHT, FILENAME_BOOST = 0.75, 0.25, 0.1
    job_keywords = set(re.findall(r'\w+', job_to_be_done.lower()))
    for i, sec in enumerate(all_sections):
        title_score = title_similarities[i]
        boost = 0
        if any(keyword in sec['document'].lower() for keyword in job_keywords):
            boost = FILENAME_BOOST
        sec["similarity"] = (CONTENT_WEIGHT * content_similarities[i]) + (TITLE_WEIGHT * title_score) + boost

    ranked_sections = sorted(all_sections, key=lambda x: x["similarity"], reverse=True)
    
    job_lower = job_to_be_done.lower()
    exclusion_keywords = []
    if "vegetarian" in job_lower or "vegan" in job_lower:
        print("Applying vegetarian/vegan exclusion filter...")
        exclusion_keywords.extend(['beef', 'chicken', 'turkey', 'pork', 'fish', 'lamb', 'sausage', 'bacon', 'tuna', 'salmon', 'ham', 'shrimp', 'crab', 'lobster', 'meatball', 'mince'])
    if "gluten-free" in job_lower:
        print("Applying gluten-free exclusion filter...")
        exclusion_keywords.extend(['wheat', 'flour', 'bread', 'pasta', 'noodle', 'barley', 'rye', 'couscous', 'semolina', 'tortilla', 'croutons'])
    
    if exclusion_keywords:
        filtered_sections = []
        for section in ranked_sections:
            section_content_lower = (section['section_title'] + ' ' + section['text']).lower()
            if not any(keyword in section_content_lower for keyword in exclusion_keywords):
                filtered_sections.append(section)
        ranked_sections = filtered_sections

    for i, sec in enumerate(ranked_sections):
        sec["importance_rank"] = i + 1

    output_data = {
        "metadata": {"input_documents": [os.path.basename(p) for p in doc_paths if os.path.exists(p)], "persona": input_data["persona"], "job_to_be_done": input_data["job_to_be_done"], "processing_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        "extracted_sections": [],
        "sub_section_analysis": []
    }
    for sec in ranked_sections[:20]:
        output_data["extracted_sections"].append({"document": clean_text(sec["document"]), "page_number": sec["page_number"], "section_title": clean_text(sec["section_title"]), "importance_rank": sec["importance_rank"]})
    top_n_sections = 5
    for sec in ranked_sections[:top_n_sections]:
        refined_text = get_refined_text(sec["text"], query_embedding)
        output_data["sub_section_analysis"].append({"document": clean_text(sec["document"]), "section_title": clean_text(sec["section_title"]), "refined_text": clean_text(refined_text), "page_number": sec["page_number"]})

    collection_name = os.path.basename(collection_dir)
    output_dir = os.path.join("app", "output", collection_name)
    os.makedirs(output_dir, exist_ok=True)
    output_filename = os.path.join(output_dir, "challenge1b_output.json")
    with open(output_filename, "w", encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"\nProcessing complete in {time.time() - start_time:.2f} seconds.")
    print(f"Output saved to {output_filename}")

def main():
    base_input_dir = "app/input"
    print(f"Scanning for collections in '{base_input_dir}'...")
    try:
        collection_dirs = [os.path.join(base_input_dir, d) for d in os.listdir(base_input_dir) if os.path.isdir(os.path.join(base_input_dir, d))]
    except FileNotFoundError:
        print(f"--> [FATAL] Input directory not found at '{base_input_dir}'. Please create it.")
        return
    if not collection_dirs:
        print("No collections found to process.")
        return

    print(f"Found {len(collection_dirs)} collections: {[os.path.basename(d) for d in collection_dirs]}")
    for collection_path in collection_dirs:
        print(f"\n--- Starting processing for: {os.path.basename(collection_path)} ---")
        process_collection(collection_path)
        print(f"--- Finished processing for: {os.path.basename(collection_path)} ---")

if __name__ == "__main__":
    main()