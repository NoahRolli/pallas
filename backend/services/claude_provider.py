# Claude Provider: Anbindung an die Anthropic Claude API
# Wird über ai_service.py aufgerufen — nie direkt
# Für Zusammenfassungen, Begriffserklärungen und Mindmap-Generierung

import json
from anthropic import Anthropic
from backend.infra.config import CLAUDE_API_KEY, CLAUDE_MODEL


class ClaudeProvider:
    """AI-Provider für die Claude API von Anthropic."""

    def __init__(self):
        # Client wird erst beim ersten Aufruf erstellt
        # So crasht die App nicht wenn kein API-Key gesetzt ist
        self._client = None

    def _get_client(self) -> Anthropic:
        """Erstellt den Anthropic Client beim ersten Aufruf (Lazy Init)."""
        if self._client is None:
            if not CLAUDE_API_KEY:
                raise ValueError(
                    "CLAUDE_API_KEY ist nicht gesetzt. "
                    "Bitte in .env oder config.py eintragen."
                )
            self._client = Anthropic(api_key=CLAUDE_API_KEY)
        return self._client

    async def summarize(self, text: str) -> dict:
        """
        Generiert eine Zusammenfassung mit Schlüsselbegriffen.
        Gibt zurück: {"summary": str, "key_terms": list[str]}
        """
        client = self._get_client()

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"""Analysiere den folgenden Text und erstelle:
1. Eine strukturierte Zusammenfassung (maximal 500 Wörter)
2. Eine Liste der 5-10 wichtigsten Fachbegriffe

Antworte im JSON-Format:
{{"summary": "...", "key_terms": ["Begriff1", "Begriff2", ...]}}

Text:
{text}"""
            }]
        )

        # Antwort parsen — Claude gibt Text zurück, wir extrahieren JSON
        response_text = message.content[0].text
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"summary": response_text, "key_terms": []}

    async def explain_term(self, term: str, context: str) -> str:
        """Erklärt einen Fachbegriff im Kontext des Dokuments."""
        client = self._get_client()

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""Erkläre den Fachbegriff "{term}" einfach und verständlich.
Beziehe dich dabei auf folgenden Kontext:

{context[:2000]}

Antworte in 2-3 Sätzen, verständlich für Studierende."""
            }]
        )

        return message.content[0].text

    async def generate_mindmap(self, text: str) -> list[dict]:
        """
        Generiert eine Mindmap-Struktur aus einem Text.
        Gibt verschachtelte Knoten zurück.
        """
        client = self._get_client()

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"""Erstelle eine hierarchische Mindmap-Struktur aus diesem Text.
Antworte im JSON-Format als Liste von Knoten:
[{{"label": "Hauptthema", "detail": "Kurze Erklärung", "children": [
    {{"label": "Unterthema", "detail": "...", "children": []}}
]}}]

Maximal 3 Ebenen tief, 3-5 Knoten pro Ebene.

Text:
{text[:3000]}"""
            }]
        )

        response_text = message.content[0].text
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return [{"label": "Fehler beim Parsen", "detail": response_text, "children": []}]

    async def deep_dive(self, node_label: str, node_detail: str, context: str) -> list[dict]:
        """Generiert Unterknoten für einen Mindmap-Knoten (Reinzoomen)."""
        client = self._get_client()

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": f"""Für eine Mindmap: Erstelle 3-5 detailliertere Unterknoten
für das Thema "{node_label}" ({node_detail}).

Kontext aus dem Originaldokument:
{context[:2000]}

Antworte im JSON-Format:
[{{"label": "...", "detail": "...", "children": []}}]"""
            }]
        )

        response_text = message.content[0].text
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return [{"label": "Fehler", "detail": response_text, "children": []}]
        