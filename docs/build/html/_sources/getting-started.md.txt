# Getting Started

## Prerequisites

- Python 3.12+
- Node.js 20+
- Git
- [Tesseract](https://github.com/tesseract-ocr/tesseract) (for OCR)
- [Ollama](https://ollama.ai) (optional, required for journal)

## Backend Setup

Clone the repository and install dependencies:

    git clone https://github.com/NoahRolli/pallas.git
    cd pallas
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -r backend/requirements.txt

Start the server:

    uvicorn backend.main:app --reload

API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).