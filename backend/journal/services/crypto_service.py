# Journal Crypto Service
# Verantwortlich für AES-256-GCM Verschlüsselung/Entschlüsselung
# und die Ableitung des AES-Keys aus dem Passwort via Argon2id.
#
# Aufbau verschlüsselter Daten: base64(IV + Ciphertext + AuthTag)
# - IV: 12 Bytes (wird bei jeder Verschlüsselung neu generiert)
# - Ciphertext: variable Länge
# - AuthTag: 16 Bytes (von GCM automatisch angehängt)

import os
import base64

from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.journal.infra.journal_config import (
    ARGON2_MEMORY_COST,
    ARGON2_TIME_COST,
    ARGON2_PARALLELISM,
    AES_KEY_LENGTH,
    AES_IV_LENGTH,
    ARGON2_SALT_LENGTH,
)


# ============================================
# Key-Ableitung & Salt
# ============================================

def generate_salt() -> bytes:
    """
    Generiert einen kryptographisch sicheren Salt.
    Wird einmalig beim Journal-Setup erstellt und in der DB gespeichert.

    Returns:
        16-byte zufälliger Salt
    """
    return os.urandom(ARGON2_SALT_LENGTH)


def derive_aes_key(password: str, salt: bytes) -> bytes:
    """
    Leitet einen AES-256 Schlüssel aus dem Passwort ab.
    Verwendet Argon2id als Key Derivation Function (KDF).
    Der gleiche Salt + Passwort ergibt immer den gleichen Key.

    Args:
        password: Das Klartext-Passwort
        salt: 16-byte Salt (wird bei Setup generiert und in DB gespeichert)

    Returns:
        32-byte AES-256 Schlüssel
    """
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=AES_KEY_LENGTH,
        type=Type.ID,
    )


# ============================================
# Verschlüsselung & Entschlüsselung
# ============================================

def encrypt(plaintext: str, key: bytes) -> str:
    """
    Verschlüsselt einen Klartext mit AES-256-GCM.
    GCM bietet sowohl Verschlüsselung als auch Integritätsschutz.

    Args:
        plaintext: Der zu verschlüsselnde Text
        key: 32-byte AES-256 Schlüssel

    Returns:
        Base64-encodierter String (IV + Ciphertext + AuthTag)
    """
    # Für jede Verschlüsselung eine neue IV — NIEMALS wiederverwenden!
    iv = os.urandom(AES_IV_LENGTH)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)

    # IV + Ciphertext zusammenfügen und als Base64 encodieren
    encrypted_blob = iv + ciphertext
    return base64.b64encode(encrypted_blob).decode("utf-8")


def decrypt(encrypted_data: str, key: bytes) -> str:
    """
    Entschlüsselt einen AES-256-GCM verschlüsselten Text.

    Args:
        encrypted_data: Base64-encodierter String (IV + Ciphertext + AuthTag)
        key: 32-byte AES-256 Schlüssel

    Returns:
        Entschlüsselter Klartext

    Raises:
        ValueError: Wenn Entschlüsselung fehlschlägt (falscher Key oder manipulierte Daten)
    """
    try:
        raw = base64.b64decode(encrypted_data)
        iv = raw[:AES_IV_LENGTH]
        ciphertext = raw[AES_IV_LENGTH:]

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        return plaintext.decode("utf-8")

    except Exception as e:
        raise ValueError(
            "Entschlüsselung fehlgeschlagen — falsches Passwort oder beschädigte Daten"
        ) from e