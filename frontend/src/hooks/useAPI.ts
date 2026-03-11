// useApi — Zentraler Hook für alle API-Aufrufe zum Backend
// Kapselt fetch() mit der Backend-URL und Fehlerbehandlung
// Wird von allen Seiten verwendet die Daten laden oder senden
//
// Beispiel:
//   const api = useApi()
//   const modules = await api.get('/api/modules/')

// Backend-URL — läuft auf Port 8000 (FastAPI/Uvicorn)
const API_BASE = 'http://localhost:8000'

// Generische Fetch-Funktion mit Fehlerbehandlung
// T = der erwartete Rückgabetyp (TypeScript Generics)
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  // Anfrage an das Backend senden
  const response = await fetch(`${API_BASE}${endpoint}`, {
    // Headers setzen — JSON als Standard
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    // Restliche Optionen (method, body, etc.) durchreichen
    ...options,
  })

  // Fehlerbehandlung — wirft einen Fehler wenn Status nicht 2xx
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `API Fehler: ${response.status}`)
  }

  // Antwort als JSON parsen und typisiert zurückgeben
  return response.json()
}

// Exportierte Hilfsfunktionen für die vier HTTP-Methoden
// Jede Seite kann diese direkt importieren und nutzen

// GET — Daten abrufen (z.B. Module laden)
export function get<T>(endpoint: string): Promise<T> {
  return fetchApi<T>(endpoint, { method: 'GET' })
}

// POST — Daten erstellen (z.B. neues Modul anlegen)
export function post<T>(endpoint: string, body?: unknown): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

// PUT — Daten aktualisieren (z.B. Modul umbenennen)
export function put<T>(endpoint: string, body?: unknown): Promise<T> {
  return fetchApi<T>(endpoint, {
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  })
}

// DELETE — Daten löschen (z.B. Modul entfernen)
export function del<T>(endpoint: string): Promise<T> {
  return fetchApi<T>(endpoint, { method: 'DELETE' })
}