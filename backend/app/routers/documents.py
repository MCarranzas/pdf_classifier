import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import (
    ESTADO_RECHAZADO,
    ESTADOS,
    Batch,
    Document,
    DocumentReview,
    User,
    es_estado_final,
    estado_desde_revision,
    requiere_revision_desde_estado,
)
from ..schemas.document import (
    AnalisisDocumentoRead,
    CategoriaConteo,
    DocumentRead,
    DocumentReviewRead,
    EstadoConteo,
    EstadoUpdate,
    ResumenClasificaciones,
    RevisionUpdate,
    UploadedDocument,
    UploadResponse,
    dump_palabras,
    parse_palabras,
)
from ..security import get_current_user, require_admin
from ..services.classifier import CATEGORY_KEYWORDS, classify_document
from ..services.observaciones import adjuntar_ultima_observacion
from ..services.pdf_text import PdfNoClasificable, extraer_texto_primera_pagina

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"],
    dependencies=[Depends(get_current_user)],
)

MAX_FILES = 5


def _descartar_archivos(rutas: list[Path], upload_dir: Path) -> None:
    for ruta in rutas:
        try:
            ruta.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        upload_dir.rmdir()
    except OSError:
        pass


def _get_document_del_usuario(db: Session, document_id: str, user: User) -> Document:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user.id)
        .one_or_none()
    )
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado")
    return document


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: list[UploadFile] = File(...),
    nombre_lote: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debes subir al menos un PDF")
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Se permiten máximo {MAX_FILES} archivos por petición",
        )

    name = (nombre_lote or "").strip()
    if not name:
        name = f"Lote {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    batch = Batch(nombre_lote=name, user_id=user.id)
    db.add(batch)
    db.flush()

    upload_dir = get_settings().uploads_path / str(batch.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    results: list[UploadedDocument] = []
    escritos: list[Path] = []
    hashes_lote: set[str] = set()
    try:
        for file in files:
            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{file.filename}' no es un PDF",
                )

            raw = await file.read()
            digest = hashlib.sha256(raw).hexdigest()

            if digest in hashes_lote:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{file.filename}' se repite dentro del mismo lote.",
                )
            if db.scalar(select(Document.id).where(Document.hash_archivo == digest).limit(1)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{file.filename}' ya fue subido anteriormente en el sistema.",
                )

            try:
                text = extraer_texto_primera_pagina(raw, file.filename)
            except PdfNoClasificable as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=exc.mensaje,
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No se pudo leer '{file.filename}'.",
                )

            resultado = classify_document(text)
            safe_name = os.path.basename(file.filename.replace("\\", "/"))
            stored_name = f"{uuid.uuid4().hex}_{safe_name}"
            ruta = upload_dir / stored_name
            ruta.write_bytes(raw)
            escritos.append(ruta)

            document = Document(
                batch_id=batch.id,
                user_id=user.id,
                nombre_archivo=safe_name,
                ruta_fisica=str(ruta),
                hash_archivo=digest,
                clasificacion=resultado.clasificacion,
                confianza=resultado.confianza,
                motivo=resultado.motivo,
                palabras=dump_palabras(resultado.matches),
                requiere_revision=resultado.requiere_revision,
                estado=estado_desde_revision(resultado.requiere_revision),
            )
            db.add(document)
            hashes_lote.add(digest)
            results.append(
                UploadedDocument(
                    nombre_archivo=safe_name,
                    clasificacion=resultado.clasificacion,
                    confianza=resultado.confianza,
                    motivo=resultado.motivo,
                    palabras=resultado.matches,
                    requiere_revision=resultado.requiere_revision,
                    estado=estado_desde_revision(resultado.requiere_revision),
                )
            )

        db.commit()
    except IntegrityError:
        db.rollback()
        _descartar_archivos(escritos, upload_dir)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno de los archivos ya fue subido anteriormente en el sistema.",
        ) from None
    except BaseException:
        db.rollback()
        _descartar_archivos(escritos, upload_dir)
        raise

    return UploadResponse(batch_id=batch.id, nombre_lote=name, documents=results)


@router.get("", response_model=list[DocumentRead])
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    documents = db.query(Document).filter(Document.user_id == user.id).all()
    adjuntar_ultima_observacion(db, documents)
    return documents


@router.get("/resumen", response_model=ResumenClasificaciones)
def resumen_clasificaciones(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    rows = (
        db.query(Document.clasificacion, func.count())
        .group_by(Document.clasificacion)
        .all()
    )
    categorias = [
        CategoriaConteo(clasificacion=clasificacion, total=total)
        for clasificacion, total in rows
        if clasificacion is not None
    ]
    filas_estado = (
        db.query(Document.estado, func.count()).group_by(Document.estado).all()
    )
    conteo_estados = {
        estado: total
        for estado, total in filas_estado
        if estado in ESTADOS
    }
    estados = [
        EstadoConteo(estado=estado, total=conteo_estados.get(estado, 0))
        for estado in ESTADOS
    ]
    return ResumenClasificaciones(
        total=sum(c.total for c in categorias),
        categorias=categorias,
        estados=estados,
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = _get_document_del_usuario(db, document_id, user)

    ruta = document.ruta_fisica
    db.delete(document)
    db.commit()
    if ruta and os.path.isfile(ruta):
        os.remove(ruta)


def _palabras_de_categoria(categoria: str, guardadas: str | None) -> list[str]:
    """Palabras a buscar en el PDF. Se prefieren las guardadas al subir, que son
    las que se usaron de verdad. Si vinieron vacias se cae a la lista completa de
    la categoria: cubre los documentos anteriores a la columna y tambien el caso
    en que PyPDF2 no vio un texto que pdf.js si dibuja."""
    return parse_palabras(guardadas) or list(CATEGORY_KEYWORDS.get(categoria, []))


@router.get("/{document_id}/analisis", response_model=AnalisisDocumentoRead)
def analisis_documento(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Palabras clave de la categoria asignada. El resaltado en el PDF lo resuelve
    el cliente: PyPDF2 y pdf.js extraen el texto con espacios distintos, asi que
    las posiciones que devuelve el backend no encajarían con lo que se dibuja."""
    document = _get_document_del_usuario(db, document_id, user)
    categoria = document.clasificacion or "OTRO"
    return AnalisisDocumentoRead(
        categoria=categoria,
        palabras=_palabras_de_categoria(categoria, document.palabras),
    )


@router.get("/{document_id}/observaciones", response_model=list[DocumentReviewRead])
def listar_observaciones(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Historial de observaciones del admin sobre un documento del propio usuario.

    A diferencia del historial del panel de admin, aquí sí se comprueba que el
    documento sea del usuario: un usuario normal no debe poder leer el historial
    de documentos ajenos. Los documentos borrados no aparecen en su listado, así
    que no hay caso de historial huérfano que atender desde esta vista.
    """
    document = _get_document_del_usuario(db, document_id, user)
    return (
        db.scalars(
            select(DocumentReview)
            .where(DocumentReview.document_id == document.id)
            .order_by(DocumentReview.created_at.desc(), DocumentReview.id.desc())
        )
        .all()
    )


@router.get("/{document_id}/archivo", response_class=FileResponse)
def download_document(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = _get_document_del_usuario(db, document_id, user)

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


@router.patch("/{document_id}/revision", response_model=DocumentRead)
def update_revision(
    document_id: str,
    payload: RevisionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = _get_document_del_usuario(db, document_id, user)
    if es_estado_final(document.estado):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El documento está en estado {document.estado}, que es final. "
                "No se puede volver a marcar para revisión."
            ),
        )
    document.requiere_revision = payload.requiere_revision
    document.estado = estado_desde_revision(payload.requiere_revision)
    db.commit()
    db.refresh(document)
    adjuntar_ultima_observacion(db, [document])
    return document


@router.patch("/{document_id}/estado", response_model=DocumentRead)
def update_estado(
    document_id: str,
    payload: EstadoUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = _get_document_del_usuario(db, document_id, user)

    nuevo_estado = payload.estado_normalizado()
    if not payload.es_valido():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Usa uno de: {', '.join(ESTADOS)}.",
        )

    if es_estado_final(document.estado):
        if nuevo_estado == document.estado:
            adjuntar_ultima_observacion(db, [document])
            return document
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"El documento está en estado {document.estado}, que es final. "
                "No se puede cambiar a otro estado."
            ),
        )

    if nuevo_estado == ESTADO_RECHAZADO and not document.requiere_revision:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puedes rechazar documentos marcados con revisión.",
        )

    document.estado = nuevo_estado
    document.requiere_revision = requiere_revision_desde_estado(nuevo_estado)
    db.commit()
    db.refresh(document)
    adjuntar_ultima_observacion(db, [document])
    return document