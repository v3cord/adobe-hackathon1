import fitz  # PyMuPDF
import json
import os
import re
from collections import Counter

def detect_language(doc):
    """
    Detects if the document is primarily CJK or Latin-based.
    This is a simple, offline heuristic.
    """
    cjk_chars = 0
    total_chars = 0
    # Sample the first few pages for efficiency
    for page_num in range(min(len(doc), 3)):
        text = doc[page_num].get_text("text")
        if not text:
            continue
        for char in text:
            total_chars += 1
            # Check for CJK character ranges (Unified Ideographs, Hiragana, Katakana)
            if '\u4e00' <= char <= '\u9fff' or \
               '\u3040' <= char <= '\u309f' or \
               '\u30a0' <= char <= '\u30ff':
                cjk_chars += 1
    
    if total_chars > 0 and (cjk_chars / total_chars) > 0.1:
        return "CJK"
    return "LATIN"

def get_body_text_size(doc):
    """Finds the most common font size, assumed to be the body text."""
    font_counts = Counter()
    for page in doc:
        # Only sample text from blocks that look like paragraphs
        for block in page.get_text("dict")["blocks"]:
            if block["type"] == 0 and len(block.get("lines", [])) > 2:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_counts[round(span["size"])] += 1
    if not font_counts:
        return 12  # A reasonable default
    return font_counts.most_common(1)[0][0]


def is_potential_heading(block, body_text_size):
    """Determines if a block is a potential heading using stricter rules."""
    if block["type"] != 0 or not block.get("lines"):
        return False
    line = block["lines"][0]
    if not line.get("spans"):
        return False
    span = line["spans"][0]
    text = "".join(s["text"] for s in line["spans"]).strip()
    word_count = len(text.split())
    if word_count > 15:
        return False
    is_bold = "bold" in span["font"].lower()
    is_larger = round(span["size"]) > body_text_size
    # Also consider all-caps text as a heading style for visual docs
    is_all_caps = text.isupper() and word_count >= 3 and word_count < 10

    if not is_larger and not is_bold and not is_all_caps:
        return False
    return True

def get_heading_level(text, size, font, style_map):
    """Gets level from numbering, then style, then capitalization."""
    text = text.strip()
    # Priority 1: Numbering
    if re.match(r'^\d{1,2}\.\d{1,2}\.\d{1,2}', text): return "H3"
    if re.match(r'^\d{1,2}\.\d{1,2}', text): return "H2"
    if re.match(r'^\d{1,2}\.?\s', text): return "H1"

    # Priority 2: Font Style from map
    if (size, font) in style_map:
        return style_map.get((size, font))

    # Priority 3: Fallback for all-caps text in visual docs
    if text.isupper():
        return "H1"

    return None


def extract_from_flyer(doc, lang):
    """Specialized function for single-page, visual documents."""
    page = doc.load_page(0)
    max_score = 0
    hero_heading = None
    title = "" # Flyers/invitations usually don't have a formal title

    for block in page.get_text("dict")["blocks"]:
        if block["type"] == 0 and block.get("lines") and block["lines"][0].get("spans"):
            span = block["lines"][0]["spans"][0]
            text = " ".join(s["text"] for s in block["lines"][0]["spans"]).strip()
            if not text or len(text) > 50: continue

            # Calculate a prominence score, heavily favoring font size
            score = span["size"] * span["size"]
            if "bold" in span["font"].lower(): score *= 1.2
            # PATCH: Only apply capitalization score to Latin scripts
            if lang == "LATIN" and text.isupper(): score *= 1.1

            if score > max_score:
                max_score = score
                hero_heading = {"level": "H1", "text": text, "page": 0}

    outline = [hero_heading] if hero_heading else []
    return {"title": title, "outline": outline}


def extract_outline(pdf_path):
    """
    Extracts outline, now with a pre-processing step to merge separated heading numbers and text.
    """
    try:
        doc = fitz.open(pdf_path)
        if not doc or doc.page_count == 0:
            return {"title": "", "outline": []}
    except Exception:
        return {"title": "", "outline": []}

    # PATCH: Add language detection
    lang = detect_language(doc)

    # Divert single-page documents to the specialized flyer function if needed
    if doc.page_count == 1:
        # PATCH: Pass language to the flyer function
        return extract_from_flyer(doc, lang)
    
    title = doc.metadata.get('title', '').strip()
    if not title or len(title) < 5 or any(ext in title.lower() for ext in [".doc", ".pdf", ".cdr"]):
        title = ""

    outline = []
    found_headings = set()
    # Find body size just once
    font_sizes = Counter(round(span["size"]) for page in doc for block in page.get_text("dict")["blocks"] if block["type"]==0 for line in block.get("lines",[]) for span in line.get("spans",[]))
    body_size = font_sizes.most_common(1)[0][0] if font_sizes else 12

    for page_num, page in enumerate(doc):
        # Pre-process blocks on each page to merge separated headings
        try:
            # Using sort=True helps ensure correct reading order for merging
            blocks = page.get_text("dict", sort=True)["blocks"]
        except Exception:
            blocks = page.get_text("dict")["blocks"]

        processed_blocks = []
        i = 0
        while i < len(blocks):
            block = blocks[i]
            if block['type'] != 0 or not block.get('lines'):
                processed_blocks.append(block)
                i += 1
                continue

            current_text = " ".join(s['text'] for l in block['lines'] for s in l['spans']).strip()
            is_standalone_number = re.fullmatch(r'[\d\.]+\s*', current_text)

            if is_standalone_number and i + 1 < len(blocks):
                next_block = blocks[i+1]
                if next_block['type'] == 0 and next_block.get('lines') and abs(block['bbox'][1] - next_block['bbox'][1]) < 5:
                    next_text = " ".join(s['text'] for l in next_block['lines'] for s in l['spans']).strip()
                    block['lines'][0]['spans'][0]['text'] = f"{current_text.strip()} {next_text}"
                    processed_blocks.append(block)
                    i += 2
                    continue
            
            processed_blocks.append(block)
            i += 1
        # End of new pre-processing step

        # Run heading detection on the processed (potentially merged) blocks
        for block in processed_blocks:
            if block['type'] == 0 and block.get("lines"):
                full_text = " ".join(s['text'] for l in block['lines'] for s in l['spans']).strip()
                full_text = re.sub(r'\s+', ' ', full_text)

                # PATCH: Language-aware length check
                is_too_long = len(full_text) > 50 if lang == "CJK" else len(full_text.split()) > 25
                if not full_text or full_text in found_headings or is_too_long:
                    continue
                
                first_span = block['lines'][0]['spans'][0]
                if round(first_span['size']) > body_size:
                    level = None
                    # PATCH: Multilingual regex for numbering
                    num_pattern = r'[\d一二三四五六七八九十百千万億壹貳叁肆伍陸柒捌玖拾零〇１-９]+'
                    h3_pattern = re.compile(f'^{num_pattern}\.{num_pattern}\.{num_pattern}')
                    h2_pattern = re.compile(f'^{num_pattern}\.{num_pattern}|[（(]{num_pattern}[)）]')
                    h1_pattern = re.compile(f'^(Chapter\s+|第)?{num_pattern}[\.、．]?\s')

                    if h3_pattern.match(full_text): level = "H3"
                    elif h2_pattern.match(full_text): level = "H2"
                    elif h1_pattern.match(full_text): level = "H1"
                    
                    # Fallback for non-numbered headings
                    if not level:
                        if len(full_text.split()) < 7:
                            level = "H1"

                    if level:
                        outline.append({
                            "level": level,
                            "text": full_text,
                            "page": page_num
                        })
                        found_headings.add(full_text)

    doc.close()
    return {"title": title, "outline": outline}


def process_files():
    """Main function to process all PDFs in the input directory."""
    input_dir = "/app/input"
    output_dir = "/app/output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.json")
            try:
                result = extract_outline(pdf_path)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
                print(f"✅ Successfully processed {filename}")
            except Exception as e:
                print(f"❌ Failed to process {filename}: {e}")

if __name__ == "__main__":
    process_files()