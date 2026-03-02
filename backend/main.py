# FastAPI Entry Point — startet den Server und konfiguriert die App

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.models.database import engine, Base
from backend.api.modules import router as modules_router
from backend.api.documents import router as documents_router
from backend.api.summaries import router as summaries_router

# WICHTIG: Alle Models importieren, damit SQLAlchemy sie kennt
from backend.models.module import Module  # noqa: F401
from backend.models.document import Document  # noqa: F401
from backend.models.summary import Summary  # noqa: F401
from backend.models.mindmap_node import MindmapNode  # noqa: F401

# Erstellt alle Tabellen in der SQLite-Datenbank beim Server-Start
Base.metadata.create_all(bind=engine)

# FastAPI App initialisieren
app = FastAPI(title="Pallas", version="0.1.0")

# CORS-Middleware: Erlaubt dem React-Frontend (Port 5173) auf die API zuzugreifen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Einfacher Test-Endpunkt — zeigt ob die API läuft
@app.get("/")
def root():
    return {"message": "Pallas API läuft!", "version": "0.1.0"}


# Health-Check Endpunkt
@app.get("/health")
def health():
    return {"status": "ok"}


# API-Routen registrieren
app.include_router(modules_router)
app.include_router(documents_router)
app.include_router(summaries_router)