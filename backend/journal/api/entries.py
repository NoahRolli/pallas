# API-Endpunkte für verschlüsselte Tagebucheinträge
# Alle Daten werden vor dem Speichern verschlüsselt und beim Lesen entschlüsselt
# Jedes Feld (Titel, Inhalt, Datum) wird unabhängig verschlüsselt
# mit eigenem IV und Auth-Tag — sicher und einzeln entschlüsselbar
# Auto-Titel: Wenn kein Titel angegeben, generiert Ollama einen
# language Query-Parameter steuert die Sprache der Auto-Titel-Generierung

from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.journal.models.journal_database import get_journal_db
from backend.journal.models.journal_entry import JournalEntry
from backend.journal.services.session_service import session_manager
from backend.journal.services.crypto_service import encrypt_text, decrypt_text
from backend.journal.services.journal_ai_service import journal_ai
from backend.journal.api.dependencies import require_unlocked
from backend.journal.api.schemas import EntryCreate, EntryUpdate

# Router-Objekt — wird in main.py registriert
router = APIRouter(prefix="/api/journal/entries", tags=["journal-entries"])


def _iso_utc(dt):
    """ISO-Zeitstempel MIT UTC-Marker.

    Column(DateTime) speichert ohne Zeitzone. created_at/updated_at werden als
    UTC geschrieben (journal_entry.py), kommen aber naiv zurueck. Ohne Marker
    liest JS den String als Lokalzeit → Anzeige um den Offset verschoben.
    replace() stellt die beim Speichern verlorene Info wieder her.
    """
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


# GET /api/journal/entries — Alle Einträge abrufen (entschlüsselt)
@router.get("/")
def get_entries(db: Session = Depends(get_journal_db)):
    require_unlocked()

    entries = db.query(JournalEntry).filter(JournalEntry.is_deleted == 0).all()
    aes_key = session_manager.get_key()
    decrypted = []

    for entry in entries:
        try:
            decrypted.append({
                "id": entry.id,
                "title": decrypt_text(entry.encrypted_title, aes_key),
                "content": decrypt_text(entry.encrypted_content, aes_key),
                "date": decrypt_text(entry.encrypted_date, aes_key),
                "created_at": _iso_utc(entry.created_at),
                "updated_at": _iso_utc(entry.updated_at),
            })
        except Exception:
            continue

    return decrypted


# POST /api/journal/entries — Neuen Eintrag erstellen (wird verschlüsselt)
# language Parameter für Auto-Titel-Generierung via Ollama
@router.post("/")
async def create_entry(
    data: EntryCreate,
    language: str = Query(default="de", pattern="^(de|en)$"),
    db: Session = Depends(get_journal_db),
):
    require_unlocked()
    aes_key = session_manager.get_key()

    # Titel: User-Eingabe verwenden oder via Ollama generieren
    title = data.title if data.title and data.title.strip() else None
    if not title:
        title = await journal_ai.generate_title(data.content, language)

    # Jedes Feld unabhängig verschlüsseln (eigener IV + Tag pro Feld)
    entry = JournalEntry(
        encrypted_title=encrypt_text(title, aes_key),
        encrypted_content=encrypt_text(data.content, aes_key),
        encrypted_date=encrypt_text(data.date, aes_key),
        iv=b'',
        auth_tag=b'',
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {"id": entry.id, "title": title, "message": "Entry created and encrypted."}


# GET /api/journal/entries/{id} — Einzelnen Eintrag abrufen
@router.get("/{entry_id}")
def get_entry(entry_id: int, db: Session = Depends(get_journal_db)):
    require_unlocked()

    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.is_deleted == 0
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")

    aes_key = session_manager.get_key()

    return {
        "id": entry.id,
        "title": decrypt_text(entry.encrypted_title, aes_key),
        "content": decrypt_text(entry.encrypted_content, aes_key),
        "date": decrypt_text(entry.encrypted_date, aes_key),
        "created_at": _iso_utc(entry.created_at),
        "updated_at": _iso_utc(entry.updated_at),
    }


# PUT /api/journal/entries/{id} — Eintrag aktualisieren (neu verschlüsselt)
@router.put("/{entry_id}")
def update_entry(entry_id: int, data: EntryUpdate, db: Session = Depends(get_journal_db)):
    require_unlocked()

    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.is_deleted == 0
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")

    aes_key = session_manager.get_key()

    current_title = decrypt_text(entry.encrypted_title, aes_key)
    current_content = decrypt_text(entry.encrypted_content, aes_key)
    current_date = decrypt_text(entry.encrypted_date, aes_key)

    new_title = data.title if data.title is not None else current_title
    new_content = data.content if data.content is not None else current_content
    new_date = data.date if data.date is not None else current_date

    entry.encrypted_title = encrypt_text(new_title, aes_key)
    entry.encrypted_content = encrypt_text(new_content, aes_key)
    entry.encrypted_date = encrypt_text(new_date, aes_key)

    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "message": "Entry updated and re-encrypted."}


# DELETE /api/journal/entries/{id} — Soft-Delete
@router.delete("/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_journal_db)):
    require_unlocked()

    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.is_deleted == 0
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found.")

    entry.is_deleted = 1
    db.commit()
    return {"message": "Entry deleted."}


# POST /api/journal/entries/{id}/restore — Wiederherstellen
@router.post("/{entry_id}/restore")
def restore_entry(entry_id: int, db: Session = Depends(get_journal_db)):
    require_unlocked()

    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.is_deleted == 1
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Deleted entry not found.")

    entry.is_deleted = 0
    db.commit()
    return {"message": "Entry restored."}