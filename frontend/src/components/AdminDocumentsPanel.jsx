import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import {
  CheckCircle2,
  Clock,
  Eye,
  History,
  Loader2,
  Search,
  Shield,
  Trash2,
  XCircle,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import HistorialDialog from '@/components/HistorialDialog'

const API = '/api/admin/documentos'

// Mismo criterio que App.jsx: el visor arrastra pdf.js (~1 MB) y aqui solo se
// necesita al abrir un documento.
const PdfViewerDialogLazy = lazy(() => import('@/components/PdfViewerDialog'))

const ESTADO_LABELS = {
  PENDIENTE: 'Pendiente',
  APROBADO: 'Aprobado',
  RECHAZADO: 'Rechazado',
}

const ESTADO_VARIANTS = {
  PENDIENTE: 'default',
  APROBADO: 'outline',
  RECHAZADO: 'destructive',
}

const OBSERVACION_MIN = 3

// Debe coincidir con PAGINA_POR_DEFECTO del backend.
const POR_PAGINA = 25
const OPCIONES_PAGINA = [10, 25, 50, 100]

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('es-ES', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function CategoryBadge({ category }) {
  const labels = {
    FACTURA: 'outline',
    CONTRATO: 'default',
    'FORMULARIO 110': 'secondary',
  }
  return <Badge variant={labels[category] ?? 'default'}>{category ?? 'OTRO'}</Badge>
}

function EstadoBadge({ estado }) {
  return (
    <Badge variant={ESTADO_VARIANTS[estado] ?? 'secondary'}>
      {ESTADO_LABELS[estado] ?? estado}
    </Badge>
  )
}

function errorMessage(data, status) {
  if (Array.isArray(data?.detail)) {
    return data.detail.map((item) => item.msg).join(', ')
  }
  return data?.detail ?? `Error ${status}`
}

/** Diálogo que pide la observación antes de ejecutar una acción. Es el punto
 * único por donde pasan aprobar, rechazar, poner en pendiente y eliminar. */
function AccionDialog({
  accion,
  documento,
  onClose,
  onConfirm,
  saving,
}) {
  const [observacion, setObservacion] = useState('')
  const [error, setError] = useState(null)

  useEffect(() => {
    setObservacion('')
    setError(null)
  }, [accion, documento?.id])

  if (!accion || !documento) return null

  const largo = observacion.trim().length
  const valida = largo >= OBSERVACION_MIN

  const confirmar = (e) => {
    e.preventDefault()
    if (!valida) {
      setError(`La observación debe tener al menos ${OBSERVACION_MIN} caracteres.`)
      return
    }
    onConfirm(observacion.trim())
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={confirmar} className="space-y-4">
          <DialogHeader>
            <DialogTitle>{accion.titulo}</DialogTitle>
            <DialogDescription className="break-all">
              {documento.nombre_archivo} · {documento.usuario_nombre ?? 'sin dueño'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2">
            <Label htmlFor="admin-observacion">Observación (obligatoria)</Label>
            <Textarea
              id="admin-observacion"
              value={observacion}
              onChange={(e) => {
                setObservacion(e.target.value)
                setError(null)
              }}
              placeholder={accion.placeholder}
              rows={4}
              maxLength={1000}
              autoFocus
              aria-invalid={Boolean(error)}
            />
            <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
              {error ? (
                <span className="text-destructive">{error}</span>
              ) : (
                <span>Se guarda en la base de datos como bitácora.</span>
              )}
              <span className={valida ? '' : 'text-muted-foreground'}>
                {largo}/{1000}
              </span>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose} disabled={saving}>
              Cancelar
            </Button>
            <Button
              type="submit"
              variant={accion.destructiva ? 'destructive' : 'default'}
              disabled={!valida || saving}
            >
              {saving && <Loader2 className="size-4 animate-spin" />}
              {accion.confirmar}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function AdminDocumentsPanel({ token, onUnauthorized, onChanged }) {
  const [documentos, setDocumentos] = useState([])
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtroEstado, setFiltroEstado] = useState('TODOS')
  const [filtroUsuario, setFiltroUsuario] = useState('TODOS')
  const [texto, setTexto] = useState('')
  const [pagina, setPagina] = useState(1)
  const [porPagina, setPorPagina] = useState(POR_PAGINA)
  const [total, setTotal] = useState(0)
  // Los contadores del resumen son globales, no de la pagina visible.
  const [pendientesTotal, setPendientesTotal] = useState(0)

  const [accion, setAccion] = useState(null)
  const [saving, setSaving] = useState(false)
  const [viewerDoc, setViewerDoc] = useState(null)
  const [historialDoc, setHistorialDoc] = useState(null)
  // Se incrementa tras cada acción para refrescar los contadores globales.
  const [refreshKey, setRefreshKey] = useState(0)

  const authHeaders = useMemo(
    () => ({ Authorization: `Bearer ${token}` }),
    [token]
  )

  const loadDocumentos = useCallback(async () => {
    const params = new URLSearchParams()
    if (filtroEstado !== 'TODOS') params.set('estado', filtroEstado)
    if (filtroUsuario !== 'TODOS') params.set('usuario_id', filtroUsuario)
    if (texto.trim()) params.set('texto', texto.trim())
    params.set('pagina', String(pagina))
    params.set('por_pagina', String(porPagina))

    try {
      const res = await fetch(`${API}?${params}`, { headers: authHeaders })
      if (res.status === 401) {
        onUnauthorized?.()
        return
      }
      const data = await res.json().catch(() => null)
      if (!res.ok) throw new Error(errorMessage(data, res.status))
      setDocumentos(data.documentos ?? [])
      setTotal(data.total ?? 0)
      setPendientesTotal(
        (data.documentos ?? []).filter((d) => d.estado === 'PENDIENTE').length
      )
      // Si la ultima pagina se vacio al borrar o filtrar, retrocede.
      if ((data.documentos ?? []).length === 0 && data.total > 0 && pagina > 1) {
        setPagina(Math.max(1, Math.ceil(data.total / porPagina)))
      }
    } catch (err) {
      toast.error('No se pudieron cargar los documentos', { description: String(err) })
    } finally {
      setLoading(false)
    }
  }, [authHeaders, filtroEstado, filtroUsuario, texto, pagina, porPagina, onUnauthorized])

  useEffect(() => {
    loadDocumentos()
  }, [loadDocumentos])

  // Los pendientes son globales: se piden aparte para no contar solo la pagina.
  useEffect(() => {
    const cargarResumen = async () => {
      try {
        const res = await fetch(`${API}/resumen`, { headers: authHeaders })
        if (res.status === 401) {
          onUnauthorized?.()
          return
        }
        if (!res.ok) return
        const data = await res.json().catch(() => null)
        const pendiente = (data?.por_estado ?? []).find((e) => e.estado === 'PENDIENTE')
        setPendientesTotal(pendiente?.total ?? 0)
      } catch {
        // El contador es informativo: si falla, se deja el de la pagina.
      }
    }
    cargarResumen()
  }, [authHeaders, onUnauthorized, onChanged, refreshKey])

  // Cambiar un filtro vuelve a la primera pagina: si no, se puede caer en una
  // pagina vacia.
  const aplicarFiltro = (setter) => (valor) => {
    setPagina(1)
    setter(valor)
  }

  useEffect(() => {
    const cargarUsuarios = async () => {
      try {
        const res = await fetch('/api/admin/users', { headers: authHeaders })
        if (res.status === 401) {
          onUnauthorized?.()
          return
        }
        if (!res.ok) return
        setUsuarios(await res.json())
      } catch {
        // El filtro por usuario es opcional: si falla, se deja la lista sin filtrar.
      }
    }
    cargarUsuarios()
  }, [authHeaders, onUnauthorized])

  const ACCIONES = {
    APROBAR: {
      titulo: 'Aprobar documento',
      placeholder: 'Ej: se verificó que es una factura válida.',
      confirmar: 'Aprobar',
      metodo: 'PATCH',
      estado: 'APROBADO',
    },
    RECHAZAR: {
      titulo: 'Rechazar documento',
      placeholder: 'Ej: no corresponde a ninguna de las categorías válidas.',
      confirmar: 'Rechazar',
      metodo: 'PATCH',
      estado: 'RECHAZADO',
    },
    PENDIENTE: {
      titulo: 'Devolver a pendiente',
      placeholder: 'Ej: falta verificar el proveedor.',
      confirmar: 'Poner en pendiente',
      metodo: 'PATCH',
      estado: 'PENDIENTE',
    },
    ELIMINAR: {
      titulo: 'Eliminar documento',
      placeholder: 'Ej: archivo duplicado que se subió por error.',
      confirmar: 'Eliminar definitivamente',
      metodo: 'DELETE',
      destructiva: true,
    },
  }

  const ejecutarAccion = useCallback(
    async (observacion) => {
      if (!accion || !accion.estado) return
      setSaving(true)
      const documentoId = accion.documento.id
      try {
        const res = await fetch(`${API}/${documentoId}/estado`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json', ...authHeaders },
          body: JSON.stringify({ estado: accion.estado, observacion }),
        })
        if (res.status === 401) {
          onUnauthorized?.()
          return
        }
        const data = await res.json().catch(() => null)
        if (!res.ok) throw new Error(errorMessage(data, res.status))

        setDocumentos((prev) =>
          prev.map((doc) => (doc.id === data.documento.id ? data.documento : doc))
        )
        setViewerDoc((prev) => (prev?.id === data.documento.id ? data.documento : prev))
        toast.success('Estado actualizado', {
          description: `Observación guardada: ${data.observacion.observacion}`,
        })
        setAccion(null)
        setRefreshKey((k) => k + 1)
        onChanged?.()
      } catch (err) {
        toast.error('No se pudo cambiar el estado', { description: String(err) })
      } finally {
        setSaving(false)
      }
    },
    [accion, authHeaders, onUnauthorized, onChanged]
  )

  const eliminarDocumento = useCallback(
    async (observacion) => {
      if (!accion) return
      setSaving(true)
      const documentoId = accion.documento.id
      try {
        const res = await fetch(`${API}/${documentoId}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json', ...authHeaders },
          body: JSON.stringify({ observacion }),
        })
        if (res.status === 401) {
          onUnauthorized?.()
          return
        }
        const data = await res.json().catch(() => null)
        if (!res.ok) throw new Error(errorMessage(data, res.status))

        setDocumentos((prev) => prev.filter((doc) => doc.id !== documentoId))
        setViewerDoc((prev) => (prev?.id === documentoId ? null : prev))
        toast.success('Documento eliminado', {
          description: `Observación conservada: ${data.observacion.observacion}`,
        })
        setAccion(null)
        setRefreshKey((k) => k + 1)
        onChanged?.()
      } catch (err) {
        toast.error('No se pudo eliminar el documento', { description: String(err) })
      } finally {
        setSaving(false)
      }
    },
    [accion, authHeaders, onUnauthorized, onChanged]
  )

  const abrirAccion = (tipo, documento) => {
    setAccion({ ...ACCIONES[tipo], documento })
  }

  const totalPaginas = Math.max(1, Math.ceil(total / porPagina))
  const desde = total === 0 ? 0 : (pagina - 1) * porPagina + 1
  const hasta = Math.min(pagina * porPagina, total)

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield />
            Todos los documentos
          </CardTitle>
          <CardDescription>
            Documentos de todos los usuarios en cualquier estado. Cada acción que tomes queda
            anotada como observación en la base de datos.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-2">
              <Label htmlFor="admin-filtro-texto" className="text-muted-foreground">
                Buscar
              </Label>
              <div className="relative">
                <Search className="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="admin-filtro-texto"
                  value={texto}
                  onChange={(e) => {
                    setPagina(1)
                    setTexto(e.target.value)
                  }}
                  placeholder="Nombre del archivo"
                  className="pl-7"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-muted-foreground">Estado</Label>
              <Select value={filtroEstado} onValueChange={aplicarFiltro(setFiltroEstado)}>
                <SelectTrigger aria-label="Filtrar por estado">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TODOS">Todos</SelectItem>
                  <SelectItem value="PENDIENTE">Pendientes</SelectItem>
                  <SelectItem value="APROBADO">Aprobados</SelectItem>
                  <SelectItem value="RECHAZADO">Rechazados</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-muted-foreground">Usuario</Label>
              <Select value={filtroUsuario} onValueChange={aplicarFiltro(setFiltroUsuario)}>
                <SelectTrigger aria-label="Filtrar por usuario">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TODOS">Todos</SelectItem>
                  {usuarios.map((u) => (
                    <SelectItem key={u.id} value={String(u.id)}>
                      {u.username}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <span className="pb-1 text-sm text-muted-foreground">
              {total} documento(s) · {pendientesTotal} pendiente(s)
            </span>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="size-5 animate-spin" />
            </div>
          ) : documentos.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              Ningún documento coincide con los filtros.
            </p>
          ) : (
            <div className="@container">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Documento</TableHead>
                  <TableHead className="hidden @min-[65rem]:table-cell">Usuario</TableHead>
                  <TableHead className="hidden @min-[73rem]:table-cell">Lote</TableHead>
                  <TableHead>Clasificación</TableHead>
                  <TableHead className="min-w-[13rem]">Estado y último cambio</TableHead>
                  <TableHead className="w-52">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documentos.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="max-w-[10rem]">
                      <p className="truncate font-medium" title={doc.nombre_archivo}>
                        {doc.nombre_archivo}
                      </p>
                      {doc.confianza != null && (
                        <p className="text-xs text-muted-foreground">
                          {Math.round(doc.confianza * 100)}%
                        </p>
                      )}
                    </TableCell>
                    <TableCell
                      className="hidden max-w-[7rem] truncate text-sm @min-[65rem]:table-cell"
                      title={doc.usuario_nombre ?? undefined}
                    >
                      {doc.usuario_nombre ?? '—'}
                    </TableCell>
                    <TableCell
                      className="hidden max-w-[8rem] truncate text-sm text-muted-foreground @min-[73rem]:table-cell"
                      title={doc.lote_nombre ?? undefined}
                    >
                      {doc.lote_nombre ?? '—'}
                    </TableCell>
                    <TableCell className="max-w-[13rem] whitespace-normal">
                      <div className="space-y-1">
                        <CategoryBadge category={doc.clasificacion} />
                        {doc.motivo && (
                          <p
                            className="line-clamp-2 text-xs leading-snug text-muted-foreground"
                            title={doc.motivo}
                          >
                            {doc.motivo}
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-normal">
                      <div className="max-w-[15rem] space-y-2">
                        <EstadoBadge estado={doc.estado} />
                        {doc.ultima_observacion ? (
                          <div className="space-y-1 border-l-2 border-muted-foreground/30 pl-2">
                            {(doc.ultima_observacion_estado_anterior ||
                              doc.ultima_observacion_estado_nuevo) && (
                              <p className="text-xs font-medium">
                                {ESTADO_LABELS[doc.ultima_observacion_estado_anterior] ??
                                  doc.ultima_observacion_estado_anterior ??
                                  '—'}
                                {' → '}
                                {ESTADO_LABELS[doc.ultima_observacion_estado_nuevo] ??
                                  doc.ultima_observacion_estado_nuevo ??
                                  '—'}
                              </p>
                            )}
                            <p className="line-clamp-3 text-xs leading-snug" title={doc.ultima_observacion}>
                              {doc.ultima_observacion}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {doc.ultima_observacion_admin &&
                                `${doc.ultima_observacion_admin} · `}
                              {formatDate(doc.ultima_observacion_fecha)}
                              {doc.total_observaciones > 1 &&
                                ` · ${doc.total_observaciones} cambios en total`}
                            </p>
                          </div>
                        ) : (
                          <p className="text-xs text-muted-foreground">
                            Sin cambios manuales.
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => setViewerDoc(doc)}
                          aria-label={`Ver ${doc.nombre_archivo}`}
                          title="Ver PDF"
                        >
                          <Eye />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => abrirAccion('APROBAR', doc)}
                          disabled={doc.estado === 'APROBADO'}
                          aria-label={`Aprobar ${doc.nombre_archivo}`}
                          title="Aprobar"
                        >
                          <CheckCircle2 className="text-emerald-600" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => abrirAccion('RECHAZAR', doc)}
                          disabled={doc.estado === 'RECHAZADO'}
                          aria-label={`Rechazar ${doc.nombre_archivo}`}
                          title="Rechazar"
                        >
                          <XCircle className="text-destructive" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => abrirAccion('PENDIENTE', doc)}
                          disabled={doc.estado === 'PENDIENTE'}
                          aria-label={`Poner ${doc.nombre_archivo} en pendiente`}
                          title="Poner en pendiente"
                        >
                          <Clock className="text-amber-600" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => abrirAccion('ELIMINAR', doc)}
                          aria-label={`Eliminar ${doc.nombre_archivo}`}
                          title="Eliminar"
                        >
                          <Trash2 className="text-destructive" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => setHistorialDoc(doc)}
                          aria-label={`Ver historial de ${doc.nombre_archivo}`}
                          title="Historial de observaciones"
                        >
                          <History />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            </div>
          )}

          {total > 0 && (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
              <span className="text-sm text-muted-foreground">
                Mostrando {desde}-{hasta} de {total}
              </span>
              <div className="flex items-center gap-2">
                <Select
                  value={String(porPagina)}
                  onValueChange={(valor) => {
                    setPagina(1)
                    setPorPagina(Number(valor))
                  }}
                >
                  <SelectTrigger className="w-20" aria-label="Documentos por página">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {OPCIONES_PAGINA.map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPagina((p) => Math.max(1, p - 1))}
                  disabled={pagina <= 1 || loading}
                  aria-label="Pagina anterior"
                >
                  Anterior
                </Button>
                <span className="text-sm text-muted-foreground">
                  {pagina} / {totalPaginas}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
                  disabled={pagina >= totalPaginas || loading}
                  aria-label="Pagina siguiente"
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {viewerDoc && (
        <Suspense fallback={null}>
          <PdfViewerDialogLazy
            key={viewerDoc.id}
            document={viewerDoc}
            token={token}
            apiBase={API}
            hideActions
            onClose={() => setViewerDoc(null)}
            onUnauthorized={onUnauthorized}
          />
        </Suspense>
      )}

      {historialDoc && (
        <HistorialDialog
          documento={historialDoc}
          token={token}
          onUnauthorized={onUnauthorized}
          onClose={() => setHistorialDoc(null)}
        />
      )}

      {accion && (
        <AccionDialog
          accion={accion}
          documento={accion.documento}
          onClose={() => !saving && setAccion(null)}
          onConfirm={accion.metodo === 'DELETE' ? eliminarDocumento : ejecutarAccion}
          saving={saving}
        />
      )}
    </>
  )
}
