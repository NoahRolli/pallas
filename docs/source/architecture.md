# Architecture

## Overview

Pallas consists of two main modules: the **Study Companion** and the **Encrypted Journal**. Both share the same FastAPI backend but are architecturally isolated.

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.13 · FastAPI · SQLAlchemy · SQLite |
| Frontend | React · TypeScript · Vite · Tailwind CSS |
| AI (Study) | Claude API · Ollama (switchable) |
| AI (Journal) | Ollama only (local, private) |
| Encryption | AES-256-GCM · Argon2id |

## Data Flow

1. User uploads a file (PDF, Word, PowerPoint, Excel, Image, Markdown, TXT)
2. Parser service extracts raw text
3. AI service generates summary and key terms
4. Mindmap service builds hierarchical node structure
5. Frontend renders interactive, zoomable mindmap

## Database Architecture

Pallas uses two separate SQLite databases:

- **pallas.db** — Study modules, documents, summaries, mindmap nodes
- **journal.db** — Encrypted journal entries, mood data, embeddings (completely isolated)

## AI Provider Pattern

The study companion uses a switchable provider pattern. Both providers implement the same interface (summarize, explain_term, generate_mindmap, deep_dive), allowing seamless switching between Claude API and local Ollama.

The journal module exclusively uses Ollama — no external API calls, no shared code path with Claude.