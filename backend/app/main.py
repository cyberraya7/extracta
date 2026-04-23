from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load backend/.env before importing modules that read os.environ.
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from app.db.database import create_all
from app.services.ner_engine import NEREngine
from app.api import upload, process, entities, graph, evidence, export, documents, sessions, faces


ner_engine = NEREngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all()
    ner_engine.load_model()
    app.state.ner_engine = ner_engine
    yield


app = FastAPI(
    title="Yose OSINT Platform",
    description="Intelligence analysis platform with NER, link analysis, and evidence mapping",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api")
app.include_router(process.router, prefix="/api")
app.include_router(entities.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(faces.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
