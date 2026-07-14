// EntryList — Journal-Einträge mit Suche und Sortierung
// SICHERHEIT: Zeigt nur Datum + Titel — kein Content in der Übersicht!
// Content wird erst sichtbar wenn man den Eintrag zum Bearbeiten öffnet

import { useState, useMemo } from 'react'
import { useLanguage } from '../../hooks/useLanguage'
import type { JournalEntry, JournalEntryCreate } from '../../types/models'
import EntryForm from './EntryForm'

interface EntryListProps {
  entries: JournalEntry[]
  editingId: number | null
  editEntry: JournalEntryCreate
  onStartEdit: (entry: JournalEntry) => void
  onSaveEdit: (data: JournalEntryCreate) => void
  onCancelEdit: () => void
  onDelete: (id: number) => void
  fullscreen?: boolean
  onToggleFullscreen?: () => void
}

function EntryList({
  entries, editingId, editEntry,
  onStartEdit, onSaveEdit, onCancelEdit, onDelete,
  fullscreen, onToggleFullscreen,
}: EntryListProps) {
  const { t } = useLanguage()
  const [search, setSearch] = useState('')
  const [sortNewest, setSortNewest] = useState(true)

  // Filtern + Sortieren
  const filtered = useMemo(() => {
    let result = entries
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(e =>
        e.title.toLowerCase().includes(q)
        || e.date.includes(q)
      )
    }
    return [...result].sort((a, b) => {
      // Primär: Tagesdatum (verschlüsselt in der DB → Sortierung erst nach dem Entschlüsseln)
      // Sekundär: created_at bricht den Gleichstand bei mehreren Einträgen am selben Tag
      const cmp = a.date.localeCompare(b.date)
        || a.created_at.localeCompare(b.created_at)
      return sortNewest ? -cmp : cmp
    })
  }, [entries, search, sortNewest])

  if (entries.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-lg mb-2" style={{ color: 'var(--color-text-muted)' }}>
          {t.entryList.emptyTitle}
        </p>
        <p style={{ color: 'var(--color-text-muted)', opacity: 0.6 }}>
          {t.entryList.emptyHint}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Suchfeld + Sort-Toggle */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={t.entryList.searchPlaceholder || 'Einträge suchen...'}
          className="hud-input text-sm flex-1"
        />
        <button
          onClick={() => setSortNewest(!sortNewest)}
          className="hud-btn text-xs px-2 py-1.5 flex items-center gap-1"
          title={sortNewest
            ? (t.entryList.sortOldest || 'Älteste zuerst')
            : (t.entryList.sortNewest || 'Neueste zuerst')}
        >
          {sortNewest ? '↓' : '↑'}
        </button>
      </div>

      {/* Ergebnis-Info bei aktiver Suche */}
      {search.trim() && (
        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
          {filtered.length} / {entries.length}
        </p>
      )}

      {/* Einträge */}
      {filtered.map(entry => (
        <div key={entry.id} className="hud-card p-4 animate-fade-in">
          {editingId === entry.id ? (
            <EntryForm
              initialData={editEntry}
              isEdit
              onSave={onSaveEdit}
              onCancel={onCancelEdit}
              fullscreen={fullscreen}
              onToggleFullscreen={onToggleFullscreen}
            />
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-xs"
                  style={{ color: 'var(--color-text-muted)' }}>
                  {entry.date}
                </span>
                <h3 className="text-sm font-medium"
                  style={{ color: 'var(--color-text-primary)' }}>
                  {entry.title}
                </h3>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => onStartEdit(entry)}
                  className="text-xs px-1.5 py-0.5 rounded transition-all duration-200
                    text-[var(--color-text-muted)] hover:text-[var(--color-primary)]
                    hover:bg-[rgba(125,216,232,0.1)]"
                  title={t.common.edit}
                >✎</button>
                <button
                  onClick={() => onDelete(entry.id)}
                  className="text-xs px-1.5 py-0.5 rounded transition-all duration-200
                    text-[var(--color-text-muted)] hover:text-[var(--color-danger)]
                    hover:bg-[rgba(255,59,92,0.1)]"
                  title={t.common.delete}
                >X</button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default EntryList
