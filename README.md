# Extracta — OSINT Intelligence Platform

Extracta is a full-stack web application for open-source intelligence-style document analysis. Upload documents (including folders), extract and normalize named entities, build relationship graphs from co-occurrence patterns, and trace every entity and edge back to source text evidence.

---

## Table of Contents

- [High-level workflow](#high-level-workflow)
- [Entity extraction and categorization](#entity-extraction-and-categorization)
- [Graph generation](#graph-generation)
- [Features](#features)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Usage](#usage)
- [API reference](#api-reference)
- [Tech stack](#tech-stack)

---

## High-level workflow

The system follows a pipeline from ingestion to visualization. Each analysis run is stored as a **session** so you can revisit past results without losing history.

```mermaid
flowchart LR
  subgraph ingest [Ingestion]
    A[Upload files or folder] --> B[Text extraction]
    B --> C[Documents stored in DB]
  end
  subgraph extract [Extraction]
    C --> D[GLiNER NER]
    C --> E[Regex patterns]
    D --> F[Merge and normalize]
    E --> F
  end
  subgraph analyze [Analysis]
    F --> G[Session created]
    G --> H[Per-document occurrences]
    H --> I[NetworkX graph]
    I --> J[Evidence snippets]
  end
  subgraph ui [UI]
    J --> K[Dashboard / Graph / Linked / Timeline]
  end
```

### End-to-end steps (what happens when you click “Process”)

1. **Upload** — Files are sent to the backend (batched for large folders). Supported types are parsed to plain text and stored as `Document` rows (SQLite by default; PostgreSQL optional via `DATABASE_URL`).
2. **Session** — A new analysis session is created with metadata (document list, labels, confidence threshold, auto-generated name with timestamp).
3. **Clear prior results** — Entity, occurrence, relationship, and evidence rows for the *current* session scope are cleared; older sessions remain in the database.
4. **NER** — For each document, **GLiNER** runs with your configured label set and confidence threshold (text is chunked for long inputs).
5. **Regex extraction** — Additional spans are detected for email, phone, and Malaysia IC-style numbers; these are merged with GLiNER output.
6. **Normalization** — Entities are deduplicated (fuzzy match, abbreviation handling, date and money normalization) and assigned stable IDs per run.
7. **Occurrences** — Per-document positions are recorded so **linked entities** (same normalized entity in 2+ documents) can be computed correctly.
8. **Graph** — A **NetworkX** graph is built from sentence-level and paragraph-level co-occurrence; edges carry weights and relationship hints.
9. **Evidence** — Snippets are stored for each entity and for entity pairs (edges) for the evidence side panel.
10. **UI** — The frontend loads entities and graph data; optional **async processing** with polling shows upload and per-document progress for large batches.

---

## Entity extraction and categorization

### Primary model: GLiNER

| Aspect | Detail |
|--------|--------|
| **Library** | [GLiNER](https://github.com/urchade/gliner) (`gliner` on PyTorch) |
| **Default checkpoint** | `urchade/gliner_multi-v2.1` (configurable in `backend/app/services/ner_engine.py` as `DEFAULT_MODEL`) |
| **Behavior** | Open-vocabulary NER: you supply a list of **string labels**; the model scores spans for each label. |
| **Chunking** | Long documents are split into chunks (max ~1500 characters per chunk in code) so inference stays within practical limits. |

**Default entity labels** (all can be toggled in the UI sidebar):

- `person`
- `organization`
- `location`
- `date`
- `money`
- `communication platform`
- `email`
- `phone`
- `ic number`

The UI maps each label to colors; the graph view also maps each label to a distinct **shape** (circle, diamond, triangle, etc.) for accessibility beyond color alone.

### Supplementary: rule-based extraction

File: `backend/app/services/regex_extractor.py`

- **Email** — Standard email pattern.
- **Phone** — Flexible international / local digit patterns.
- **Malaysia IC** — Numeric patterns with optional hyphens (e.g. `920710-14-5678`).

These are converted into the same internal structure as GLiNER spans and merged during normalization.

### Normalization

File: `backend/app/services/entity_normalizer.py`

- Deduplicates mentions into canonical entities (fuzzy threshold, abbreviation checks).
- Normalizes **dates** (via `python-dateutil`) and **money** strings where applicable.
- Assigns unique entity IDs per analysis run to avoid database collisions across sessions.

---

## Graph generation

### Backend: structure and logic

| Component | Technology | Role |
|-----------|------------|------|
| Graph data structure | **NetworkX** (`networkx`) | In-memory undirected graph of entities. |
| Builder | `backend/app/services/link_analyzer.py` | Adds nodes from normalized entities; adds edges when entities **co-occur** in the same sentence and with weaker weights in the same **paragraph**. |
| Serialization | Same module | Exports `nodes` (id, label, type, score, occurrences, connection count) and `edges` (source, target, weight, relationship type, endpoint labels). |

**Edge semantics (simplified):**

- **Sentence co-occurrence** — If two entities have overlapping positions within the same sentence span, an edge is created or strengthened.
- **Paragraph proximity** — Additional edges (scaled by `PARAGRAPH_WEIGHT_FACTOR`) connect entities that appear in the same paragraph but not necessarily the same sentence.

Combined text from all documents in the run is used when building the graph so cross-document co-occurrence in the concatenated view contributes to link structure; per-document occurrence records power **linked entities** across files.

### Frontend: layout and rendering

| Component | Technology | Role |
|-----------|------------|------|
| Layout engine | **d3-force** (via `react-force-graph-2d`) | Charge repulsion, link distance, cooldown simulation. |
| Component | `react-force-graph-2d` | Canvas-based 2D force-directed graph. |
| Custom drawing | Canvas `nodeCanvasObject` / `linkCanvasObject` | Node shapes, colors, labels; edge styling and optional relationship labels at high zoom. |

The graph tab includes **filters**: search by entity text (value), toggle visibility by **entity type**, a shape legend, and stronger spacing parameters for readability.

---

## Features

### Document ingestion

- **Formats** — PDF, DOCX, TXT, CSV; audio/video (MP3, WAV, M4A, MP4, WEBM, MKV) via **OpenAI Whisper** (local; requires `ffmpeg`).
- **Single and multi-file** upload; **folder** upload (webkit directory) with extension filtering.
- **Batched uploads** for large folders to reduce timeouts.
- **Document list** in results with index, size, **add files/folder**, and **delete** (removes file and DB row; re-runs analysis on remaining docs).

### Analysis and performance

- **Asynchronous processing** — `POST /api/process` starts work in a background thread; `GET /api/process/status/{session_id}` reports progress (current file, counts).
- **Progress UI** — Upload stage (batched) and processing stage (polling) with a real progress bar.

### Entity and graph UI

- **Dashboard** — Sortable/filterable entity table; confidence and type filters; search.
- **Graph (full tab)** — Interactive force-directed graph; node click (evidence), edge click (pair evidence); type + value filters; distinct shapes per type.
- **Linked** — Entities that appear in **two or more documents** in the same session (cross-document linking).
- **Timeline** — Date-type entities on a horizontal timeline (chronological sort).
- **Evidence panel** — Snippets with document names for selected entity or edge.

### Sessions and history

- Each process run creates a **session** stored in the database.
- **History** sidebar: list sessions, load previous analysis, **rename** session, delete session.
- **New analysis** clears the current UI workflow but keeps prior sessions in the DB.

### Data and export

- **SQLite** default (`backend/yose.db`); **PostgreSQL** via `DATABASE_URL`.
- **Export** JSON and CSV from the sidebar (full dump / entities per existing API).

### API surface

- REST API under `/api/*`; CORS open for local dev.
- Health check for monitoring.

---

## Architecture

```
backend/ Python 3.10+, FastAPI, Uvicorn
  app/
    api/                 upload, process (+ async status), entities, graph, evidence,
                         export, documents, sessions
    db/                  SQLAlchemy models, SQLite/Postgres engine, lightweight migrations
    services/            ner_engine (GLiNER), file_parser, regex_extractor,
                         entity_normalizer, link_analyzer (NetworkX), evidence_mapper
    store/               Session-scoped persistence helpers (MemoryStore)
    models/              Pydantic request/response schemas
    utils/               Text splitting, cleaning

frontend/                React, TypeScript, Vite, Tailwind CSS
  src/
    components/          Layout, UploadPanel, DocumentList, EntityTable, GraphVisualization,
                         EvidencePanel, Sidebar, TimelineView, LinkedEntitiesPanel,
                         HistoryPanel, ProcessingStatus
    services/            Axios API client (batched upload, process polling)
    types/               Shared TS types and label/color maps
```

Default dev ports:

- **Backend:** `http://localhost:8001` (see `backend/run.py`)
- **Frontend:** `http://localhost:5173` with `/api` proxied to `8001` (see `frontend/vite.config.ts`)

---

## Quick start

### Prerequisites

- Python 3.10+
- Node.js 18+
- For media: `ffmpeg` on the system path (e.g. `brew install ffmpeg`)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py # http://localhost:8001
```

The first run downloads the GLiNER model (on the order of hundreds of MB depending on cache). Subsequent starts are faster.

### Frontend

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

### Optional: PostgreSQL

Set `DATABASE_URL` before starting the backend, for example:

```bash
export DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/extracta
```

---

## Usage

1. Open `http://localhost:5173`.
2. Upload files or an entire folder (supported extensions only).
3. Wait for upload and processing (progress is shown for large batches).
4. Explore **Dashboard** (table, timeline), **Graph** (filters, shapes, zoom), and **Linked** (cross-document entities).
5. Click entities or edges to open **Evidence**.
6. Use **History** to reload or rename past sessions; **New analysis** starts a fresh upload flow without deleting old sessions.
7. Export **JSON** or **CSV** when needed.

Sample text: `backend/test_data/sample_report.txt`

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Multipart file upload; extracts text and stores documents |
| POST | `/api/process` | Starts analysis (async); returns `session_id`, `status: processing` |
| GET | `/api/process/status/{session_id}` | Processing progress and completion status |
| GET | `/api/entities` | List entities (`?type=`, `?min_confidence=`, `?search=`) |
| GET | `/api/entities/linked` | Entities appearing in 2+ documents (current session) |
| GET | `/api/graph` | Graph nodes and edges (`?type=` filter) |
| GET | `/api/evidence/{entity_id}` | Evidence snippets for an entity |
| GET | `/api/evidence/edge/{source}/{target}` | Evidence for an entity pair |
| GET | `/api/documents` | List uploaded documents |
| DELETE | `/api/documents/{id}` | Delete a document and reprocess as needed from UI |
| GET | `/api/sessions` | List analysis sessions |
| GET | `/api/sessions/{id}` | Session detail + documents |
| POST | `/api/sessions/{id}/load` | Set current session for API reads |
| PATCH | `/api/sessions/{id}` | Rename session |
| DELETE | `/api/sessions/{id}` | Delete session and associated analysis rows |
| GET | `/api/export/json` | Full JSON export |
| GET | `/api/export/csv` | CSV export |
| GET | `/api/health` | Health check |

---

## Tech stack

| Layer | Technologies |
|-------|----------------|
| **API** | FastAPI, Uvicorn, Pydantic |
| **NER** | GLiNER, PyTorch |
| **Graph (server)** | NetworkX |
| **Database** | SQLAlchemy 2, SQLite (default), psycopg2 (PostgreSQL optional) |
| **Documents** | pdfplumber, python-docx, CSV; Whisper + ffmpeg for A/V |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS 4 |
| **Graph (client)** | react-force-graph-2d, d3-force |
| **UI** | Lucide icons, Axios |

---

## License and attribution

Extracta integrates open models and libraries (e.g. GLiNER/Hugging Face ecosystem, NetworkX, React). Refer to each dependency’s license for redistribution terms.
