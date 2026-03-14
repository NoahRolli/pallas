// ModuleDetail — Detailseite für ein einzelnes Studienmodul
// Zeigt alle Dokumente des Moduls an
// Ermöglicht Datei-Upload und Zusammenfassung generieren
//
// Route: /modules/:id (id kommt aus der URL)
// Nutzt useParams() um die Modul-ID aus der URL zu lesen

import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { get, post, del } from '../hooks/useAPI'
import type { Module, Document, Summary } from '../types/models'

function ModuleDetail() {
  // --- URL-Parameter ---
  // useParams liest die :id aus der URL, z.B. /modules/3 → id = "3"
  const { id } = useParams<{ id: string }>()

  // --- State ---
  const [module, setModule] = useState<Module | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Upload-State
  const [uploading, setUploading] = useState(false)

  // Zusammenfassung-State (pro Dokument)
  const [summaries, setSummaries] = useState<Record<number, Summary>>({})
  const [generating, setGenerating] = useState<number | null>(null)

  // --- Daten laden ---

  async function loadModule() {
    try {
      setLoading(true)
      setError(null)

      // Modul-Details laden
      const moduleData = await get<Module>(`/api/modules/${id}`)
      setModule(moduleData)

      // Dokumente des Moduls laden
      const docsData = await get<Document[]>(`/api/modules/${id}/documents/`)
      setDocuments(docsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden')
    } finally {
      setLoading(false)
    }
  }

  // Beim ersten Rendern und wenn sich die ID ändert
  useEffect(() => {
    if (id) loadModule()
  }, [id])

  // --- Datei-Upload ---

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      setUploading(true)
      setError(null)

      // FormData statt JSON — für Datei-Upload
      const formData = new FormData()
      formData.append('file', file)

      // Direkter fetch() weil useApi JSON-Headers setzt,
      // aber für FormData brauchen wir keinen Content-Type
      // (Browser setzt ihn automatisch mit Boundary)
      const response = await fetch(
        `http://localhost:8000/api/modules/${id}/documents/`,
        {
          method: 'POST',
          body: formData,
        }
      )

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || `Upload fehlgeschlagen: ${response.status}`)
      }

      // Dokumente neu laden
      await loadModule()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload fehlgeschlagen')
    } finally {
      setUploading(false)
      // Input zurücksetzen damit dieselbe Datei nochmal gewählt werden kann
      event.target.value = ''
    }
  }

  // --- Zusammenfassung generieren ---

  async function generateSummary(documentId: number) {
    try {
      setGenerating(documentId)
      setError(null)

      // POST /api/documents/{id}/summarize → AI-Zusammenfassung
      const summary = await post<Summary>(
        `/api/documents/${documentId}/summarize`
      )

      // Zusammenfassung im State speichern (nach Dokument-ID)
      setSummaries((prev) => ({ ...prev, [documentId]: summary }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Zusammenfassung fehlgeschlagen')
    } finally {
      setGenerating(null)
    }
  }

  // --- Dokument löschen ---

  async function deleteDocument(documentId: number) {
    try {
      await del(`/api/documents/${documentId}`)
      // Dokumente neu laden
      await loadModule()
      // Zusammenfassung entfernen falls vorhanden
      setSummaries((prev) => {
        const updated = { ...prev }
        delete updated[documentId]
        return updated
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Löschen fehlgeschlagen')
    }
  }

  // --- Render ---

  // Ladezustand
  if (loading) {
    return <p className="text-gray-400">Modul wird geladen...</p>
  }

  // Modul nicht gefunden
  if (!module) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-500 text-lg mb-4">Modul nicht gefunden.</p>
        <Link to="/" className="text-blue-400 hover:text-blue-300">
          ← Zurück zum Dashboard
        </Link>
      </div>
    )
  }

  return (
    <div>
      {/* Navigation zurück */}
      <Link
        to="/"
        className="text-sm text-gray-500 hover:text-gray-300 transition-colors mb-4 inline-block"
      >
        ← Zurück zum Dashboard
      </Link>

      {/* Modul-Header */}
      <div className="flex items-center gap-4 mb-8">
        {/* Farbiger Punkt */}
        <div
          className="w-4 h-4 rounded-full"
          style={{ backgroundColor: module.color }}
        />
        <div>
          <h1 className="text-3xl font-bold">{module.name}</h1>
          <p className="text-gray-400">{module.description}</p>
        </div>
      </div>

      {/* Fehlermeldung */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Upload-Bereich */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 mb-8">
        <h2 className="text-lg font-semibold mb-3">Dokument hochladen</h2>
        <p className="text-sm text-gray-500 mb-4">
          Unterstützte Formate: PDF, Word, PowerPoint, Excel, Markdown, TXT, Bilder (OCR)
        </p>

        {/* File-Input mit Label als Button gestylt */}
        <label className="inline-block cursor-pointer bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg transition-colors">
          {uploading ? 'Wird hochgeladen...' : 'Datei auswählen'}
          <input
            type="file"
            onChange={handleFileUpload}
            disabled={uploading}
            className="hidden"
            accept=".pdf,.docx,.pptx,.xlsx,.md,.txt,.png,.jpg,.jpeg"
          />
        </label>
      </div>

      {/* Dokument-Liste */}
      <h2 className="text-lg font-semibold mb-4">
        Dokumente ({documents.length})
      </h2>

      {/* Leerer Zustand */}
      {documents.length === 0 && (
        <div className="text-center py-12 bg-gray-900/50 border border-gray-800 rounded-lg">
          <p className="text-gray-500 mb-1">Noch keine Dokumente.</p>
          <p className="text-gray-600 text-sm">
            Lade ein Dokument hoch um loszulegen.
          </p>
        </div>
      )}

      {/* Dokument-Karten */}
      <div className="space-y-4">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="bg-gray-900 border border-gray-800 rounded-lg p-5"
          >
            {/* Dokument-Header */}
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-medium">{doc.filename}</h3>
                <span className="text-xs text-gray-500">
                  {doc.file_type.toUpperCase()} · {new Date(doc.uploaded_at).toLocaleDateString('de-CH')}
                </span>
              </div>

              {/* Aktionen */}
              <div className="flex items-center gap-3">
                {/* Zusammenfassung generieren */}
                <button
                  onClick={() => generateSummary(doc.id)}
                  disabled={generating === doc.id}
                  className="text-sm bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 disabled:opacity-50 px-3 py-1.5 rounded-lg transition-colors"
                >
                  {generating === doc.id ? 'Generiert...' : 'Zusammenfassen'}
                </button>

                {/* Löschen */}
                <button
                  onClick={() => deleteDocument(doc.id)}
                  className="text-xs text-red-400/50 hover:text-red-400 transition-colors"
                >
                  Löschen
                </button>
              </div>
            </div>

            {/* Zusammenfassung anzeigen (falls vorhanden) */}
            {summaries[doc.id] && (
              <div className="mt-4 pt-4 border-t border-gray-800">
                <h4 className="text-sm font-semibold text-gray-300 mb-2">
                  Zusammenfassung
                  <span className="text-xs text-gray-600 ml-2">
                    via {summaries[doc.id].ai_provider}
                  </span>
                </h4>
                <p className="text-sm text-gray-400 leading-relaxed">
                  {summaries[doc.id].summary}
                </p>

                {/* Schlüsselbegriffe */}
                {summaries[doc.id].key_terms.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {summaries[doc.id].key_terms.map((term, i) => (
                      <span
                        key={i}
                        className="text-xs bg-white/5 text-gray-400 px-2 py-1 rounded"
                      >
                        {term}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// Default Export — wird in App.tsx vom Router importiert
export default ModuleDetail
