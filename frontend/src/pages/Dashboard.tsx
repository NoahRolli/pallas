// Dashboard — Startseite mit Übersicht aller Studienmodule
// Lädt Module von der API (GET /api/modules/)
// Zeigt sie als Karten an mit Name, Beschreibung und Farbe
// Enthält einen Button um neue Module zu erstellen
// Modul-Karten sind klickbar und führen zur Detailseite (/modules/:id)
//
// Nutzt useState für lokalen State und useEffect für den API-Call
// beim ersten Laden der Seite

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { get, post, del } from '../hooks/useAPI'
import type { Module, ModuleCreate } from '../types/models'

function Dashboard() {
  // --- State ---

  // Liste aller Module (kommt von der API)
  const [modules, setModules] = useState<Module[]>([])

  // Ladezustand — zeigt "Laden..." während der API-Call läuft
  const [loading, setLoading] = useState(true)

  // Fehlermeldung falls die API nicht erreichbar ist
  const [error, setError] = useState<string | null>(null)

  // Steuert ob das "Neues Modul"-Formular sichtbar ist
  const [showForm, setShowForm] = useState(false)

  // Formular-Daten für ein neues Modul
  const [newModule, setNewModule] = useState<ModuleCreate>({
    name: '',
    description: '',
    color: '#4a90d9',
  })

  // --- API-Aufrufe ---

  // Module laden — wird beim ersten Rendern aufgerufen (useEffect)
  async function loadModules() {
    try {
      setLoading(true)
      setError(null)
      // GET /api/modules/ → Liste aller Module
      const data = await get<Module[]>('/api/modules/')
      setModules(data)
    } catch (err) {
      // Fehler abfangen (z.B. Backend nicht gestartet)
      setError(err instanceof Error ? err.message : 'Fehler beim Laden')
    } finally {
      // Ladezustand beenden, egal ob Erfolg oder Fehler
      setLoading(false)
    }
  }

  // useEffect mit leerem Array [] = wird nur EINMAL ausgeführt
  // beim ersten Rendern der Komponente (wie componentDidMount)
  useEffect(() => {
    loadModules()
  }, [])

  // Neues Modul erstellen — wird beim Absenden des Formulars aufgerufen
  async function createModule() {
    try {
      // POST /api/modules/ mit den Formulardaten
      await post('/api/modules/', newModule)

      // Formular zurücksetzen und schliessen
      setNewModule({ name: '', description: '', color: '#4a90d9' })
      setShowForm(false)

      // Module neu laden damit das neue Modul in der Liste erscheint
      await loadModules()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Erstellen')
    }
  }

  // Modul löschen — wird beim Klick auf den Löschen-Button aufgerufen
  async function deleteModule(id: number, event: React.MouseEvent) {
    // stopPropagation verhindert dass der Klick auf "Löschen"
    // auch den Link zur Detailseite auslöst
    event.preventDefault()
    event.stopPropagation()

    try {
      // DELETE /api/modules/{id}
      await del(`/api/modules/${id}`)

      // Module neu laden
      await loadModules()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Löschen')
    }
  }

  // --- Render ---

  return (
    <div>
      {/* Header mit Titel und "Neues Modul"-Button */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Dashboard</h1>

        {/* Button toggelt das Formular */}
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-white/10 hover:bg-white/20 px-4 py-2 rounded-lg transition-colors"
        >
          {showForm ? 'Abbrechen' : '+ Neues Modul'}
        </button>
      </div>

      {/* Formular für neues Modul — nur sichtbar wenn showForm = true */}
      {showForm && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Neues Modul erstellen</h2>

          {/* Name */}
          <div className="mb-4">
            <label className="block text-sm text-gray-400 mb-1">Name</label>
            <input
              type="text"
              value={newModule.name}
              onChange={(e) => setNewModule({ ...newModule, name: e.target.value })}
              placeholder="z.B. Lineare Algebra"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-gray-500"
            />
          </div>

          {/* Beschreibung */}
          <div className="mb-4">
            <label className="block text-sm text-gray-400 mb-1">Beschreibung</label>
            <input
              type="text"
              value={newModule.description}
              onChange={(e) => setNewModule({ ...newModule, description: e.target.value })}
              placeholder="z.B. Mathe Semester 2"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-gray-500"
            />
          </div>

          {/* Farbe */}
          <div className="mb-6">
            <label className="block text-sm text-gray-400 mb-1">Farbe</label>
            <div className="flex items-center gap-3">
              {/* Nativer Farbwähler */}
              <input
                type="color"
                value={newModule.color}
                onChange={(e) => setNewModule({ ...newModule, color: e.target.value })}
                className="w-10 h-10 rounded cursor-pointer bg-transparent"
              />
              {/* Hex-Code anzeigen */}
              <span className="text-gray-400 text-sm">{newModule.color}</span>
            </div>
          </div>

          {/* Absenden-Button — nur klickbar wenn Name ausgefüllt */}
          <button
            onClick={createModule}
            disabled={!newModule.name}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-2 rounded-lg transition-colors"
          >
            Modul erstellen
          </button>
        </div>
      )}

      {/* Fehlermeldung — rot, nur sichtbar wenn error gesetzt */}
      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Ladezustand */}
      {loading && (
        <p className="text-gray-400">Module werden geladen...</p>
      )}

      {/* Leerer Zustand — wenn keine Module vorhanden */}
      {!loading && modules.length === 0 && (
        <div className="text-center py-16">
          <p className="text-gray-500 text-lg mb-2">Noch keine Module vorhanden.</p>
          <p className="text-gray-600">Klicke auf "+ Neues Modul" um loszulegen.</p>
        </div>
      )}

      {/* Modul-Karten — Grid mit 1-3 Spalten je nach Bildschirmbreite */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map((module) => (
          <Link
            to={`/modules/${module.id}`}
            key={module.id}
            className="block bg-gray-900 border border-gray-800 rounded-lg p-5 hover:border-gray-700 transition-colors"
          >
            {/* Farbiger Balken oben — zeigt die Modul-Farbe */}
            <div
              className="h-1.5 rounded-full mb-4"
              style={{ backgroundColor: module.color }}
            />

            {/* Modul-Name */}
            <h3 className="text-lg font-semibold mb-1">{module.name}</h3>

            {/* Beschreibung */}
            <p className="text-gray-400 text-sm mb-4">{module.description}</p>

            {/* Aktions-Buttons */}
            <div className="flex items-center justify-between">
              {/* Erstellt-Datum */}
              <span className="text-xs text-gray-600">
                {new Date(module.created_at).toLocaleDateString('de-CH')}
              </span>

              {/* Löschen-Button — stopPropagation verhindert Navigation */}
              <button
                onClick={(e) => deleteModule(module.id, e)}
                className="text-xs text-red-400/50 hover:text-red-400 transition-colors"
              >
                Löschen
              </button>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

// Default Export — wird in App.tsx vom Router importiert
export default Dashboard