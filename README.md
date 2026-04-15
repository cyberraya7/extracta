# Extracta — OSINT Intelligence Platform

A production-ready web application for open-source intelligence analysis. Upload documents, extract named entities using GLiNER, visualize relationship graphs, and trace every link back to source evidence.

## Features

- **File Upload** — PDF, DOCX, TXT, and CSV ingestion with text extraction
- **Named Entity Recognition** — GLiNER (`urchade/gliner_multi-v2.1`) with configurable entity labels and confidence thresholds
- **Entity Normalization** — Fuzzy deduplication, abbreviation matching, date and currency normalization
- **Link Analysis** — Sentence-level co-occurrence and paragraph proximity graphs via NetworkX
- **Evidence Mapping** — Every entity and relationship links back to source text snippets
- **Interactive Graph** — Force-directed visualization with click-to-explore, color-coded by entity type
- **Export** — Download results as JSON or CSV
- **Timeline View** — Extracted dates displayed chronologically

## Architecture

```
backend/          Python FastAPI
  app/
    api/          REST endpoints (upload, process, entities, graph, evidence, export)
    services/     NER engine, file parser, normalizer, link analyzer, evidence mapper
    models/       Pydantic schemas
    store/        In-memory session store
    utils/        Text splitting utilities

frontend/         React + TypeScript + Vite
  src/
    components/   Dashboard UI (graph, entity table, evidence panel, timeline)
    services/     API client (Axios)
    types/        Shared TypeScript types
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py                  # Starts on http://localhost:8000
```

The first run downloads the GLiNER model (~800 MB). Subsequent starts are instant.

### Frontend

```bash
cd frontend
npm install
npm run dev                    # Starts on http://localhost:5173
```

The Vite dev server proxies `/api` requests to the backend automatically.

## Usage

1. Open http://localhost:5173
2. Upload one or more documents (a sample report is at `backend/test_data/sample_report.txt`)
3. The platform extracts entities, builds the relationship graph, and maps evidence
4. Explore the interactive graph — click nodes to see connections, click edges to see co-occurrence evidence
5. Use the entity table to search, sort, and filter extracted entities
6. Adjust confidence threshold and entity type filters in the sidebar
7. Export results as JSON or CSV

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload files (multipart form) |
| POST | `/api/process` | Run NER + graph analysis |
| GET | `/api/entities` | List entities (supports `?type=`, `?min_confidence=`, `?search=`) |
| GET | `/api/graph` | Get graph nodes and edges (supports `?type=` filter) |
| GET | `/api/evidence/{entity_id}` | Get source snippets for an entity |
| GET | `/api/evidence/edge/{source}/{target}` | Get snippets for an entity pair |
| GET | `/api/export/json` | Download full export as JSON |
| GET | `/api/export/csv` | Download entities as CSV |
| GET | `/api/health` | Health check |

## Tech Stack

**Backend:** FastAPI, GLiNER, PyTorch, NetworkX, pdfplumber, python-docx

**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, react-force-graph-2d, Lucide icons, Axios
