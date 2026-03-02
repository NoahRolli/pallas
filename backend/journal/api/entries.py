# API-Endpunkte für verschlüsselte Tagebucheinträge
# Alle Daten werden vor dem Speichern verschlüsselt und beim Lesen entschlüsselt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.journal.models.journal_database import get_journal_db
from backend.journal.models.journal_entry import JournalEntry
from backend.journal.services.session_service import session_manager
from backend.journal.services.crypto_service import encrypt_text, decrypt_text
from backend.journal.api.dependencies import require_unlocked
from backend.journal.api.schemas import EntryCreate, EntryUpdate

# Router-Objekt — wird in main.py registriert
router = APIRouter(prefix="/api/journal/entries", tags=["journal-entries"])


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
                "title": decrypt_text(entry.encrypted_title, aes_key, entry.iv),
                "content": decrypt_text(entry.encrypted_content, aes_key, entry.iv),
                "date": decrypt_text(entry.encrypted_date, aes_key, entry.iv),
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            })
        except Exception:
            continue

    return decrypted


# POST /api/journal/entries — Neuen Eintrag erstellen (wird verschlüsselt)
@router.post("/")
def create_entry(data: EntryCreate, db: Session = Depends(get_journal_db)):
    require_unlocked()
    aes_key = session_manager.get_key()

    encrypted_title, iv, auth_tag = encrypt_text(data.title, aes_key)
    encrypted_content, _, _ = encrypt_text(data.content, aes_key, iv=iv)
    encrypted_date, _, _ = encrypt_text(data.date, aes_key, iv=iv)

    entry = JournalEntry(
        encrypted_title=encrypted_title,
        encrypted_content=encrypted_content,
        encrypted_date=encrypted_date,
        iv=iv,
        auth_tag=auth_tag,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {"id": entry.id, "message": "Eintrag erstellt und verschlüsselt."}


# GET /api/journal/entries/{id} — Einzelnen Eintrag abrufen
@router.get("/{entry_id}")
def get_entry(entry_id: int, db: Session = Depends(get_journal_db)):
    require_unlocked()

    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.is_deleted == 0
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")

    aes_key = session_manager.get_key()
    return {
        "id": entry.id,
        "title": decrypt_text(entry.encrypted_title, aes_key, entry.iv),
        "content": decrypt_text(entry.encrypted_content, aes_key, entry.iv),
        "date": decrypt_text(entry.encrypted_date, aes_key, entry.iv),
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


# PUT /api/journal/entries/{id} — Eintrag aktualisieren (neu verschlüsselt)
@router.put("/{entry_id}")
def update_entry(entry_id: int, data: EntryUpdate, db: Session = Depends(get_journal_db)):
    require_unlocked()

    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.is_deleted == 0
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")

    aes_key = session_manager.get_key()

    # Aktuelle Werte entschlüsseln als Fallback
    current_title = decrypt_text(entry.encrypted_title, aes_key, entry.iv)
    current_content = decrypt_text(entry.encrypted_content, aes_key, entry.iv)
    current_date = decrypt_text(entry.encrypted_date, aes_key, entry.iv)

    # Neue Werte übernehmen oder alte behalten
    new_title = data.title if data.title is not None else current_title
    new_content = data.content if data.content is not None else current_content
    new_date = data.date if data.date is not None else current_date

    # Komplett neu verschlüsseln mit neuem IV
    entry.encrypted_title, entry.iv, entry.auth_tag = encrypt_text(new_title, aes_key)
    entry.encrypted_content, _, _ = encrypt_text(new_content, aes_key, iv=entry.iv)
    entry.encrypted_date, _, _ = encrypt_text(new_date, aes_key, iv=entry.iv)

    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "message": "Eintrag aktualisiert und neu verschlüsselt."}


# DELETE /api/journal/entries/{id} — Soft-Delete
@router.delete("/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_journal_db)):
    require_unlocked()

    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.is_deleted == 0
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden.")

    entry.is_deleted = 1
    db.commit()
    return {"message": "Eintrag gelöscht."}


# POST /api/journal/entries/{id}/restore — Wiederherstellen
@router.post("/{entry_id}/restore")
def restore_entry(entry_id: int, db: Session = Depends(get_journal_db)):
    require_unlocked()

    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id, JournalEntry.is_deleted == 1
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Gelöschter Eintrag nicht gefunden.")

    entry.is_deleted = 0
    db.commit()
    return {"message": "Eintrag wiederhergestellt."}