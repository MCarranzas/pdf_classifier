import { useEffect, useRef, useState } from 'react'
import { Download, FileWarning, Loader2, RefreshCw, XCircle } from 'lucide-react'
import * as pdfjsLib from 'pdfjs-dist'
import workerSrc from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { buscarPalabras, concatenarItems, resaltar } from '@/lib/pdfHighlights'

pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc

const COLOR_PALABRA = {
  FACTURA: 'rgba(249, 115, 22, 0.38)',
  CONTRATO: 'rgba(59, 130, 246, 0.38)',
  'FORMULARIO 110': 'rgba(16, 185, 129, 0.38)',
}

function CategoryBadge({ category }) {
  const labels = {
    FACTURA: 'outline',
    CONTRATO: 'default',
    'FORMULARIO 110': 'secondary',
  }
  return <Badge variant={labels[category] ?? 'default'}>{category ?? 'OTRO'}</Badge>
}

const ESTADO_LABELS = {
  PENDIENTE: 'Pendiente',
  APROBADO: 'Aprobado',
  RECHAZADO: 'Rechazado',
}

const ESTADO_VARIANTS = {
  PENDIENTE: 'destructive',
  APROBADO: 'outline',
  RECHAZADO: 'secondary',
}

function EstadoBadge({ estado }) {
  return (
    <Badge variant={ESTADO_VARIANTS[estado] ?? 'secondary'}>
      {ESTADO_LABELS[estado] ?? estado}
    </Badge>
  )
}

/** Pinta la primera pagina y devuelve los rectangulos de las palabras halladas. */
function usePrimeraPagina(datos, palabras, ancho, onError) {
  const canvasRef = useRef(null)
  const [rects, setRects] = useState([])
  const [totalPaginas, setTotalPaginas] = useState(0)

  useEffect(() => {
    if (!datos || !canvasRef.current) return

    let cancelado = false
    let pdf = null
    let tarea = null

    const pintar = async () => {
      try {
        pdf = await pdfjsLib.getDocument({ data: datos.slice(0) }).promise
        if (cancelado) return
        setTotalPaginas(pdf.numPages)

        const pagina = await pdf.getPage(1)
        if (cancelado) return
        const base = pagina.getViewport({ scale: 1 })
        const escala = ancho > 0 ? Math.min(ancho / base.width, 2) : 1
        const viewport = pagina.getViewport({ scale: escala })

        const canvas = canvasRef.current
        const dpr = Math.min(window.devicePixelRatio || 1, 2)
        canvas.width = Math.floor(viewport.width * dpr)
        canvas.height = Math.floor(viewport.height * dpr)
        canvas.style.width = `${Math.floor(viewport.width)}px`
        canvas.style.height = `${Math.floor(viewport.height)}px`

        const ctx = canvas.getContext('2d')
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
        tarea = pagina.render({ canvasContext: ctx, viewport })
        await tarea.promise
        if (cancelado) return

        const items = (await pagina.getTextContent()).items.filter((i) => i.str)
        const medidas = items.map((item) => {
          const tx = pdfjsLib.Util.transform(viewport.transform, item.transform)
          const alto = Math.hypot(tx[2], tx[3]) || 1
          const proporcion = item.width && item.height ? item.width / item.height : 1
          return { izquierda: tx[4], arriba: tx[5] - alto, ancho: proporcion * alto, alto }
        })

        const { crudo, inicios } = concatenarItems(items)
        const { coincidencias } = buscarPalabras(crudo, palabras)
        if (!cancelado) setRects(resaltar(items, medidas, inicios, coincidencias))
      } catch (err) {
        if (!cancelado && err?.name !== 'RenderingCancelledException') onError?.(err)
      }
    }

    setRects([])
    pintar()

    return () => {
      cancelado = true
      tarea?.cancel()
      pdf?.destroy?.()
    }
  }, [datos, palabras, ancho, onError])

  return { canvasRef, rects, totalPaginas }
}

export default function PdfViewerDialog({
  document: doc,
  token,
  onClose,
  onUnauthorized,
  onToggleRevision,
  onUpdateEstado,
  saving,
  savingEstado,
  // El panel de admin lee el PDF con las rutas /api/admin/documentos, que no
  // filtran por dueño. Por defecto se usan las del usuario.
  apiBase = '/api/documents',
  hideActions = false,
}) {
  const [datos, setDatos] = useState(null)
  const [url, setUrl] = useState(null)
  const [palabras, setPalabras] = useState([])
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [ancho, setAncho] = useState(0)
  const marcoRef = useRef(null)
  const docId = doc?.id

  useEffect(() => {
    if (!docId) return

    let cancelado = false
    let objectUrl = null

    const cargar = async () => {
      try {
        const [archivo, analisis] = await Promise.all([
          fetch(`${apiBase}/${docId}/archivo`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${apiBase}/${docId}/analisis`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ])
        if (archivo.status === 401 || analisis.status === 401) {
          onUnauthorized?.()
          return
        }
        const cuerpo = archivo.ok ? null : await archivo.json().catch(() => null)
        if (!archivo.ok) throw new Error(cuerpo?.detail ?? `Error ${archivo.status}`)
        if (!analisis.ok) throw new Error(`Error ${analisis.status}`)

        const blob = await archivo.blob()
        const datos = await analisis.json()
        if (cancelado) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
        setPalabras(datos.palabras ?? [])
        setDatos(await blob.arrayBuffer())
        setError(null)
      } catch (err) {
        if (!cancelado) setError(String(err.message ?? err))
      }
    }

    cargar()
    return () => {
      cancelado = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [docId, token, reloadKey, onUnauthorized, apiBase])

  useEffect(() => {
    const marco = marcoRef.current
    if (!marco) return
    const observer = new ResizeObserver(([entrada]) => setAncho(entrada.contentRect.width))
    observer.observe(marco)
    return () => observer.disconnect()
  }, [datos])

  const { canvasRef, rects, totalPaginas } = usePrimeraPagina(
    datos,
    palabras,
    ancho,
    setError,
  )
  const color = COLOR_PALABRA[doc?.clasificacion] ?? 'rgba(148, 163, 184, 0.45)'
  const halladas = new Set(rects.map((r) => r.palabra))

  return (
    <Dialog
      open={Boolean(doc)}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <DialogContent className="sm:max-w-4xl">
        {doc && (
          <>
            <DialogHeader>
              <DialogTitle className="pr-8 break-all">{doc.nombre_archivo}</DialogTitle>
              <DialogDescription className="flex flex-wrap items-center gap-2">
                <CategoryBadge category={doc.clasificacion} />
                <span>
                  Confianza{' '}
                  {doc.confianza == null ? '—' : `${Math.round(doc.confianza * 100)}%`}
                </span>
                <EstadoBadge estado={doc.estado} />
                <Badge variant={doc.requiere_revision ? 'secondary' : 'outline'}>
                  {doc.requiere_revision ? 'Revisión 1' : 'Revisión 0'}
                </Badge>
              </DialogDescription>
            </DialogHeader>

            {doc.motivo && (
              <p className="rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">{doc.motivo}</p>
            )}

            {palabras.length > 0 && !error && (
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-muted-foreground">Textos reconocidos:</span>
                {palabras.map((palabra) => (
                  <Badge
                    key={palabra}
                    variant={halladas.has(palabra) ? 'default' : 'ghost'}
                    className={halladas.has(palabra) ? '' : 'text-muted-foreground line-through'}
                  >
                    {palabra}
                  </Badge>
                ))}
              </div>
            )}

            <div
              ref={marcoRef}
              className="relative flex max-h-[70vh] min-h-80 items-start justify-center overflow-auto rounded-lg border bg-muted/30 p-2"
            >
              {error ? (
                <div className="flex flex-col items-center gap-3 p-8 text-center">
                  <FileWarning className="size-6 text-destructive" />
                  <p className="max-w-sm text-sm text-muted-foreground">{error}</p>
                  <Button variant="outline" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
                    <RefreshCw className="size-3.5" />
                    Reintentar
                  </Button>
                </div>
              ) : datos ? (
                <div className="relative shrink-0">
                  <canvas ref={canvasRef} className="rounded bg-white shadow-sm" />
                  {rects.map((rect, i) => (
                    <span
                      key={`${rect.palabra}-${i}`}
                      title={rect.palabra}
                      className="pointer-events-none absolute rounded-[2px]"
                      style={{
                        left: `${rect.x}px`,
                        top: `${rect.y}px`,
                        width: `${Math.max(rect.width, 2)}px`,
                        height: `${rect.height}px`,
                        backgroundColor: color,
                        mixBlendMode: 'multiply',
                      }}
                    />
                  ))}
                  {totalPaginas > 1 && (
                    <p className="mt-2 text-center text-xs text-muted-foreground">
                      Mostrando la página 1 de {totalPaginas} (es la única que se analiza)
                    </p>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="size-5 animate-spin text-muted-foreground" />
                </div>
              )}
            </div>

            {!hideActions && (
              <DialogFooter>
                {url && (
                  <Button variant="outline" asChild>
                    <a href={url} download={doc.nombre_archivo}>
                      <Download className="size-4" />
                      Descargar
                    </a>
                  </Button>
                )}
                <Button
                  variant="outline"
                  onClick={() => onUpdateEstado?.(doc, 'RECHAZADO')}
                  disabled={!doc.requiere_revision || saving}
                  title={
                    doc.requiere_revision
                      ? 'Rechazar documento'
                      : 'Solo los documentos con revisión pueden rechazarse'
                  }
                >
                  {savingEstado ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <XCircle className="size-4" />
                  )}
                  Rechazar
                </Button>
                <Button
                  variant={doc.requiere_revision ? 'default' : 'secondary'}
                  onClick={() => onToggleRevision(doc, !doc.requiere_revision)}
                  disabled={doc.estado !== 'PENDIENTE' || saving}
                  title={
                    doc.estado === 'PENDIENTE'
                      ? 'Cambiar el estado de revisión'
                      : `El estado ${doc.estado} es final y no admite más cambios`
                  }
                >
                  {saving && !savingEstado && <Loader2 className="size-4 animate-spin" />}
                  {doc.requiere_revision ? 'Marcar como revisado (0)' : 'Marcar con revisión (1)'}
                </Button>
              </DialogFooter>
            )}

            {hideActions && url && (
              <DialogFooter>
                <Button variant="outline" asChild>
                  <a href={url} download={doc.nombre_archivo}>
                    <Download className="size-4" />
                    Descargar
                  </a>
                </Button>
              </DialogFooter>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
