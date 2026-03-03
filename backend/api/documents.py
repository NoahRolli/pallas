# API-Endpunkte für Dokument-Upload und Verwaltung
# Ermöglicht das Hochladen von Dateien in ein Studienmodul
# Der Parser extrahiert automatisch den Text beim Upload

import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from backend.models.database import get_db
from backend.models.module import Module
from backend.models.document import Document
from backend.services.parser_service import parse_file, SUPPORTED_FORMATS
from backend.infra.config import STORAGE_DIR

# Router-Objekt — wird in main.py registriert
router = APIRouter(prefix="/api", tags=["documents"])


# GET /api/modules/{id}/documents — Alle Dokumente eines Moduls auflisten
@router.get("/modules/{module_id}/documents")
def get_documents(module_id: int, db: Session = Depends(get_db)):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Modul nicht gefunden")

    return module.documents


# POST /api/modules/{id}/documents — Datei hochladen
@router.post("/modules/{module_id}/documents")
def upload_document(
    module_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Modul nicht gefunden")

    # Dateiendung prüfen
    suffix = "." + file.filename.split(".")[-1].lower()
    if suffix not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Dateityp '{suffix}' wird nicht unterstützt. "
                   f"Erlaubt: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    # Modul-Ordner auf der SSD erstellen
    import os
    module_dir = STORAGE_DIR / str(module_id)
    os.makedirs(module_dir, exist_ok=True)

    # Datei auf der SSD speichern
    file_path = module_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Text aus der Datei extrahieren
    try:
        raw_text = parse_file(str(file_path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Dokument in der Datenbank speichern
    document = Document(
        module_id=module_id,
        filename=file.filename,
        file_path=str(file_path),
        file_type=suffix.replace(".", ""),
        raw_text=raw_text
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "text_length": len(raw_text),
        "message": f"'{file.filename}' erfolgreich hochgeladen und geparst"
    }


# DELETE /api/documents/{id} — Dokument löschen
@router.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")

    # Datei von der SSD löschen
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()

    db.delete(document)
    db.commit()

    return {"message": f"'{document.filename}' gelöscht"}
