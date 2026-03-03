# Ollama Provider: Anbindung an die lokale Ollama API
# Wird über ai_service.py aufgerufen — nie direkt
# Läuft komplett lokal — keine Daten verlassen den Rechner

import json
import re
import httpx
from backend.infra.config import OLLAMA_BASE_URL, OLLAMA_MODEL


class OllamaProvider:
    """AI-Provider für die lokale Ollama-Instanz."""

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL

    async def _chat(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        Sendet eine Anfrage an die Ollama API.
        Gibt den Antwort-Text zurück.
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                    }
                }
            )

            if response.status_code != 200:
                raise ConnectionError(
                    f"Ollama nicht erreichbar (Status {response.status_code}). "
                    "Läuft Ollama? Starte mit: ollama serve"
                )

            return response.json()["response"]

    async def is_available(self) -> bool:
        """Prüft ob Ollama läuft und erreichbar ist."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def _parse_json(self, text: str):
        """
        Extrahiert JSON aus Ollama-Antworten.
        Ollama packt JSON oft in Markdown-Backticks, die wir entfernen.
        """
        # Markdown-Backticks entfernen (```json ... ``` oder ``` ... ```)
        cleaned = re.sub(r"```(?:json)?\s*", "", text)
        cleaned = cleaned.strip("`").strip()
        return json.loads(cleaned)
    
    async def summarize(self, text: str) -> dict:
        """
        Generiert eine Zusammenfassung mit Schlüsselbegriffen.
        Gibt zurück: {"summary": str, "key_terms": list[str]}
        """
        prompt = f"""Analysiere den folgenden Text und erstelle:
1. Eine strukturierte Zusammenfassung (maximal 500 Wörter)
2. Eine Liste der 5-10 wichtigsten Fachbegriffe

Antworte NUR im JSON-Format, kein anderer Text:
{{"summary": "...", "key_terms": ["Begriff1", "Begriff2", ...]}}

Text:
{text[:4000]}"""

        response_text = await self._chat(prompt)
        try:
            return self._parse_json(response_text)
        except json.JSONDecodeError:
            return {"summary": response_text, "key_terms": []}

    async def explain_term(self, term: str, context: str) -> str:
        """Erklärt einen Fachbegriff im Kontext des Dokuments."""
        prompt = f"""Erkläre den Fachbegriff "{term}" einfach und verständlich.
Beziehe dich dabei auf folgenden Kontext:

{context[:2000]}

Antworte in 2-3 Sätzen, verständlich für Studierende."""

        return await self._chat(prompt, max_tokens=500)

    async def generate_mindmap(self, text: str) -> list[dict]:
        """
        Generiert eine Mindmap-Struktur aus einem Text.
        Gibt verschachtelte Knoten zurück.
        """
        prompt = f"""Erstelle eine hierarchische Mindmap-Struktur aus diesem Text.
Antworte NUR im JSON-Format als Liste von Knoten:
[{{"label": "Hauptthema", "detail": "Kurze Erklärung", "children": [
    {{"label": "Unterthema", "detail": "...", "children": []}}
]}}]

Maximal 3 Ebenen tief, 3-5 Knoten pro Ebene.

Text:
{text[:3000]}"""

        response_text = await self._chat(prompt)
        try:
            return self._parse_json(response_text)
        except json.JSONDecodeError:
            return [{"label": "Fehler beim Parsen", "detail": response_text, "children": []}]

    async def deep_dive(self, node_label: str, node_detail: str, context: str) -> list[dict]:
        """Generiert Unterknoten für einen Mindmap-Knoten (Reinzoomen)."""
        prompt = f"""Für eine Mindmap: Erstelle 3-5 detailliertere Unterknoten
für das Thema "{node_label}" ({node_detail}).

Kontext aus dem Originaldokument:
{context[:2000]}

Antworte NUR im JSON-Format:
[{{"label": "...", "detail": "...", "children": []}}]"""

        response_text = await self._chat(prompt)
        try:
            return self._parse_json(response_text)
        except json.JSONDecodeError:
            return [{"label": "Fehler", "detail": response_text, "children": []}]