# API-Endpunkte für Journal-Authentifizierung
# Passwort setzen, Session starten (Unlock), Session beenden (Lock)
# Das Passwort wird nie gespeichert — nur der Argon2id Hash

from fastapi import APIRouter, HTTPException
from backend.journal.api.schemas import PasswordInput
from backend.journal.services.password_service import (
    hash_password, verify_password, is_password_set, get_stored_hash
)
from backend.journal.services.crypto_service import derive_key
from backend.journal.services.session_service import (
    session_manager, is_session_active
)

# Router-Objekt — wird in main.py registriert
router = APIRouter(prefix="/api/journal", tags=["journal-auth"])


# GET /api/journal/status — Ist das Journal eingerichtet? Ist es entsperrt?
@router.get("/status")
def journal_status():
    return {
        "is_setup": is_password_set(),
        "is_unlocked": is_session_active(),
    }


# POST /api/journal/setup — Erstmaliges Passwort setzen
# Kann nur einmal aufgerufen werden — danach kein Reset möglich
@router.post("/setup")
def setup_journal(data: PasswordInput):
    if is_password_set():
        raise HTTPException(
            status_code=400,
            detail="Journal ist bereits eingerichtet. Kein Passwort-Reset möglich."
        )

    if len(data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Passwort muss mindestens 8 Zeichen lang sein."
        )

    hash_password(data.password)
    return {"message": "Journal erfolgreich eingerichtet."}


# POST /api/journal/unlock — Session starten (Passwort prüfen)
@router.post("/unlock")
def unlock_journal(data: PasswordInput):
    if not is_password_set():
        raise HTTPException(
            status_code=400,
            detail="Journal ist noch nicht eingerichtet. Bitte zuerst /setup aufrufen."
        )

    if not verify_password(data.password, get_stored_hash()):
        raise HTTPException(
            status_code=401,
            detail="Falsches Passwort."
        )

    aes_key = derive_key(data.password)
    session_manager.unlock(aes_key)
    return {"message": "Journal entsperrt."}


# POST /api/journal/lock — Session beenden (AES-Key aus RAM löschen)
@router.post("/lock")
def lock_journal():
    session_manager.lock()
    return {"message": "Journal gesperrt."}