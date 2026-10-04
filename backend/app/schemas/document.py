import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models import ESTADO_APROBADO, ESTADOS

OBSERVACION_MIN = 3
OBSERVACION_MAX = 1000


def parse_palabras(valor) -> list[str]:
    """La columna `palabras` guarda un JSON; tolera null y texto corrupto."""
    if valor is None:
        return []
    if isinstance(valor, list):
        return [str(item) for item in valor]
    try:
        datos = json.loads(valor)
    except (TypeError, ValueError):
        return []
    return [str(item) for item in datos] if isinstance(datos, list) else []


def dump_palabras(palabras: list[str]) -> str:
    return json.dumps(palabras, ensure_ascii=False)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    batch_id: int | None
    nombre_archivo: str
    ruta_fisica: str
    clasificacion: str | None
    confianza: float | None = None
    motivo: str | None = None
    palabras: list[str] = []
    requiere_revision: bool = False
    estado: str = ESTADO_APROBADO
    # Última acción del admin sobre este documento (tabla document_reviews).
    # Se rellena a mano desde los routers; por eso tienen default None. Es el
    # "por qué" que ve el dueño cuando su documento cambia de estado.
    ultima_observacion: str | None = None
    ultima_observacion_fecha: datetime | None = None
    ultima_observacion_accion: str | None = None
    ultima_observacion_estado_anterior: str | None = None
    ultima_observacion_estado_nuevo: str | None = None
    ultima_observacion_admin: str | None = None

    @field_validator("palabras", mode="before")
    @classmethod
    def _leer_palabras(cls, valor) -> list[str]:
        return parse_palabras(valor)


class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_lote: str
    fecha_creacion: datetime
    documents: list[DocumentRead] = []


class UploadedDocument(BaseModel):
    nombre_archivo: str
    clasificacion: str
    confianza: float | None = None
    motivo: str | None = None
    palabras: list[str] = []
    requiere_revision: bool = False
    estado: str = ESTADO_APROBADO


class UploadResponse(BaseModel):
    batch_id: int
    nombre_lote: str
    documents: list[UploadedDocument]


class RevisionUpdate(BaseModel):
    requiere_revision: bool


class EstadoUpdate(BaseModel):
    estado: str

    def estado_normalizado(self) -> str:
        return (self.estado or "").strip().upper()

    def es_valido(self) -> bool:
        return self.estado_normalizado() in ESTADOS


class AnalisisDocumentoRead(BaseModel):
    categoria: str
    palabras: list[str]


class CategoriaConteo(BaseModel):
    clasificacion: str
    total: int


class EstadoConteo(BaseModel):
    estado: str
    total: int


class ResumenClasificaciones(BaseModel):
    total: int
    categorias: list[CategoriaConteo]
    estados: list[EstadoConteo] = []


# --------------------------------------------------------------------------- #
# Panel de administracion: todos los documentos de todos los usuarios
# --------------------------------------------------------------------------- #


class DocumentReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: str
    nombre_archivo: str
    admin_username: str
    usuario_username: str | None = None
    accion: str
    estado_anterior: str | None = None
    estado_nuevo: str | None = None
    observacion: str
    created_at: datetime


class AdminDocumentoRead(BaseModel):
    """Documento visto desde el panel de admin: incluye datos del dueño."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre_archivo: str
    batch_id: int | None = None
    lote_nombre: str | None = None
    user_id: int | None = None
    usuario_nombre: str | None = None
    clasificacion: str | None = None
    confianza: float | None = None
    motivo: str | None = None
    palabras: list[str] = []
    requiere_revision: bool = False
    estado: str = ESTADO_APROBADO
    fecha_subida: datetime | None = None
    ultima_observacion: str | None = None
    ultima_observacion_fecha: datetime | None = None
    # Contexto del ultimo cambio de estado: que accion lo produjo, de que
    # estado salio, a cual entro y quien lo decidio. Sin esto la observacion
    # queda suelta y no se sabe a que transicion corresponde.
    ultima_observacion_accion: str | None = None
    ultima_observacion_estado_anterior: str | None = None
    ultima_observacion_estado_nuevo: str | None = None
    ultima_observacion_admin: str | None = None
    total_observaciones: int = 0

    @field_validator("palabras", mode="before")
    @classmethod
    def _leer_palabras(cls, valor) -> list[str]:
        return parse_palabras(valor)


class AdminDocumentoAccion(BaseModel):
    """Toda acción del admin exige observación: es la trazabilidad del cambio."""

    observacion: str = Field(min_length=OBSERVACION_MIN, max_length=OBSERVACION_MAX)

    @field_validator("observacion")
    @classmethod
    def _sin_espacios(cls, valor: str) -> str:
        limpio = valor.strip()
        if len(limpio) < OBSERVACION_MIN:
            raise ValueError(
                f"La observación debe tener al menos {OBSERVACION_MIN} caracteres."
            )
        return limpio


class AdminEstadoUpdate(AdminDocumentoAccion):
    estado: str

    def estado_normalizado(self) -> str:
        return (self.estado or "").strip().upper()

    def es_valido(self) -> bool:
        return self.estado_normalizado() in ESTADOS


class AdminEliminarUpdate(AdminDocumentoAccion):
    """Cuerpo del borrado. Se separa del cambio de estado porque no lleva estado."""


class AccionAplicada(BaseModel):
    """Respuesta comun: el documento resultante (null si se borro) y la
    observacion que quedo registrada en la base de datos."""

    documento: AdminDocumentoRead | None = None
    observacion: DocumentReviewRead


class AdminResumenRead(BaseModel):
    total: int
    por_estado: list[EstadoConteo] = []
    por_usuario: list[UsuarioConteo] = []


class UsuarioConteo(BaseModel):
    usuario_id: int | None = None
    usuario_nombre: str
    total: int


class DocumentosPaginadosRead(BaseModel):
    """Pagina del listado global del panel de administracion.

    `por_pagina=0` significa "sin paginar": se devuelve todo y `pagina` es 1.
    """

    total: int
    pagina: int
    por_pagina: int
    documentos: list[AdminDocumentoRead] = []
