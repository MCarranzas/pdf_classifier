"""Panel de administracion de documentos.

A diferencia de /api/documents, aqui el admin ve los documentos de todos los
usuarios y puede moverlos entre estados sin la restriccion de "estado final"
que aplica a los usuarios normales. Toda accion exige una observacion, que se
guarda en document_reviews como bitacora.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    ACCION_APROBAR,
    ACCION_ELIMINAR,
    ACCION_PENDIENTE,
    ACCION_RECHAZAR,
    ESTADOS,
    Batch,
    Document,
    DocumentReview,
    User,
    requiere_revision_desde_estado,
)
from ..schemas.document import (
    AccionAplicada,
    AdminDocumentoRead,
    AdminEliminarUpdate,
    AdminEstadoUpdate,
    AnalisisDocumentoRead,
    DocumentReviewRead,
    DocumentosPaginadosRead,
    EstadoConteo,
    parse_palabras,
)
from ..security import require_admin
from ..services.classifier import CATEGORY_KEYWORDS

router = APIRouter(
    prefix="/api/admin/documentos",
    tags=["admin-documentos"],
    dependencies=[Depends(require_admin)],
)

PAGINA_POR_DEFECTO = 25
MAX_POR_PAGINA = 200

# Estado pedido -> accion registrada en la bitacora.
ACCION_POR_ESTADO = {
    "APROBADO": ACCION_APROBAR,
    "RECHAZADO": ACCION_RECHAZAR,
    "PENDIENTE": ACCION_PENDIENTE,
}


def _get_documento(db: Session, document_id: str) -> Document:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado"
        )
    return document


def _nombre_de_usuario(db: Session, user_id: int | None) -> str | None:
    if user_id is None:
        return None
    return db.scalar(select(User.username).where(User.id == user_id))


# --------------------------------------------------------------------------- #
# Enriquecimiento del listado
# --------------------------------------------------------------------------- #
# Antes de esto, cada fila del listado lanzaba sus propias consultas: la ultima
# observacion, el total de observaciones, el nombre del dueno y el lote. Con la
# paginacion de 25 filas eso eran ~75 consultas por pagina, y el numero crecia
# con cada documento. Ademas documents.py ya resolvia lo mismo con UNA consulta
# (adjuntar_ultima_observacion), asi que el panel de admin era la excepcion.
#
# Ahora el enriquecimiento se hace para el conjunto de documentos con un numero
# fijo de consultas (4), sin importar cuantos sean.


@dataclass(frozen=True)
class _UltimaObservacion:
    """Lo que el listado muestra de la ultima observacion del admin."""

    observacion: str
    created_at: datetime
    accion: str
    estado_anterior: str | None
    estado_nuevo: str | None
    admin_username: str


@dataclass(frozen=True)
class _Enriquecimiento:
    """Datos de las tablas vecinas para un conjunto de documentos.

    Todo indexado por id de documento (o de lote / de usuario), de forma que
    proyectar cada fila es una busqueda en un diccionario.
    """

    lotes: dict[int, Batch]
    usuarios: dict[int, str]
    observaciones: dict[str, _UltimaObservacion]
    totales: dict[str, int]


def _enriquecer(db: Session, documentos: Sequence[Document]) -> _Enriquecimiento:
    """Resuelve lote, dueno, ultima observacion y total con 4 consultas fijas."""
    ids = [document.id for document in documentos]
    batch_ids = {d.batch_id for d in documentos if d.batch_id is not None}
    user_ids = {d.user_id for d in documentos if d.user_id is not None}

    lotes: dict[int, Batch] = {}
    if batch_ids:
        lotes = {
            lote.id: lote
            for lote in db.scalars(select(Batch).where(Batch.id.in_(batch_ids)))
        }

    usuarios: dict[int, str] = {}
    if user_ids:
        usuarios = dict(
            db.execute(select(User.id, User.username).where(User.id.in_(user_ids))).all()
        )

    observaciones: dict[str, _UltimaObservacion] = {}
    totales: dict[str, int] = {}
    if ids:
        # La ultima observacion de cada documento sale con MAX(id) y no con
        # ROW_NUMBER(): aunque las funciones de ventana existen desde MariaDB
        # 10.2, se calculan sobre TODAS las filas del grupo antes de filtrar,
        # asi que con 400.000 revisiones esta consulta tardaba 6,5 s frente a
        # los ~7 ms de MAX(id). Se descarto por medicion, no por gusto.
        #
        # MAX(id) y "ORDER BY created_at DESC, id DESC" coinciden porque
        # document_reviews es un log que solo crece: id es AUTO_INCREMENT y
        # created_at lo pone la aplicacion en el INSERT, de modo que la fila
        # con id mas alto es siempre la mas reciente. Es el mismo criterio que
        # ya usa services/observaciones.py (ordena por id DESC), asi que el
        # panel y la vista del dueno no pueden discrepar.
        ultimos_ids = (
            select(
                DocumentReview.document_id.label("document_id"),
                func.max(DocumentReview.id).label("ultimo_id"),
            )
            .where(DocumentReview.document_id.in_(ids))
            .group_by(DocumentReview.document_id)
            .subquery()
        )
        observaciones = {
            fila.document_id: _UltimaObservacion(
                observacion=fila.observacion,
                created_at=fila.created_at,
                accion=fila.accion,
                estado_anterior=fila.estado_anterior,
                estado_nuevo=fila.estado_nuevo,
                admin_username=fila.admin_username,
            )
            for fila in db.execute(
                select(
                    DocumentReview.document_id,
                    DocumentReview.observacion,
                    DocumentReview.created_at,
                    DocumentReview.accion,
                    DocumentReview.estado_anterior,
                    DocumentReview.estado_nuevo,
                    DocumentReview.admin_username,
                ).join(ultimos_ids, DocumentReview.id == ultimos_ids.c.ultimo_id)
            )
        }

        # El total necesita su propio GROUP BY, pero el indice
        # (document_id, created_at, id) lo resuelve como covering index.
        totales = dict(
            db.execute(
                select(DocumentReview.document_id, func.count())
                .where(DocumentReview.document_id.in_(ids))
                .group_by(DocumentReview.document_id)
            ).all()
        )

    return _Enriquecimiento(
        lotes=lotes,
        usuarios=usuarios,
        observaciones=observaciones,
        totales=totales,
    )


def _construir_documento_read(
    document: Document, datos: _Enriquecimiento
) -> AdminDocumentoRead:
    """Proyecta una fila. Todo lo que no esta en `documents` viene de `datos`."""
    observacion = datos.observaciones.get(document.id)
    lote = datos.lotes.get(document.batch_id) if document.batch_id else None

    return AdminDocumentoRead(
        id=document.id,
        nombre_archivo=document.nombre_archivo,
        batch_id=document.batch_id,
        lote_nombre=lote.nombre_lote if lote else None,
        user_id=document.user_id,
        usuario_nombre=datos.usuarios.get(document.user_id) if document.user_id else None,
        clasificacion=document.clasificacion,
        confianza=document.confianza,
        motivo=document.motivo,
        palabras=parse_palabras(document.palabras),
        requiere_revision=document.requiere_revision,
        estado=document.estado,
        fecha_subida=lote.fecha_creacion if lote else None,
        ultima_observacion=observacion.observacion if observacion else None,
        ultima_observacion_fecha=observacion.created_at if observacion else None,
        ultima_observacion_accion=observacion.accion if observacion else None,
        ultima_observacion_estado_anterior=(
            observacion.estado_anterior if observacion else None
        ),
        ultima_observacion_estado_nuevo=(
            observacion.estado_nuevo if observacion else None
        ),
        ultima_observacion_admin=observacion.admin_username if observacion else None,
        total_observaciones=datos.totales.get(document.id, 0),
    )


def _documento_read(db: Session, document: Document) -> AdminDocumentoRead:
    """Proyeccion de un unico documento (respuestas de una sola fila).

    Delega en _enriquecer/_construir_documento_read para que este camino y el
    del listado no puedan divergir en los campos que exponen.
    """
    return _construir_documento_read(document, _enriquecer(db, [document]))


def _documentos_read(
    db: Session, documentos: Sequence[Document]
) -> list[AdminDocumentoRead]:
    """Proyecta una pagina entera con 4 consultas, no ~3 por documento."""
    if not documentos:
        return []
    datos = _enriquecer(db, documentos)
    return [_construir_documento_read(document, datos) for document in documentos]


def _registrar_observacion(
    db: Session,
    document: Document,
    admin: User,
    accion: str,
    observacion: str,
    estado_anterior: str | None,
    estado_nuevo: str | None,
) -> DocumentReview:
    review = DocumentReview(
        document_id=document.id,
        nombre_archivo=document.nombre_archivo,
        admin_user_id=admin.id,
        admin_username=admin.username,
        usuario_id=document.user_id,
        usuario_username=_nombre_de_usuario(db, document.user_id),
        accion=accion,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        observacion=observacion,
    )
    db.add(review)
    return review


@router.get("", response_model=DocumentosPaginadosRead)
def listar_documentos(
    estado: str | None = Query(default=None),
    usuario_id: int | None = Query(default=None),
    texto: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    # 0 desactiva el corte y devuelve todo: lo usan los tests y cualquier
    # consumidor interno que necesite el listado completo.
    por_pagina: int = Query(default=PAGINA_POR_DEFECTO, ge=0, le=MAX_POR_PAGINA),
    db: Session = Depends(get_db),
) -> DocumentosPaginadosRead:
    """Todos los documentos de todos los usuarios, con filtros opcionales.

    A diferencia del listado del propio usuario, no filtra por user_id salvo que
    se pida explicitamente en el query.

    Va paginado a proposito: el listado completo podia traer cientos de filas y
    el panel los recorre con 3 queries por documento. `por_pagina=0` devuelve
    todo sin paginar, que es lo que necesitan los tests y los consumidores
    internos.

    El enriquecimiento (lote, dueno, ultima observacion y total) se resuelve
    para toda la pagina con 4 consultas en _documentos_read, no documento a
    documento.
    """
    consulta = select(Document).order_by(Document.nombre_archivo, Document.id)

    if estado:
        consulta = consulta.where(Document.estado == estado.strip().upper())
    if usuario_id is not None:
        consulta = consulta.where(Document.user_id == usuario_id)
    if texto and texto.strip():
        consulta = consulta.where(Document.nombre_archivo.like(f"%{texto.strip()}%"))

    total = db.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0

    if por_pagina:
        consulta = consulta.offset((pagina - 1) * por_pagina).limit(por_pagina)

    documentos = db.scalars(consulta).all()
    return DocumentosPaginadosRead(
        total=total,
        pagina=1 if not por_pagina else pagina,
        por_pagina=por_pagina,
        documentos=_documentos_read(db, documentos),
    )


@router.get("/resumen", response_model=dict)
def resumen_documentos(db: Session = Depends(get_db)):
    filas_estado = (
        db.query(Document.estado, func.count()).group_by(Document.estado).all()
    )
    conteo = {e: total for e, total in filas_estado if e in ESTADOS}
    por_estado = [
        EstadoConteo(estado=e, total=conteo.get(e, 0)) for e in ESTADOS
    ]
    return {"total": sum(conteo.values()), "por_estado": por_estado}


@router.get("/{document_id}/observaciones", response_model=list[DocumentReviewRead])
def listar_observaciones(document_id: str, db: Session = Depends(get_db)):
    """Historial de un documento.

    No se comprueba que el documento siga existiendo: el historial tiene que
    poder consultarse aunque el documento se haya borrado, que es justo cuando
    mas interesa saber por que se borro.
    """
    return (
        db.scalars(
            select(DocumentReview)
            .where(DocumentReview.document_id == document_id)
            .order_by(DocumentReview.created_at.desc(), DocumentReview.id.desc())
        )
        .all()
    )


@router.get("/{document_id}/analisis", response_model=AnalisisDocumentoRead)
def analisis_documento(document_id: str, db: Session = Depends(get_db)):
    """Palabras clave para el resaltado. El admin puede ver el analisis de
    cualquier documento, no solo de los suyos."""
    document = _get_documento(db, document_id)
    categoria = document.clasificacion or "OTRO"
    return AnalisisDocumentoRead(
        categoria=categoria,
        palabras=parse_palabras(document.palabras)
        or list(CATEGORY_KEYWORDS.get(categoria, [])),
    )


@router.get("/{document_id}/archivo", response_class=FileResponse)
def ver_archivo(document_id: str, db: Session = Depends(get_db)):
    document = _get_documento(db, document_id)
    ruta = Path(document.ruta_fisica)
    if not ruta.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El archivo ya no está disponible en el servidor",
        )
    return FileResponse(
        ruta,
        media_type="application/pdf",
        filename=document.nombre_archivo,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, no-store"},
    )


@router.patch("/{document_id}/estado", response_model=AccionAplicada)
def actualizar_estado(
    document_id: str,
    payload: AdminEstadoUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Aprobar, rechazar o volver a pendiente.

    El admin si puede salir de un estado final (APROBADO / RECHAZADO): es la
    diferencia con el endpoint del usuario, que los trata como terminales.
    """
    nuevo_estado = payload.estado_normalizado()
    if not payload.es_valido():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Usa uno de: {', '.join(ESTADOS)}.",
        )

    document = _get_documento(db, document_id)
    estado_anterior = document.estado

    document.estado = nuevo_estado
    document.requiere_revision = requiere_revision_desde_estado(nuevo_estado)

    review = _registrar_observacion(
        db,
        document,
        admin,
        ACCION_POR_ESTADO[nuevo_estado],
        payload.observacion,
        estado_anterior,
        nuevo_estado,
    )
    db.commit()
    db.refresh(review)

    return AccionAplicada(
        documento=_documento_read(db, document),
        observacion=DocumentReviewRead.model_validate(review),
    )


@router.delete("/{document_id}", response_model=AccionAplicada)
def eliminar_documento(
    document_id: str,
    payload: AdminEliminarUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Borra el documento y su PDF, pero conserva la observacion.

    El archivo fisico se borra despues del commit, igual que en el endpoint del
    usuario: si el commit falla el PDF sigue en disco y se puede reintentar.
    """
    document = _get_documento(db, document_id)
    ruta = document.ruta_fisica

    review = _registrar_observacion(
        db,
        document,
        admin,
        ACCION_ELIMINAR,
        payload.observacion,
        document.estado,
        None,
    )
    db.delete(document)
    db.flush()
    db.commit()
    db.refresh(review)

    if ruta and os.path.isfile(ruta):
        try:
            os.remove(ruta)
        except OSError:
            pass

    return AccionAplicada(
        documento=None,
        observacion=DocumentReviewRead.model_validate(review),
    )
