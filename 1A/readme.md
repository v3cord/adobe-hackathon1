 Understand Your Document - Outline Extractor

## Overview

This project implements a PDF outline extraction tool that processes PDF documents and extracts a structured outline including the document title and headings (H1, H2, H3) along with their page numbers. The goal is to mimic how a machine understanding system parses and organizes document structure for further applications like semantic search and recommendations.

---

## Features / Approach

- **Text Extraction:** Uses [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/en/latest/) to parse PDF documents.
- **Heading Detection:** Employs multi-factor heuristics combining:
  - **Font size analysis** to estimate relative importance.
  - **Text appearance cues:** bold and italic font styles.
  - **Text patterns using regex:** supports chapter/section markers in English, Chinese, Japanese, French, and German.
  - **Heading keywords:** common structural keywords across multiple languages.
  - **Position on the page:** indentation used as a weak signal.
- **Multilingual support:** Covers heading patterns for:
  - English, Chinese, Japanese, French, and German.
- **Output:** JSON file per PDF containing:
  - Document `title`.
  - `outline`: list of headings with level ("H1", "H2", "H3"), their text, and page number.
- **Performance:** Runs fully offline, CPU only, suitable for up to 50 pages within 10 seconds.
- **Dockerized:** Easy to build and run inside a Docker container, explicitly targeting AMD64 architecture.

---

## Dependencies

- Python 3.9
- PyMuPDF v1.23.7

All dependencies are installed via `requirements.txt`.

---

## Project Structure
<pre>
/1A
├── app
       ├── main.py
       ├── requirements.txt # Main extraction script
├── input
├── output
├── Dockerfile
├── readme.md # Python dependencies (PyMuPDF)
</pre>




---

## How to Build and Run

### Build the Docker Image

docker build --platform linux/amd64 -t pdf-extractor .

### Run the Container

Mount your input PDFs folder and output folder:
(MAC)
docker run --rm
-v $(pwd)/input:/app/input
-v $(pwd)/output:/app/output
--network none
mysolution:latest

(WINDOWS)

docker run --rm -v "%cd%/input:/app/input" -v "%cd%/output:/app/output" --network none pdf-extractor 


- Place your input PDF files in the `input/` directory.
- JSON output files will be created in the `output/` directory.
- The container automatically processes all `.pdf` files found in `input/`.

---

## How It Works

1. The script opens each PDF and extracts text blocks along with font size and styling info.
2. It merges multiline text blocks where appropriate.
3. It detects the document title as the first large font heading candidate.
4. Extracts outline elements (headings) with levels H1, H2, or H3 based on combined heuristics.
5. Outputs a JSON file following the format:

{
"title": "Document Title",
"outline": [
{ "level": "H1", "text": "Introduction", "page": 1 },
{ "level": "H2", "text": "What is AI?", "page": 2 },
{ "level": "H3", "text": "History of AI", "page": 3 }
]
}


---

## Multilingual Heading Support

The solution supports pattern-based detection in:

- **English:** Chapter, Section numbering, uppercase headings.
- **Chinese:** Patterns like `第X章`, `第X节`.
- **Japanese:** Patterns like `第X章`, `はじめに`.
- **French:** `chapitre`, `section`, `partie`.
- **German:** `Kapitel`, `Abschnitt`, `Teil`.

Additional heuristic coverage includes common keywords such as "Introduction", "Résumé", "Einleitung", and their equivalents.

---

## Notes and Limitations

- Designed for PDFs up to 50 pages for performance constraints.
- No external ML models; relies on heuristic rules and text appearance.
- May require further tuning for complex documents or other languages.
- Assumes fonts and layout are consistent for headings detection.
- No internet access required or used.

---

## Contact / Support

For issues or improvements, please open an issue or contact @prakashkumar0001000@gmail.com & @rishav.raj.im@gmail.com

---

Thank you for checking out this project!
