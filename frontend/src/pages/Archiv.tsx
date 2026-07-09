// Archiv — Ordner-Hierarchie mit DnD, Pin, Inline-Edit
import PageProviderBadge from "../components/PageProviderBadge"// Nutzt useArchiv Hook für State und Logik

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import { useArchiv } from '../hooks/useArchiv'
import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import { SortableContext, rectSortingStrategy, arrayMove } from '@dnd-kit/sortable'
import type { DragEndEvent, DragStartEvent } from '@dnd-kit/core'
import DraggableCard from '../components/DraggableCard'
import DroppableFolder from '../components/DroppableFolder'
import DroppableBreadcrumb from '../components/DroppableBreadcrumb'
import ArchivForms from '../components/archiv/ArchivForms'
import ArchivDocuments from '../components/archiv/ArchivDocuments'
import ArchiveSemanticMap from '../components/archiv/ArchiveSemanticMap'
import SortDropdown from '../components/SortDropdown'
import { useDocumentSort } from '../hooks/useDocumentSort'
import type { ModuleCreate } from '../types/models'

function Archiv() {
  const { t } = useLanguage()
  const db = useArchiv()
  const [dragLabel, setDragLabel] = useState<string | null>(null)
  const [showFolderForm, setShowFolderForm] = useState(false)
  const [showModuleForm, setShowModuleForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [view, setView] = useState<'folders' | 'semantic'>('folders')

  const folderSort = useDocumentSort(db.folders, {
    dateField: "created_at",
    nameField: (f) => f.name,
    defaultMode: "manual",
    allowManual: true,
  })
  const moduleSort = useDocumentSort(db.modules, {
    dateField: "created_at",
    nameField: (m) => m.name,
    defaultMode: "manual",
    allowManual: true,
  })

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  // --- Inline-Edit ---
  function startEdit(type: 'folder' | 'module', id: number, name: string) {
    setEditingId(`${type}-${id}`)
    setEditName(name)
  }

  async function saveEdit() {
    if (!editingId || !editName.trim()) { setEditingId(null); return }
    try {
      if (editingId.startsWith('folder-')) {
        await db.updateFolder(parseInt(editingId.replace('folder-', '')), { name: editName.trim() })
      } else {
        await db.renameModule(parseInt(editingId.replace('module-', '')), editName.trim())
      }
    } catch { /* Fehler im Hook */ }
    setEditingId(null)
  }

  // --- DnD ---
  function handleDragStart(event: DragStartEvent) {
    const id = String(event.active.id)
    if (id.startsWith('folder-')) {
      const f = db.folders.find((f) => f.id === parseInt(id.replace('folder-', '')))
      setDragLabel(f ? f.name : null)
    } else if (id.startsWith('module-')) {
      const m = db.modules.find((m) => m.id === parseInt(id.replace('module-', '')))
      setDragLabel(m ? m.name : null)
    }
  }

  async function handleDragEnd(event: DragEndEvent) {
    setDragLabel(null)
    const { active, over } = event
    if (!over || active.id === over.id) return
    const draggedId = String(active.id)
    const targetId = String(over.id)

    // In Ordner verschieben
    if (targetId.startsWith('drop-folder-')) {
      const targetFolderId = parseInt(targetId.replace('drop-folder-', ''))
      try { await db.moveToFolder(draggedId, targetFolderId) }
      catch { db.setError(t.archiv.moveFailed) }
      return
    }

    // In Breadcrumb (hoehere Ebene oder Root) verschieben
    if (targetId === 'drop-breadcrumb-root') {
      try { await db.moveToFolder(draggedId, null) }
      catch { db.setError(t.archiv.moveFailed) }
      return
    }
    if (targetId.startsWith('drop-breadcrumb-')) {
      const targetFolderId = parseInt(targetId.replace('drop-breadcrumb-', ''))
      try { await db.moveToFolder(draggedId, targetFolderId) }
      catch { db.setError(t.archiv.moveFailed) }
      return
    }

    // Reihenfolge aendern (Sortable) — nur wenn beide Sort-Modi auf 'manual' stehen
    if (folderSort.mode !== 'manual' || moduleSort.mode !== 'manual') return

    if (draggedId.startsWith('folder-') && targetId.startsWith('folder-')) {
      const oldIdx = db.folders.findIndex((f) => `folder-${f.id}` === draggedId)
      const newIdx = db.folders.findIndex((f) => `folder-${f.id}` === targetId)
      if (oldIdx !== -1 && newIdx !== -1) {
        const sorted = arrayMove(db.folders, oldIdx, newIdx)
        await db.saveSortOrder(sorted, db.modules)
      }
    } else if (draggedId.startsWith('module-') && targetId.startsWith('module-')) {
      const oldIdx = db.modules.findIndex((m) => `module-${m.id}` === draggedId)
      const newIdx = db.modules.findIndex((m) => `module-${m.id}` === targetId)
      if (oldIdx !== -1 && newIdx !== -1) {
        const sorted = arrayMove(db.modules, oldIdx, newIdx)
        await db.saveSortOrder(db.folders, sorted)
      }
    }
  }

  // --- Formular-Callbacks ---
  async function handleCreateFolder(name: string) {
    try { await db.createFolder(name); setShowFolderForm(false) }
    catch (err) { db.setError(err instanceof Error ? err.message : t.common.error) }
  }

  async function handleCreateModule(data: ModuleCreate) {
    try { await db.createModule(data); setShowModuleForm(false) }
    catch (err) { db.setError(err instanceof Error ? err.message : t.common.error) }
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3"><h1 className="hud-title text-glow text-2xl">{t.archiv.title}</h1><PageProviderBadge page="archiv" /></div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <button onClick={() => setView('folders')} className="hud-btn text-xs"
              style={{ color: view === 'folders' ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>
              {t.archiv.semantic.viewFolders}
            </button>
            <button onClick={() => setView('semantic')} className="hud-btn text-xs"
              style={{ color: view === 'semantic' ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>
              {t.archiv.semantic.viewSemantic}
            </button>
          </div>
          {view === 'folders' && (
            <>
              <button onClick={() => { setShowFolderForm(!showFolderForm); setShowModuleForm(false) }} className="hud-btn">
                {showFolderForm ? t.common.cancel : t.archiv.newFolder}
              </button>
              <button onClick={() => { setShowModuleForm(!showModuleForm); setShowFolderForm(false) }} className="hud-btn">
                {showModuleForm ? t.common.cancel : t.archiv.newModule}
              </button>
            </>
          )}
        </div>
      </div>

      {view === 'folders' && (
      <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>

      {/* Breadcrumbs (auch Drop-Targets fuer Folder-Verschiebung) */}
      <div className="flex items-center gap-2 mb-6 text-xs flex-wrap">
        <DroppableBreadcrumb id="drop-breadcrumb-root">
          <button onClick={db.goToRoot} className="transition-colors"
            style={{ color: db.currentFolderId === null ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>
            {t.sidebar.archiv}
          </button>
        </DroppableBreadcrumb>
        {db.breadcrumbs.map((crumb, i) => (
          <span key={crumb.id} className="flex items-center gap-2">
            <span style={{ color: 'var(--color-border)' }}>/</span>
            <DroppableBreadcrumb id={`drop-breadcrumb-${crumb.id}`}>
              <button onClick={() => db.goToBreadcrumb(crumb.id)} className="transition-colors"
                style={{ color: i === db.breadcrumbs.length - 1 ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>
                {crumb.name}
              </button>
            </DroppableBreadcrumb>
          </span>
        ))}
      </div>

      {db.error && (
        <div className="px-4 py-3 rounded-lg mb-6 border"
          style={{ background: 'rgba(255,59,92,0.1)', borderColor: 'rgba(255,59,92,0.3)', color: 'var(--color-danger)' }}>
          {db.error}
        </div>
      )}

      {/* Formulare */}
      <ArchivForms
        showFolderForm={showFolderForm}
        showModuleForm={showModuleForm}
        onCreateFolder={handleCreateFolder}
        onCreateModule={handleCreateModule}
      />


      {/* Lose Dokumente + Upload-Zone */}
      <ArchivDocuments folderId={db.currentFolderId}
        documents={db.documents} onReload={db.loadContents} />

      {db.loading && <p style={{ color: 'var(--color-text-muted)' }}>{t.common.loading}</p>}

      {!db.loading && db.folders.length === 0 && db.modules.length === 0 && db.documents.length === 0 && (
        <div className="text-center py-16">
          <p className="text-lg mb-2" style={{ color: 'var(--color-text-muted)' }}>
            {db.currentFolderId === null ? t.archiv.emptyRoot : t.archiv.emptyFolder}
          </p>
          <p style={{ color: 'var(--color-text-muted)', opacity: 0.6 }}>{t.archiv.emptyHint}</p>
        </div>
      )}

      {/* Sort-Toolbar — nur wenn Folders/Modules vorhanden */}
      {(db.folders.length > 0 || db.modules.length > 0) && (
        <div className="flex items-center gap-4 mb-4 flex-wrap">
          {db.folders.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                {t.archiv.foldersLabel || 'Ordner'}:
              </span>
              <SortDropdown mode={folderSort.mode} onChange={folderSort.setMode} showManual={folderSort.hasManual} />
            </div>
          )}
          {db.modules.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                {t.archiv.modulesLabel || 'Module'}:
              </span>
              <SortDropdown mode={moduleSort.mode} onChange={moduleSort.setMode} showManual={moduleSort.hasManual} />
            </div>
          )}
        </div>
      )}

      {/* DnD Grid */}
        <SortableContext items={[...folderSort.sorted.map(f => `folder-${f.id}`), ...moduleSort.sorted.map(m => `module-${m.id}`)]}
          strategy={rectSortingStrategy}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Ordner */}
            {folderSort.sorted.map((folder) => (
              <DraggableCard key={`folder-${folder.id}`} id={`folder-${folder.id}`} type="folder" disabled={folderSort.mode !== "manual"}>
                <DroppableFolder id={`drop-folder-${folder.id}`}>
                  <div onClick={() => editingId !== `folder-${folder.id}` && db.openFolder(folder.id)}
                    className="hud-card p-5 cursor-pointer">
                    <div className="flex items-center gap-3 mb-2">
                      {folder.is_pinned && <span className="text-xs" style={{ color: 'var(--color-primary)' }}>&#9650;</span>}
                      {editingId === `folder-${folder.id}` ? (
                        <input className="hud-input text-sm py-1" value={editName}
                          onChange={(e) => setEditName(e.target.value)} autoFocus
                          onBlur={saveEdit} onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') setEditingId(null) }}
                          onClick={(e) => e.stopPropagation()} />
                      ) : (
                        <h3 className="text-base font-semibold" style={{ color: 'var(--color-text-primary)' }}>{folder.name}</h3>
                      )}
                    </div>
                    {folder.description && (
                      <p className="text-xs pl-0 mb-1" style={{ color: 'var(--color-text-muted)' }}>{folder.description}</p>
                      )}
                    <div className="flex items-center justify-between">
                      <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        {new Date(folder.created_at).toLocaleDateString('de-CH')}
                      </span>
                      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        <button onClick={() => db.togglePinFolder(folder.id)}
                          className={`text-xs px-1.5 py-0.5 rounded transition-all duration-200 hover:text-[var(--color-primary)] ${folder.is_pinned ? "text-[var(--color-primary)]" : "text-[var(--color-text-muted)]"}`}
                          title="Pin">&#9650;</button>
                        <button onClick={() => db.toggleMetisFolder(folder.id)}
                          className={`text-xs px-1.5 py-0.5 rounded transition-all duration-200 hover:text-[var(--color-primary)] ${folder.metis_enabled ? "text-[var(--color-primary)]" : "text-[var(--color-text-muted)]"}`}
                          title="Metis Sphäre">&#9673;</button>
                        <button onClick={() => startEdit('folder', folder.id, folder.name)}
                          className="text-xs px-1.5 py-0.5 rounded transition-all duration-200 text-[var(--color-text-muted)] hover:text-[var(--color-primary)]"
                          title={t.common.edit}>&#9998;</button>
                        <button onClick={() => db.deleteFolder(folder.id)}
                          className="text-xs px-1.5 py-0.5 rounded transition-all duration-200 text-[var(--color-text-muted)] hover:text-[var(--color-danger)] hover:bg-[rgba(255,59,92,0.1)]"
                          title={t.common.delete}>X</button>
                      </div>
                    </div>
                  </div>
                </DroppableFolder>
              </DraggableCard>
            ))}

            {/* Module */}
            {moduleSort.sorted.map((module) => (
              <DraggableCard key={`module-${module.id}`} id={`module-${module.id}`} type="module" disabled={moduleSort.mode !== "manual"}>
                <Link to={editingId === `module-${module.id}` ? '#' : `/modules/${module.id}`} className="hud-card p-5 block">
                  <div className="flex items-center gap-3 mb-2">
                    {module.is_pinned && <span className="text-xs" style={{ color: 'var(--color-primary)' }}>&#9650;</span>}
                    {editingId === `module-${module.id}` ? (
                      <input className="hud-input text-sm py-1" value={editName}
                        onChange={(e) => setEditName(e.target.value)} autoFocus
                        onBlur={saveEdit} onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') setEditingId(null) }}
                        onClick={(e) => e.preventDefault()} />
                    ) : (
                      <h3 className="text-base font-semibold" style={{ color: 'var(--color-text-primary)' }}>{module.name}</h3>
                    )}
                  </div>
                  <p className="text-sm mb-3 pl-8" style={{ color: 'var(--color-text-secondary)' }}>{module.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      {new Date(module.created_at).toLocaleDateString('de-CH')}
                    </span>
                    <div className="flex items-center gap-2" onClick={(e) => e.preventDefault()}>
                      <button onClick={(e) => { e.preventDefault(); db.togglePinModule(module.id) }}
                        className="text-xs px-1.5 py-0.5 rounded transition-all duration-200"
                        style={{ color: module.is_pinned ? 'var(--color-primary)' : 'var(--color-text-muted)' }}
                        title="Pin">&#9650;</button>
                      <button onClick={(e) => { e.preventDefault(); startEdit('module', module.id, module.name) }}
                        className="text-xs px-1.5 py-0.5 rounded transition-all duration-200 text-[var(--color-text-muted)] hover:text-[var(--color-primary)]"
                        title={t.common.edit}>&#9998;</button>
                      <button onClick={(e) => { e.preventDefault(); db.deleteModule(module.id) }}
                        className="text-xs px-1.5 py-0.5 rounded transition-all duration-200 text-[var(--color-text-muted)] hover:text-[var(--color-danger)] hover:bg-[rgba(255,59,92,0.1)]"
                        title={t.common.delete}>X</button>
                    </div>
                  </div>
                </Link>
              </DraggableCard>
            ))}
          </div>
        </SortableContext>

        <DragOverlay>
          {dragLabel && (
            <div className="hud-card px-4 py-3 text-sm font-medium"
              style={{ color: 'var(--color-primary)', boxShadow: '0 0 30px var(--color-highlight-strong)', pointerEvents: 'none' }}>
              {dragLabel}
            </div>
          )}
        </DragOverlay>
      </DndContext>
      )}

      {view === 'semantic' && <ArchiveSemanticMap />}
    </div>
  )
}

export default Archiv
