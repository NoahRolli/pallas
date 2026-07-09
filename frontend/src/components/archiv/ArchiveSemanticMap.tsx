// ArchiveSemanticMap — semantische Karte der Archiv-Dokumente (Toggle "Semantisch").
// Laedt das vorberechnete 2D-Layout (GET /api/archive/layout) und rendert es als
// interaktive SVG-Karte: Cluster-Inseln (Hubs) + Dokument-Punkte, eingefaerbt nach
// cluster_id, Bruecken-Docs (silhouette < 0) abgesetzt. Zoom (Scroll), Pan (Ziehen),
// Hover-Tooltip mit Titel.
//
// SVG statt Canvas: ~1350 Knoten sind unkritisch, Hover/Click gratis via DOM-Events.
// Perf: die teure Punkt-Ebene (1254 Kreise) ist memoisiert -> bei Zoom/Pan aendert
// sich nur die <g>-Transform, die Kreise werden nicht neu gerendert.

import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { get } from '../../hooks/useAPI'
import { useLanguage } from '../../hooks/useLanguage'
import type { ArchiveLayout } from '../../types/archive'

const SVG_W = 1000
const SVG_H = 640
const PAD = 60
const LABEL_ZOOM = 1.8          // ab diesem Zoom Hub-Labels einblenden
const MIN_K = 0.4
const MAX_K = 12

// Stabile Farbe pro Cluster (golden angle -> gute Streuung im Farbkreis).
function clusterColor(id: number | null): string {
  if (id == null) return '#888888'
  return `hsl(${(id * 137.508) % 360}, 62%, 58%)`
}

interface Tip { x: number; y: number; text: string; sub?: string }

export default function ArchiveSemanticMap() {
  const { t } = useLanguage()
  const [data, setData] = useState<ArchiveLayout | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tf, setTf] = useState({ k: 1, x: 0, y: 0 })
  const [tip, setTip] = useState<Tip | null>(null)
  const svgRef = useRef<SVGSVGElement | null>(null)
  const drag = useRef<{ x: number; y: number } | null>(null)

  useEffect(() => {
    get<ArchiveLayout>('/api/archive/layout')
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : 'Fehler'))
  }, [])

  // Datengrenzen -> Projektion in den viewBox (Aspect erhalten, y gespiegelt).
  const proj = useMemo(() => {
    if (!data) return null
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
    const add = (x: number | null, y: number | null) => {
      if (x == null || y == null) return
      minX = Math.min(minX, x); maxX = Math.max(maxX, x)
      minY = Math.min(minY, y); maxY = Math.max(maxY, y)
    }
    data.documents.forEach((d) => add(d.proj_x, d.proj_y))
    data.clusters.forEach((c) => add(c.hub_x, c.hub_y))
    const w = maxX - minX || 1, h = maxY - minY || 1
    const s = Math.min((SVG_W - 2 * PAD) / w, (SVG_H - 2 * PAD) / h)
    const offX = (SVG_W - s * w) / 2, offY = (SVG_H - s * h) / 2
    return {
      px: (x: number) => offX + (x - minX) * s,
      py: (y: number) => offY + (maxY - y) * s,   // y spiegeln (oben = positiv)
    }
  }, [data])

  // Client-Koordinaten -> viewBox-Koordinaten (beruecksichtigt Groesse + viewBox).
  const toSvg = useCallback((cx: number, cy: number) => {
    const svg = svgRef.current
    if (!svg) return { x: 0, y: 0 }
    const pt = svg.createSVGPoint()
    pt.x = cx; pt.y = cy
    const ctm = svg.getScreenCTM()
    if (!ctm) return { x: 0, y: 0 }
    const p = pt.matrixTransform(ctm.inverse())
    return { x: p.x, y: p.y }
  }, [])

  // Zoom auf den Cursor. Nativer Listener mit passive:false, sonst blockt React
  // preventDefault nicht und die Seite scrollt beim Zoomen mit.
  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    const handler = (e: WheelEvent) => {
      e.preventDefault()
      const p = toSvg(e.clientX, e.clientY)
      setTf((prev) => {
        const factor = Math.exp(-e.deltaY * 0.0015)
        const k = Math.min(MAX_K, Math.max(MIN_K, prev.k * factor))
        const wx = (p.x - prev.x) / prev.k
        const wy = (p.y - prev.y) / prev.k
        return { k, x: p.x - wx * k, y: p.y - wy * k }
      })
    }
    svg.addEventListener('wheel', handler, { passive: false })
    return () => svg.removeEventListener('wheel', handler)
  }, [toSvg, data])

  const onDown = useCallback((e: React.MouseEvent) => {
    drag.current = toSvg(e.clientX, e.clientY)
  }, [toSvg])

  const onMove = useCallback((e: React.MouseEvent) => {
    if (!drag.current) return
    const p = toSvg(e.clientX, e.clientY)
    const start = drag.current
    setTf((prev) => ({ k: prev.k, x: prev.x + (p.x - start.x), y: prev.y + (p.y - start.y) }))
    drag.current = p
  }, [toSvg])

  const onUp = useCallback(() => { drag.current = null }, [])

  // Teure Punkt-Ebene: memoisiert, unabhaengig von Zoom/Pan.
  const points = useMemo(() => {
    if (!data || !proj) return null
    return data.documents.map((d) => {
      if (d.proj_x == null || d.proj_y == null) return null
      const bridge = (d.silhouette ?? 0) < 0
      const color = clusterColor(d.cluster_id)
      return (
        <circle
          key={d.id}
          cx={proj.px(d.proj_x)}
          cy={proj.py(d.proj_y)}
          r={bridge ? 3.2 : 3}
          fill={color}
          fillOpacity={bridge ? 0.28 : 0.85}
          stroke={bridge ? color : 'none'}
          strokeWidth={bridge ? 0.8 : 0}
          style={{ cursor: 'pointer' }}
          onMouseEnter={(e) => setTip({ x: e.clientX, y: e.clientY, text: d.title })}
          onMouseLeave={() => setTip(null)}
        />
      )
    })
  }, [data, proj])

  // Hub-Marker (Inseln): memoisiert, Radius ~ sqrt(size).
  const hubs = useMemo(() => {
    if (!data || !proj) return null
    return data.clusters.map((c) => {
      if (c.hub_x == null || c.hub_y == null) return null
      const color = clusterColor(c.cluster_id)
      const r = 4 + Math.sqrt(c.size ?? 1) * 1.4
      return (
        <circle
          key={`h-${c.cluster_id}`}
          cx={proj.px(c.hub_x)}
          cy={proj.py(c.hub_y)}
          r={r}
          fill={color}
          fillOpacity={0.18}
          stroke={color}
          strokeWidth={1.2}
          style={{ cursor: 'pointer' }}
          onMouseEnter={(e) => setTip({
            x: e.clientX, y: e.clientY,
            text: c.label ?? `Cluster ${c.cluster_id}`, sub: `${c.size ?? 0} ${t.archiv.semantic.docs}`,
          })}
          onMouseLeave={() => setTip(null)}
        />
      )
    })
  }, [data, proj])

  // Hub-Labels: nur ab LABEL_ZOOM (100 Stueck, guenstig, reagiert auf Zoom/Pan).
  const labels = tf.k >= LABEL_ZOOM && data && proj
    ? data.clusters.map((c) =>
        c.hub_x == null || c.hub_y == null || !c.label ? null : (
          <text
            key={`l-${c.cluster_id}`}
            x={proj.px(c.hub_x)}
            y={proj.py(c.hub_y) - (7 + Math.sqrt(c.size ?? 1) * 1.4)}
            textAnchor="middle"
            fontSize={11}
            fill="var(--color-text-secondary)"
            style={{ pointerEvents: 'none' }}
          >
            {c.label}
          </text>
        ))
    : null

  if (error) {
    return (
      <div className="hud-card p-6" style={{ color: 'var(--color-danger)' }}>
        {t.archiv.semantic.loadError}: {error}
      </div>
    )
  }
  if (!data) {
    return (
      <div className="hud-card p-6" style={{ color: 'var(--color-text-muted)' }}>
        {t.archiv.semantic.loading}
      </div>
    )
  }

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-3 text-xs"
        style={{ color: 'var(--color-text-muted)' }}>
        <span>
          {data.counts.documents} {t.archiv.semantic.documents} · {data.counts.clusters} {t.archiv.semantic.clusters} · {t.archiv.semantic.hint}
        </span>
        <button onClick={() => setTf({ k: 1, x: 0, y: 0 })} className="hud-btn text-xs">
          {t.archiv.semantic.resetView}
        </button>
      </div>
      <div className="hud-card" style={{ overflow: 'hidden' }}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          width="100%"
          style={{ display: 'block', height: '70vh', cursor: 'grab',
            touchAction: 'none', userSelect: 'none' }}
          onMouseDown={onDown}
          onMouseMove={onMove}
          onMouseUp={onUp}
          onMouseLeave={onUp}
        >
          <g transform={`translate(${tf.x},${tf.y}) scale(${tf.k})`}>
            {hubs}
            {points}
            {labels}
          </g>
        </svg>
      </div>
      {tip && (
        <div style={{
          position: 'fixed', left: tip.x + 14, top: tip.y + 14, zIndex: 50,
          background: 'var(--color-bg-elevated, rgba(18,18,28,0.96))',
          border: '1px solid var(--color-border)', borderRadius: 8,
          padding: '6px 10px', pointerEvents: 'none', maxWidth: 320,
          color: 'var(--color-text-primary)', fontSize: 12,
        }}>
          <div style={{ fontWeight: 600 }}>{tip.text}</div>
          {tip.sub && <div style={{ color: 'var(--color-text-muted)' }}>{tip.sub}</div>}
        </div>
      )}
    </div>
  )
}
