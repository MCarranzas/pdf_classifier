import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import {
  Eye,
  FileUp,
  History,
  Loader2,
  Lock,
  LogOut,
  Search,
  Shield,
  Trash2,
  UploadCloud,
  UserCog,
  UserPlus,
  XCircle,
} from 'lucide-react'
import AdminDocumentsPanel from '@/components/AdminDocumentsPanel'
import HistorialDialog from '@/components/HistorialDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
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

const TOKEN_KEY = 'pdf_classifier_token'
const USER_KEY = 'pdf_classifier_user'
const MAX_FILES = 5

// El visor arrastra pdf.js (~1 MB), que solo hace falta al abrir un documento.
const PdfViewerDialog = lazy(() => import('@/components/PdfViewerDialog'))

function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleString('es-ES', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

// Compara nombres sin distinguir mayúsculas ni acentos: así "diciembre" encuentra
// "Diciembre_2022.pdf" y "factura" encuentra "Factúra.pdf".
function normalizarTexto(valor) {
  return (valor ?? '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
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
  PENDIENTE: 'default',
  APROBADO: 'outline',
  RECHAZADO: 'destructive',
}

function EstadoBadge({ estado }) {
  return (
    <Badge variant={ESTADO_VARIANTS[estado] ?? 'secondary'}>
      {ESTADO_LABELS[estado] ?? estado}
    </Badge>
  )
}

const FILTROS_ESTADO = [
  { value: 'TODOS', label: 'Todos' },
  { value: 'PENDIENTE', label: 'Solo pendientes de revisión' },
  { value: 'APROBADO', label: 'Solo aprobados' },
  { value: 'RECHAZADO', label: 'Solo rechazados' },
]

const MENSAJES_VACIOS_FILTRO = {
  PENDIENTE: 'Ningún documento requiere revisión.',
  APROBADO: 'Ningún documento ha sido aprobado.',
  RECHAZADO: 'Ningún documento ha sido rechazado.',
}

function RoleBadge({ role }) {
  return <Badge variant={role === 'admin' ? 'default' : 'secondary'}>{role}</Badge>
}

const CATEGORY_COLORS = {
  FACTURA: '#f97316',
  CONTRATO: '#3b82f6',
  'FORMULARIO 110': '#10b981',
  OTRO: '#6b7280',
}

function PieChart({ data, size = 220 }) {
  const total = data.reduce((acc, item) => acc + item.total, 0)

  if (!total) {
    return (
      <div
        className="flex items-center justify-center rounded-full border border-dashed text-sm text-muted-foreground"
        style={{ width: size, height: size }}
      >
        Sin datos
      </div>
    )
  }

  const radius = size / 2
  const innerRadius = radius - 4

  // Con una sola categoría un arco de 360º se dibuja mal, así que va círculo.
  if (data.length === 1) {
    const only = data[0]
    return (
      <svg
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        role="img"
        aria-label={only.clasificacion}
      >
        <circle
          cx={radius}
          cy={radius}
          r={innerRadius}
          fill={CATEGORY_COLORS[only.clasificacion] ?? '#94a3b8'}
          stroke="#fff"
          strokeWidth="2"
        />
      </svg>
    )
  }

  const { arcs } = data.reduce(
    (acc, item) => {
      const fraction = item.total / total
      const endAngle = acc.startAngle + fraction * Math.PI * 2
      const largeArcFlag = +(fraction > 0.5)
      const x1 = radius + innerRadius * Math.cos(acc.startAngle)
      const y1 = radius + innerRadius * Math.sin(acc.startAngle)
      const x2 = radius + innerRadius * Math.cos(endAngle)
      const y2 = radius + innerRadius * Math.sin(endAngle)
      acc.arcs.push({
        d: `M ${radius} ${radius} L ${x1} ${y1} A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`,
        fill: CATEGORY_COLORS[item.clasificacion] ?? '#94a3b8',
        label: item.clasificacion,
      })
      acc.startAngle = endAngle
      return acc
    },
    { startAngle: -Math.PI / 2, arcs: [] }
  )

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width={size}
      height={size}
      role="img"
      aria-label="Distribución de clasificaciones"
    >
      {arcs.map((arc) => (
        <path
          key={arc.label}
          d={arc.d}
          fill={arc.fill}
          stroke="#fff"
          strokeWidth="2"
        />
      ))}
    </svg>
  )
}

function Footer() {
  return (
    <footer className="border-t">
      <div className="mx-auto max-w-7xl px-4 py-4 text-center text-sm text-muted-foreground">
        Gonchi@{new Date().getFullYear()}
      </div>
    </footer>
  )
}

function errorMessage(data, status) {
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => item.msg.replace('String should have at least', 'Mínimo'))
      .join(', ')
  }
  return data?.detail ?? `Error ${status}`
}

function AuthScreen({ onSuccess }) {
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            {mode === 'login' ? <Lock className="size-5" /> : <UserPlus className="size-5" />}
          </div>
          <CardTitle className="text-lg">Clasificador de PDFs</CardTitle>
          <CardDescription>
            {mode === 'login'
              ? 'Inicia sesión para continuar'
              : 'Crea tu cuenta de usuario'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={async (e) => {
              e.preventDefault()
              setSubmitting(true)
              try {
                const res = await fetch(
                  `/api/auth/${mode === 'login' ? 'login' : 'register'}`,
                  {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password }),
                  }
                )
                const data = await res.json().catch(() => null)
                if (!res.ok) throw new Error(errorMessage(data, res.status))
                if (mode === 'login') {
                  localStorage.setItem(TOKEN_KEY, data.access_token)
                  localStorage.setItem(USER_KEY, JSON.stringify(data.user))
                  toast.success(`Bienvenido, ${data.user.username}`)
                  onSuccess(data.access_token, data.user)
                } else {
                  toast.success('Usuario registrado, ya puedes iniciar sesión')
                  setPassword('')
                  setMode('login')
                }
              } catch (err) {
                toast.error('No se pudo completar la operación', {
                  description: String(err),
                })
              } finally {
                setSubmitting(false)
              }
            }}
            className="space-y-4"
          >
            <div className="space-y-2">
              <Label htmlFor="username">Usuario</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                placeholder="tu.usuario"
                minLength={3}
                maxLength={100}
                required
              />
              {mode === 'register' && (
                <p className="text-xs text-muted-foreground">
                  El usuario debe tener al menos 3 caracteres.
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Contraseña</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                placeholder="••••••"
                minLength={mode === 'login' ? 1 : 6}
                maxLength={128}
                required
              />
              {mode === 'register' && (
                <p className="text-xs text-muted-foreground">
                  La contraseña debe tener al menos 6 caracteres.
                </p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting && <Loader2 className="size-4 animate-spin" />}
              {mode === 'login' ? 'Iniciar sesión' : 'Registrarse'}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={() => {
                setMode(mode === 'login' ? 'register' : 'login')
                setPassword('')
              }}
            >
              {mode === 'login' ? '¿No tienes cuenta? Regístrate' : '¿Ya tienes cuenta? Inicia sesión'}
            </Button>
          </form>
        </CardContent>
      </Card>
      <Footer />
    </div>
  )
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY))
    } catch {
      return null
    }
  })
  const [batches, setBatches] = useState([])
  const [resumen, setResumen] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [batchName, setBatchName] = useState('')
  const fileInputRef = useRef(null)
  const [adminUsers, setAdminUsers] = useState([])
  const [adminRoles, setAdminRoles] = useState(['user'])
  const [loadingAdmin, setLoadingAdmin] = useState(true)
  const [creatingUser, setCreatingUser] = useState(false)
  const [newUser, setNewUser] = useState({ username: '', password: '', role: 'user' })
  const [viewerDoc, setViewerDoc] = useState(null)
  const [historialDoc, setHistorialDoc] = useState(null)
  const [savingRevision, setSavingRevision] = useState(null)
  const [savingEstado, setSavingEstado] = useState(null)
  const [filtroEstado, setFiltroEstado] = useState('TODOS')
  const [busqueda, setBusqueda] = useState('')

  const isAdmin = user?.roles?.includes('admin') ?? false

  // Las dos vistas: la operativa (cualquier usuario) y la de administración.
  // Por defecto el admin entra en Administración; un usuario normal nunca la ve.
  const [vista, setVista] = useState('admin')
  const vistaActiva = isAdmin ? vista : 'documentos'

  const handleLogout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
    setBatches([])
    setResumen(null)
    setAdminUsers([])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [])

  const loadBatches = useCallback(async () => {
    try {
      const res = await fetch('/api/batches', {
        headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` },
      })
      if (res.status === 401) {
        handleLogout()
        return
      }
      if (!res.ok) throw new Error(`Error ${res.status}`)
      setBatches(await res.json())
    } catch (err) {
      toast.error('No se pudieron cargar los lotes', { description: String(err) })
    } finally {
      setLoading(false)
    }
  }, [handleLogout])

  const loadResumen = useCallback(async () => {
    try {
      const res = await fetch('/api/documents/resumen', {
        headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` },
      })
      if (res.status === 401) {
        handleLogout()
        return
      }
      if (!res.ok) throw new Error(`Error ${res.status}`)
      setResumen(await res.json())
    } catch (err) {
      toast.error('No se pudo cargar el dashboard', { description: String(err) })
    }
  }, [handleLogout])

  const refreshProfile = useCallback(async () => {
    try {
      const res = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` },
      })
      if (res.status === 401) {
        handleLogout()
        return
      }
      if (!res.ok) throw new Error(`Error ${res.status}`)
      const data = await res.json()
      setUser(data)
      localStorage.setItem(USER_KEY, JSON.stringify(data))
    } catch {
      toast.error('No se pudo refrescar tu sesión')
    }
  }, [handleLogout])

  const loadAdminData = useCallback(async () => {
    try {
      const headers = { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` }
      const [usersRes, rolesRes] = await Promise.all([
        fetch('/api/admin/users', { headers }),
        fetch('/api/admin/roles', { headers }),
      ])
      if (usersRes.status === 401) {
        handleLogout()
        return
      }
      if (!usersRes.ok || !rolesRes.ok) {
        throw new Error(`admin ${usersRes.status}/${rolesRes.status}`)
      }
      setAdminUsers(await usersRes.json())
      setAdminRoles(await rolesRes.json())
    } catch (err) {
      toast.error('No se pudo cargar la administración', { description: String(err) })
    } finally {
      setLoadingAdmin(false)
    }
  }, [handleLogout])

  const handleToggleRevision = useCallback(
    async (doc, value) => {
      setSavingRevision(doc.id)
      try {
        const res = await fetch(`/api/documents/${doc.id}/revision`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`,
          },
          body: JSON.stringify({ requiere_revision: value }),
        })
        if (res.status === 401) {
          handleLogout()
          return
        }
        const data = await res.json().catch(() => null)
        if (!res.ok) throw new Error(errorMessage(data, res.status))
        setBatches((prev) =>
          prev.map((b) => ({
            ...b,
            documents: b.documents.map((d) => (d.id === data.id ? data : d)),
          }))
        )
        setViewerDoc((prev) => (prev?.id === data.id ? data : prev))
        toast.success(
          value ? 'Documento marcado con revisión' : 'Documento marcado como revisado',
          { description: doc.nombre_archivo }
        )
      } catch (err) {
        toast.error('No se pudo cambiar el estado de revisión', { description: String(err) })
      } finally {
        setSavingRevision(null)
      }
    },
    [handleLogout]
  )

  const handleUpdateEstado = useCallback(
    async (doc, estado) => {
      setSavingEstado(doc.id)
      try {
        const res = await fetch(`/api/documents/${doc.id}/estado`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`,
          },
          body: JSON.stringify({ estado }),
        })
        if (res.status === 401) {
          handleLogout()
          return
        }
        const data = await res.json().catch(() => null)
        if (!res.ok) throw new Error(errorMessage(data, res.status))
        setBatches((prev) =>
          prev.map((b) => ({
            ...b,
            documents: b.documents.map((d) => (d.id === data.id ? data : d)),
          }))
        )
        setViewerDoc((prev) => (prev?.id === data.id ? data : prev))
        toast.success(`Documento ${ESTADO_LABELS[estado]?.toLowerCase() ?? estado}`, {
          description: doc.nombre_archivo,
        })
        if (isAdmin) loadResumen()
      } catch (err) {
        toast.error('No se pudo cambiar el estado del documento', { description: String(err) })
      } finally {
        setSavingEstado(null)
      }
    },
    [handleLogout, isAdmin, loadResumen]
  )

  useEffect(() => {
    if (token) {
      loadBatches()
      refreshProfile()
    }
  }, [token, loadBatches, refreshProfile])

  useEffect(() => {
    if (token && isAdmin) {
      loadResumen()
      loadAdminData()
    }
  }, [token, isAdmin, loadResumen, loadAdminData])

  const filteredBatches = useMemo(() => {
    const consulta = normalizarTexto(busqueda)
    if (filtroEstado === 'TODOS' && !consulta) return batches
    return batches
      .map((b) => ({
        ...b,
        documents: b.documents.filter((d) => {
          const coincideEstado = filtroEstado === 'TODOS' || d.estado === filtroEstado
          const coincideNombre =
            !consulta || normalizarTexto(d.nombre_archivo).includes(consulta)
          return coincideEstado && coincideNombre
        }),
      }))
      .filter((b) => b.documents.length > 0)
  }, [batches, filtroEstado, busqueda])

  const documentosVisibles = useMemo(
    () => filteredBatches.reduce((acc, b) => acc + b.documents.length, 0),
    [filteredBatches]
  )

  const estadoCounts = useMemo(() => {
    return batches.reduce((acc, b) => {
      b.documents.forEach((d) => {
        acc[d.estado] = (acc[d.estado] ?? 0) + 1
      })
      return acc
    }, {})
  }, [batches])

  const pendientes = estadoCounts.PENDIENTE ?? 0
  const rechazados = estadoCounts.RECHAZADO ?? 0

  const handleAuthSuccess = (accessToken, nextUser) => {
    setToken(accessToken)
    setUser(nextUser)
  }

  if (!token) return <AuthScreen onSuccess={handleAuthSuccess} />

  const handleUpload = async () => {
    if (!selectedFiles.length) return
    const form = new FormData()
    selectedFiles.forEach((file) => form.append('files', file))
    if (batchName.trim()) form.append('nombre_lote', batchName.trim())
    setUploading(true)
    try {
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` },
        body: form,
      })
      const data = await res.json().catch(() => null)
      if (res.status === 401) {
        handleLogout()
        return
      }
      if (!res.ok) throw new Error(data?.detail ?? `Error ${res.status}`)
      const clasificados = data.documents?.length ?? 0
      toast.success(`Lote clasificado: ${data.nombre_lote}`, {
        description: `${clasificados} documento(s) clasificado(s)`,
      })
      setSelectedFiles([])
      setBatchName('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      await loadBatches()
      if (isAdmin) await loadResumen()
    } catch (err) {
      toast.error('No se pudo clasificar el lote', { description: String(err) })
    } finally {
      setUploading(false)
    }
  }

  const handleDeleteBatch = async (batchId) => {
    try {
      const res = await fetch(`/api/batches/${batchId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` },
      })
      if (res.status === 401) {
        handleLogout()
        return
      }
      if (!res.ok) throw new Error(`Error ${res.status}`)
      toast.success('Lote eliminado')
      await loadBatches()
      if (isAdmin) await loadResumen()
    } catch (err) {
      toast.error('No se pudo eliminar el lote', { description: String(err) })
    }
  }

  const toggleRole = async (target, role) => {
    const hasRole = target.roles.includes(role)
    const roles = hasRole ? target.roles.filter((r) => r !== role) : [...target.roles, role]
    try {
      const res = await fetch(`/api/admin/users/${target.id}/roles`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`,
        },
        body: JSON.stringify({ roles }),
      })
      if (res.status === 401) {
        handleLogout()
        return
      }
      const data = await res.json().catch(() => null)
      if (!res.ok) throw new Error(errorMessage(data, res.status))
      setAdminUsers((prev) => prev.map((u) => (u.id === target.id ? data : u)))
      toast.success(`Rol '${role}' ${hasRole ? 'quitado' : 'asignado'} a ${target.username}`)
    } catch (err) {
      toast.error('No se pudo actualizar el rol', { description: String(err) })
    }
  }

  const handleCreateUser = async (e) => {
    e.preventDefault()
    if (!newUser.username.trim() || newUser.password.length < 6) return
    setCreatingUser(true)
    try {
      const res = await fetch('/api/admin/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`,
        },
        body: JSON.stringify({
          username: newUser.username.trim(),
          password: newUser.password,
          roles: [newUser.role],
        }),
      })
      if (res.status === 401) {
        handleLogout()
        return
      }
      const data = await res.json().catch(() => null)
      if (!res.ok) throw new Error(errorMessage(data, res.status))
      toast.success(`Usuario ${data.username} creado con rol ${newUser.role}`)
      setNewUser({ username: '', password: '', role: 'user' })
      await loadAdminData()
    } catch (err) {
      toast.error('No se pudo crear el usuario', { description: String(err) })
    } finally {
      setCreatingUser(false)
    }
  }

  const tooMany = selectedFiles.length > MAX_FILES

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-6">
          <div className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <FileUp className="size-5" />
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-semibold tracking-tight">Clasificador de PDFs</h1>
            <p className="text-sm text-muted-foreground">
              Sube hasta 5 pdfs y se clasificarán automáticamente
            </p>
          </div>
          {user && (
            <div className="flex items-center gap-3">
              {isAdmin && (
                <Badge variant="default">
                  <Shield className="mr-1 size-3" />
                  admin
                </Badge>
              )}
              <span className="text-sm text-muted-foreground">{user.username}</span>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <LogOut className="size-4" />
                Salir
              </Button>
            </div>
          )}
        </div>

        {/* Navegación: solo el admin tiene segunda vista. No protege nada,
            `require_admin` en el backend sí. */}
        {isAdmin && (
          <nav className="mx-auto flex max-w-7xl gap-1 px-4 pb-3">
            <Button
              variant={vistaActiva === 'documentos' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setVista('documentos')}
              aria-current={vistaActiva === 'documentos' ? 'page' : undefined}
            >
              <UploadCloud className="size-4" />
              Mis documentos
            </Button>
            <Button
              variant={vistaActiva === 'admin' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setVista('admin')}
              aria-current={vistaActiva === 'admin' ? 'page' : undefined}
            >
              <Shield className="size-4" />
              Administración
            </Button>
          </nav>
        )}
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 px-4 py-8">
        {vistaActiva === 'admin' && (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Dashboard de clasificaciones</CardTitle>
                <CardDescription>
                  Distribución de todos los documentos clasificados en el sistema
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loading || !resumen ? (
                  <div className="flex items-center justify-center py-10 text-muted-foreground">
                    <Loader2 className="size-5 animate-spin" />
                  </div>
                ) : resumen.total === 0 ? (
                  <p className="py-10 text-center text-sm text-muted-foreground">
                    Aún no hay documentos clasificados.
                  </p>
                ) : (
                  <div className="flex flex-wrap items-center gap-8">
                    <PieChart data={resumen.categorias} />
                    <ul className="space-y-2 text-sm">
                      {resumen.categorias.map((item) => (
                        <li key={item.clasificacion} className="flex items-center gap-2">
                          <span
                            className="size-3 rounded-full"
                            style={{
                              background: CATEGORY_COLORS[item.clasificacion] ?? '#94a3b8',
                            }}
                          />
                          <span className="font-medium">{item.clasificacion}</span>
                          <span className="text-muted-foreground">
                            {item.total} · {Math.round((item.total / resumen.total) * 100)}%
                          </span>
                        </li>
                      ))}
                    </ul>
                    <ul className="space-y-2 text-sm">
                      {(resumen.estados ?? []).map((item) => (
                        <li key={item.estado} className="flex items-center gap-2">
                          <EstadoBadge estado={item.estado} />
                          <span className="text-muted-foreground">{item.total}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>

            <AdminDocumentsPanel
              token={token}
              onUnauthorized={handleLogout}
              onChanged={loadResumen}
            />

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <UserCog className="size-4" />
                  Administración de usuarios
                </CardTitle>
                <CardDescription>Crea usuarios y asígnales roles</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <form
                  onSubmit={handleCreateUser}
                  className="flex flex-wrap items-end gap-3 rounded-lg border p-4"
                >
                  <div className="space-y-2">
                    <Label htmlFor="adminNewUsername">Usuario</Label>
                    <Input
                      id="adminNewUsername"
                      value={newUser.username}
                      onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                      placeholder="nuevo.usuario"
                      minLength={3}
                      maxLength={100}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="adminNewPassword">Contraseña</Label>
                    <Input
                      id="adminNewPassword"
                      type="password"
                      value={newUser.password}
                      onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                      placeholder="••••••"
                      minLength={6}
                      maxLength={128}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="adminNewRole">Rol</Label>
                    <select
                      id="adminNewRole"
                      value={newUser.role}
                      onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                      className="flex h-9 rounded-md border bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                    >
                      {adminRoles.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Button type="submit" disabled={creatingUser || loadingAdmin}>
                    {creatingUser && <Loader2 className="size-4 animate-spin" />}
                    Crear usuario
                  </Button>
                </form>

                {loadingAdmin ? (
                  <div className="flex items-center justify-center py-8 text-muted-foreground">
                    <Loader2 className="size-5 animate-spin" />
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Usuario</TableHead>
                        <TableHead>Creado</TableHead>
                        <TableHead>Roles</TableHead>
                        <TableHead className="w-40" />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {adminUsers.map((u) => (
                        <TableRow key={u.id}>
                          <TableCell className="font-medium">{u.username}</TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {formatDate(u.created_at)}
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {u.roles.length ? (
                                u.roles.map((role) => <RoleBadge key={role} role={role} />)
                              ) : (
                                <span className="text-sm text-muted-foreground">sin rol</span>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Button
                              type="button"
                              variant={u.roles.includes('admin') ? 'default' : 'outline'}
                              size="sm"
                              onClick={() => toggleRole(u, 'admin')}
                            >
                              {u.roles.includes('admin') ? 'Quitar admin' : 'Hacer admin'}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </>
        )}

        {vistaActiva === 'documentos' && (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Clasificar lote</CardTitle>
                <CardDescription>
                  El texto de la primera página de cada PDF se analiza con BigPickle cuando está
                  configurado y usa palabras clave como respaldo. Máximo {MAX_FILES} por lote.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  multiple
                  className="hidden"
                  onChange={(e) => setSelectedFiles(Array.from(e.target.files ?? []))}
                />
                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                  >
                    Elegir PDFs
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {selectedFiles.length
                      ? `${selectedFiles.length} de ${MAX_FILES} archivo(s) seleccionado(s)`
                      : 'Ningún archivo seleccionado'}
                  </span>
                </div>
                {selectedFiles.length > 0 && (
                  <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
                    {selectedFiles.map((file, i) => (
                      <li key={i} className="max-w-[35rem] truncate">
                        {file.name}
                      </li>
                    ))}
                  </ul>
                )}
                {tooMany && (
                  <p className="text-sm text-destructive">Máximo {MAX_FILES} PDFs por lote.</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="batchName">Nombre del lote (opcional)</Label>
                  <Input
                    id="batchName"
                    value={batchName}
                    onChange={(e) => setBatchName(e.target.value)}
                    placeholder="Ej: Facturas de marzo"
                    maxLength={255}
                  />
                </div>
                {selectedFiles.length > 0 && !tooMany && (
                  <Button type="button" onClick={handleUpload} disabled={uploading}>
                    {uploading && <Loader2 className="size-4 animate-spin" />}
                    Clasificar lote
                  </Button>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Lotes clasificados</CardTitle>
                <CardDescription>
                  {batches.length} en total · {pendientes} pendiente(s) de revisión · {rechazados}{' '}
                  rechazado(s)
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-end gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="buscar-documento" className="text-muted-foreground">
                      Buscar
                    </Label>
                    <div className="relative">
                      <Search className="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        id="buscar-documento"
                        value={busqueda}
                        onChange={(e) => setBusqueda(e.target.value)}
                        placeholder="Nombre del documento"
                        className="pl-7"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="filtro-estado" className="text-muted-foreground">
                      Estado
                    </Label>
                    <Select value={filtroEstado} onValueChange={setFiltroEstado}>
                      <SelectTrigger id="filtro-estado" aria-label="Filtrar documentos por estado">
                        <SelectValue placeholder="Filtrar por estado" />
                      </SelectTrigger>
                      <SelectContent>
                        {FILTROS_ESTADO.map((f) => (
                          <SelectItem key={f.value} value={f.value}>
                            {f.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {(filtroEstado !== 'TODOS' || busqueda.trim()) && (
                    <span className="pb-2 text-sm text-muted-foreground">
                      Mostrando {documentosVisibles} documento(s)
                    </span>
                  )}
                  <span className="pb-2 text-sm text-muted-foreground">
                    {pendientes
                      ? 'Revisa el PDF y apruébalo o recházalo para quitarlo de la lista de pendientes.'
                      : 'No hay documentos pendientes de revisión.'}
                  </span>
                </div>

                {loading ? (
                  <div className="flex items-center justify-center py-10 text-muted-foreground">
                    <Loader2 className="size-5 animate-spin" />
                  </div>
                ) : filteredBatches.length === 0 ? (
                  <p className="py-10 text-center text-sm text-muted-foreground">
                    {batches.length === 0
                      ? 'Aún no hay lotes clasificados.'
                      : busqueda.trim()
                        ? 'Ningún documento coincide con la búsqueda.'
                        : (MENSAJES_VACIOS_FILTRO[filtroEstado] ??
                          'Ningún documento coincide con el filtro seleccionado.')}
                  </p>
                ) : (
                  <div className="flex flex-col gap-6">
                    {filteredBatches.map((batch) => (
                      <div key={batch.id} className="space-y-3">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <h3 className="font-medium">{batch.nombre_lote}</h3>
                            <p className="text-sm text-muted-foreground">
                              {formatDate(batch.fecha_creacion)} · {batch.documents.length}{' '}
                              documento(s)
                            </p>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteBatch(batch.id)}
                            aria-label={`Eliminar lote ${batch.nombre_lote}`}
                          >
                            <Trash2 className="size-4" />
                          </Button>
                        </div>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Nombre</TableHead>
                              <TableHead>Clasificación</TableHead>
                              <TableHead>Confianza</TableHead>
                              <TableHead className="min-w-[13rem]">Estado y último cambio</TableHead>
                              <TableHead>Revisión</TableHead>
                              <TableHead className="w-24" />
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {batch.documents.map((doc) => (
                              <TableRow key={doc.id}>
                                <TableCell className="max-w-[14rem] truncate font-medium" title={doc.nombre_archivo}>
                                  {doc.nombre_archivo}
                                </TableCell>
                                <TableCell className="max-w-[16rem] whitespace-normal">
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
                                <TableCell>
                                  {doc.confianza == null
                                    ? '—'
                                    : `${Math.round(doc.confianza * 100)}%`}
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
                                        <p
                                          className="line-clamp-3 text-xs leading-snug"
                                          title={doc.ultima_observacion}
                                        >
                                          {doc.ultima_observacion}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                          {doc.ultima_observacion_admin &&
                                            `${doc.ultima_observacion_admin} · `}
                                          {formatDate(doc.ultima_observacion_fecha)}
                                        </p>
                                      </div>
                                    ) : (
                                      <p className="text-xs text-muted-foreground">
                                        Sin cambios del administrador.
                                      </p>
                                    )}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <Button
                                    type="button"
                                    variant={doc.requiere_revision ? 'default' : 'outline'}
                                    size="sm"
                                    onClick={() => handleToggleRevision(doc, !doc.requiere_revision)}
                                    disabled={
                                      doc.estado !== 'PENDIENTE' ||
                                      savingRevision === doc.id ||
                                      savingEstado === doc.id
                                    }
                                    title={
                                      doc.estado === 'PENDIENTE'
                                        ? 'Cambiar el estado de revisión'
                                        : `El estado ${doc.estado} es final y no admite más cambios`
                                    }
                                    aria-label={`Cambiar estado de revisión de ${doc.nombre_archivo}`}
                                  >
                                    {savingRevision === doc.id && (
                                      <Loader2 className="size-3.5 animate-spin" />
                                    )}
                                    {doc.requiere_revision ? 'Revisión 1' : 'Revisión 0'}
                                  </Button>
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-1">
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={() => setViewerDoc(doc)}
                                      aria-label={`Ver ${doc.nombre_archivo}`}
                                    >
                                      <Eye className="size-4" />
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={() =>
                                        setHistorialDoc({ ...doc, usuario_nombre: user?.username })
                                      }
                                      title="Historial de observaciones"
                                      aria-label={`Ver historial de ${doc.nombre_archivo}`}
                                    >
                                      <History className="size-4" />
                                    </Button>
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      onClick={() => handleUpdateEstado(doc, 'RECHAZADO')}
                                      disabled={!doc.requiere_revision || savingEstado === doc.id}
                                      title={
                                        doc.requiere_revision
                                          ? 'Rechazar documento'
                                          : 'Solo los documentos con revisión pueden rechazarse'
                                      }
                                      aria-label={`Rechazar ${doc.nombre_archivo}`}
                                    >
                                      {savingEstado === doc.id ? (
                                        <Loader2 className="size-4 animate-spin" />
                                      ) : (
                                        <XCircle className="size-4 text-destructive" />
                                      )}
                                    </Button>
                                  </div>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}
      </main>

      {viewerDoc && (
        <Suspense fallback={null}>
          <PdfViewerDialog
            key={viewerDoc.id}
            document={viewerDoc}
            token={token}
            onClose={() => setViewerDoc(null)}
            onUnauthorized={handleLogout}
            onToggleRevision={handleToggleRevision}
            onUpdateEstado={handleUpdateEstado}
            saving={savingRevision === viewerDoc.id || savingEstado === viewerDoc.id}
            savingEstado={savingEstado === viewerDoc.id}
          />
        </Suspense>
      )}

      {historialDoc && (
        <HistorialDialog
          documento={historialDoc}
          token={token}
          apiBase="/api/documents"
          onClose={() => setHistorialDoc(null)}
          onUnauthorized={handleLogout}
        />
      )}

      <Footer />
    </div>
  )
}