import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const ESTADO_LABELS = {
  PENDIENTE: 'Pendiente',
  APROBADO: 'Aprobado',
  RECHAZADO: 'Rechazado',
}

const ACCION_LABELS = {
  APROBAR: 'Aprobado',
  RECHAZAR: 'Rechazado',
  PENDIENTE: 'Puesto en pendiente',
  ELIMINAR: 'Eliminado',
}

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('es-ES', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function errorMessage(data, status) {
  if (Array.isArray(data?.detail)) {
    return data.detail.map((item) => item.msg).join(', ')
  }
  return data?.detail ?? `Error ${status}`
}

/** Historial de observaciones de un documento.
 *
 * El mismo diálogo sirve para las dos vistas; solo cambia el endpoint:
 *   - Administración: apiBase="/api/admin/documentos" (ve cualquier documento).
 *   - Dueño:          apiBase="/api/documents" (el backend solo sirve los suyos).
 */
export default function HistorialDialog({
  documento,
  token,
  apiBase = '/api/admin/documentos',
  onClose,
  onUnauthorized,
}) {
  const [observaciones, setObservaciones] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!documento) return
    let cancelado = false
    setLoading(true)

    const cargar = async () => {
      try {
        const res = await fetch(`${apiBase}/${documento.id}/observaciones`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (res.status === 401) {
          onUnauthorized?.()
          return
        }
        const data = await res.json().catch(() => null)
        if (!res.ok) throw new Error(errorMessage(data, res.status))
        if (!cancelado) setObservaciones(data)
      } catch (err) {
        if (!cancelado) {
          toast.error('No se pudo cargar el historial', { description: String(err) })
          setObservaciones([])
        }
      } finally {
        if (!cancelado) setLoading(false)
      }
    }

    cargar()
    return () => {
      cancelado = true
    }
  }, [documento, token, apiBase, onUnauthorized])

  return (
    <Dialog open={Boolean(documento)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="break-all">Historial de observaciones</DialogTitle>
          <DialogDescription className="break-all">
            {documento?.nombre_archivo} · {documento?.usuario_nombre ?? 'sin dueño'}
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Loader2 className="size-5 animate-spin" />
          </div>
        ) : observaciones?.length ? (
          <ul className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
            {observaciones.map((obs) => (
              <li key={obs.id} className="rounded-lg border p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">{ACCION_LABELS[obs.accion] ?? obs.accion}</Badge>
                  {obs.estado_anterior && (
                    <span className="text-xs text-muted-foreground">
                      {ESTADO_LABELS[obs.estado_anterior] ?? obs.estado_anterior}
                      {' → '}
                      {obs.estado_nuevo
                        ? (ESTADO_LABELS[obs.estado_nuevo] ?? obs.estado_nuevo)
                        : 'eliminado'}
                    </span>
                  )}
                  <span className="ml-auto text-xs text-muted-foreground">
                    {formatDate(obs.created_at)}
                  </span>
                </div>
                <p className="mt-2">{obs.observacion}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  por {obs.admin_username}
                  {obs.usuario_username ? ` · dueño: ${obs.usuario_username}` : ''}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Este documento todavía no tiene observaciones.
          </p>
        )}
      </DialogContent>
    </Dialog>
  )
}
