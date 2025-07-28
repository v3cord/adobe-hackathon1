Connect What Matters — For the User Who Matters

## Overview

This project implements an intelligent document section extraction and ranking system tailored to prioritize content most relevant to a user persona and their specific job-to-be-done. It processes a collection of PDF documents to identify and rank the sections best matching the persona’s goals, supporting diverse user roles like HR professionals, researchers, analysts, and students. The solution is designed to run offline, on CPU-only environments, and is compliant with "Round 1B" challenge constraints.
## Features / Approach

    Input Handling: Accepts multiple PDF documents and a JSON configuration detailing the persona and their task.

    PDF Parsing: Uses PyMuPDF (fitz) to extract document sections and headings leveraging font size, boldness, and numbering heuristics.

    Semantic Embeddings: Employs MiniLM-L6-v2, an efficient sentence-transformers model (<0.1 GB), to embed sections and query semantics offline.

    Relevance Scoring: Ranks sections based on semantic similarity to the persona and job description.

    Diversity: Ensures selected sections cover diverse documents to provide broad, useful insights.

    Text Refinement: Extracted sections are truncated and cleaned for concise information delivery.

    Output: Generates a structured JSON output listing top-ranked sections along with metadata, supporting downstream processing.

    Performance: Runs fully offline with CPU-only requirements, processing 3-5 PDFs in under 60 seconds.

    Dockerized: Containerized for easy deployment and environment consistency.

## Dependencies
    Python 3.9 or above

    PyMuPDF

    sentence-transformers

    torch

    transformers

    huggingface-hub

    numpy

All dependencies are listed in requirements.txt.
## Project Structure

1B/
├── app/
│   ├── input/
│   │   ├──Collection1/
│   │   │    ├── PDFs/                       # Input PDF documents
│   │   │    └── challenge1b_input.json     # Input config: document list, persona, task
│   │   ├──Collection2/
│   │   │    ├── PDFs/                       # Input PDF documents
│   │   │    └── challenge1b_input.json
│   │   ├──Collection3/
│   │       ├── PDFs/                       # Input PDF documents
│   │       └── challenge1b_input.json
│   └── output/ 
|        ├──Collection1/
|        └── challenge1b_input.json                       # Output JSON files
├── models/
│   └── all-MiniLM-L6-v2/              # Offline pre-downloaded embedding model
├── src/
│   └── main.py                        # Main pipeline script
├── Dockerfile                        # Docker container setup
├── requirements.txt                  # Python dependencies

### Build the Docker Image

bash
docker build -t doc-intel-app .

### Run the Container
#(MAC)
bash
docker run --rm -v $(pwd)/app/input:/app/input -v $(pwd)/app/output:/app/output doc-intel-app

#(Windows Command Prompt)

bash
docker run --rm -v "%cd%\app\output:/project/app/output" doc-intel-app

    Place all PDF files in app/input/Collection X/PDFs/      {X is the serial number 1, 2, 3,....}

    Define scenario with persona and job in app/input/Collection X/challenge1b_input.json

    Resulting output JSON appears in app/output/Collection X/challenge1b_output.json

## How It Works

    Loads specified PDFs and parses headings and sections based on typographic cues.

    Embeds extracted sections and the job-to-be-done statement using MiniLM.

    Computes relevance scores per section for the persona’s task using semantic similarity.

    Selects top-ranking sections ensuring diverse document coverage.

    Refines text bodies to concise summaries.

    Outputs challenge-compliant JSON file with metadata and ranked sections.

Input Format Example (challenge1b_input.json)

json
{
  "documents": [
    {"filename": "Doc1.pdf", "title": "Doc1"},
    {"filename": "Doc2.pdf", "title": "Doc2"}
  ],
  "persona": {"role": "HR professional"},
  "job_to_be_done": {"task": "Create and manage fillable forms for onboarding and compliance."}
}

Output Format Example (challenge1b_output.json)

json
{
  "metadata": {
    "input_documents": [...],
    "persona": "HR professional",
    "job_to_be_done": "Create and manage fillable forms for onboarding and compliance.",
    "processing_timestamp": "2025-07-27T16:00:00Z"
  },
  "extracted_sections": [
    {
      "document": "Doc1",
      "section_title": "Onboarding Forms",
      "importance_rank": 1,
      "page_number": 2
    }
  ],
  "subsection_analysis": [
    {
      "document": "Doc1",
      "refined_text": "Details on managing fillable forms including templates and workflows...",
      "page_number": 2
    }
  ]
}

Challenge Compliance

    Runs offline with zero internet dependency at runtime.

    Embedding model size less than 1 GB.

    CPU-only execution for broad compatibility.

    Execution time within 60 seconds for up to 5 PDFs. Took ~40 seconds in test run for 31 test documents provided in github link

## Notes and Limitations 

    Designed for generic persona and document types – customizable by changing input JSON.

    Suitable for HR, researchers, analysts, students, and more.

    Can be extended by replacing the embedding model or adjusting selection heuristics to other use cases.

## Contact / Support

For issues or improvements, please open an issue or contact @prakashkumar0001000@gmail.com & @rishav.raj.im@gmail.com

Thank you for exploring the Connect What Matters — For the User Who Matters project!
