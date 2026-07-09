# FastAPI Entry Point — startet den Server und konfiguriert die App
# Serviert im Production-Modus auch das gebaute Frontend als Static Files
import os
from pathlib import Path
from dotenv import load_dotenv

# .env laden bevor andere Module os.getenv() aufrufen.
# Docker-Env hat Vorrang — lokal .env, auf Olymp override.yml.
load_dotenv()
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.models.database import engine, Base
from backend.api.modules import router as modules_router
from backend.api.documents import router as documents_router
from backend.api.summaries import router as summaries_router
from backend.api.mindmap import router as mindmap_router
from backend.api.folders import router as folders_router
from backend.api.calendar import router as calendar_router
from backend.api.sport import router as sport_router
from backend.api.insights_sport import router as insights_sport_router
from backend.api.sport_stats import router as sport_stats_router
from backend.api.notes import router as notes_router
from backend.journal.api.auth import router as journal_auth_router
from backend.journal.api.entries import router as journal_entries_router
from backend.journal.api.analytics import router as journal_analytics_router
from backend.journal.api.medications import router as journal_medications_router
from backend.journal.api.medication_dose import router as journal_dose_router
from backend.journal.api.medication_calendar import router as journal_med_calendar_router
from backend.journal.models.journal_database import engine as journal_engine
from backend.journal.models.journal_database import JournalBase
from backend.journal.api.calendar import router as journal_calendar_router
from backend.journal.api.insights import router as journal_insights_router
from backend.journal.api.topics import router as journal_topics_router
from backend.journal.api.mood_checkin import router as mood_checkin_router
from backend.journal.api.journal_metis import router as journal_metis_router
from backend.journal.api.journal_metis_ai import router as journal_metis_ai_router
from backend.auth.auth_middleware import router as auth_router
from backend.auth.auth_middleware import require_auth
from backend.api.ollama_status import router as ollama_status_router
from backend.api.notes_ai import router as notes_ai_router# WICHTIG: Alle Models importieren, damit SQLAlchemy sie kennt
from backend.api.delphi import router as delphi_router
from backend.api.metis import router as metis_router
from backend.api.metis_ai import router as metis_ai_router
from backend.api.relations import router as relations_router
from backend.api.relations import type_router as relation_types_router
from backend.api.relations_ai import router as relations_ai_router
from backend.api.relations_ai_stream import router as relations_ai_stream_router
from backend.api.relations_inference import router as relations_inference_router
from backend.api.relations_evidence import router as relations_evidence_router
from backend.api.git_tracker import router as git_tracker_router
from backend.api.concepts import router as concepts_router
from backend.api.concepts_ai import router as concepts_ai_router
from backend.api.concepts_link import router as concepts_link_router
from backend.api.concepts_link_stream import router as concepts_link_stream_router
from backend.api.concepts_embedding import router as concepts_embedding_router
from backend.api.concepts_cluster import router as concepts_cluster_router
from backend.api.concepts_cluster_stream import router as concepts_cluster_stream_router
from backend.api.concepts_graph import router as concepts_graph_router
from backend.api.concepts_sphere_layout import router as concepts_sphere_layout_router
from backend.api.concepts_unlinked import router as concepts_unlinked_router
from backend.api.archive import router as archive_router
from backend.api.concepts_gaps import router as concepts_gaps_router
from backend.api.concepts_merge import router as concepts_merge_router
from backend.api.settings import router as settings_router
from backend.api.weather import router as weather_router
from backend.api.icloud_admin import router as icloud_admin_router
from backend.api.llm import router as llm_router
# Alle Models importieren, damit SQLAlchemy-Relationships auflösen
import backend.models.registry  # noqa: F401
import backend.journal.models  # noqa: F401


# Erstellt alle Tabellen in beiden Datenbanken beim Server-Start
Base.metadata.create_all(bind=engine)
JournalBase.metadata.create_all(bind=journal_engine)

# FastAPI App initialisieren
app = FastAPI(title="Pallas", version="0.1.0")

# CORS-Middleware: Erlaubt Frontend-Zugriff
# Dev: localhost:5173, Production: Server-IP auf Port 8001
CORS_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Auth-Middleware — prüft JWT-Cookie bei jedem API-Request
# Wird nur aktiv wenn /etc/olymp/auth.json existiert (Production)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Auth für alle API-Routen erzwingen (Production-Modus)"""
    auth_response = await require_auth(request)
    if auth_response is not None:
        return auth_response
    return await call_next(request)


# Prüfe ob Frontend vorhanden ist (Production-Modus)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
_HAS_FRONTEND = (
    (FRONTEND_DIR / "index.html").exists()
    and (FRONTEND_DIR / "assets").exists()
)


# Root-Endpunkt — Frontend in Production, API-Info in Dev
@app.get("/")
def root():
    if _HAS_FRONTEND:
        return FileResponse(str(FRONTEND_DIR / "index.html"))
    return {"message": "Pallas API läuft!", "version": "0.1.0"}


# Health-Check Endpunkt
@app.get("/health")
def health():
    return {"status": "ok"}



# iCloud Background-Scheduler (alle 30min sync)
@app.on_event("startup")
async def _icloud_startup():
    from backend.services.icloud_scheduler import start_scheduler
    start_scheduler()


@app.on_event("shutdown")
async def _icloud_shutdown():
    from backend.services.icloud_scheduler import stop_scheduler
    await stop_scheduler()

# API-Routen registrieren
app.include_router(settings_router)
app.include_router(settings_router)
app.include_router(auth_router)
app.include_router(modules_router)
app.include_router(documents_router)
app.include_router(summaries_router)
app.include_router(mindmap_router)
app.include_router(folders_router)
app.include_router(calendar_router)
app.include_router(sport_stats_router)
app.include_router(sport_router)
app.include_router(insights_sport_router)
app.include_router(notes_router)
app.include_router(journal_auth_router)
app.include_router(journal_entries_router)
app.include_router(journal_analytics_router)
app.include_router(journal_med_calendar_router)
app.include_router(journal_medications_router)
app.include_router(journal_dose_router)
app.include_router(journal_calendar_router)
app.include_router(journal_topics_router)
app.include_router(journal_insights_router)
app.include_router(mood_checkin_router)
app.include_router(journal_metis_router)
app.include_router(journal_metis_ai_router)
app.include_router(ollama_status_router)
app.include_router(notes_ai_router)
app.include_router(delphi_router)
app.include_router(metis_router)
app.include_router(metis_ai_router)
app.include_router(relations_router)
app.include_router(relation_types_router)
app.include_router(relations_ai_stream_router)
app.include_router(relations_ai_router)
app.include_router(relations_inference_router)
app.include_router(relations_evidence_router)
app.include_router(git_tracker_router)
app.include_router(concepts_graph_router)
app.include_router(concepts_sphere_layout_router)
app.include_router(concepts_unlinked_router)
app.include_router(archive_router)
app.include_router(concepts_gaps_router)
app.include_router(concepts_merge_router)
app.include_router(concepts_router)
app.include_router(concepts_cluster_stream_router)
app.include_router(concepts_cluster_router)
app.include_router(concepts_ai_router)
app.include_router(concepts_embedding_router)
app.include_router(concepts_link_stream_router)
app.include_router(concepts_link_router)
app.include_router(llm_router)
app.include_router(weather_router)
app.include_router(icloud_admin_router)

# Static Files — gebautes Frontend servieren (nur in Production)
if _HAS_FRONTEND:
    # Statische Assets (JS, CSS, Bilder) direkt servieren
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIR / "assets")),
        name="static-assets",
    )

    # Catch-All Route — alles was kein API-Call ist geht ans Frontend
    # Wichtig für React Router (Client-Side Routing)
    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """Frontend servieren — SPA Catch-All für React Router"""
        # Prüfen ob die Datei direkt existiert (z.B. favicon.ico)
        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Sonst immer index.html zurückgeben (React Router übernimmt)
        return FileResponse(str(FRONTEND_DIR / "index.html"))
