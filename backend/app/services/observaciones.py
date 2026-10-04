"""Última observación del admin por documento (tabla `document_reviews`).

El panel de administración es el único que escribe en `document_reviews`: cada
aprobación, rechazo, devolución a pendiente o borrado deja una fila. Aquí se
expone la última de esas filas también al dueño del documento, para que sepa
por qué cambió de estado sin tener que abrir el panel de admin.
"""

from sqlalchemy.orm import Session

from ..models import Document, DocumentReview


def adjuntar_ultima_observacion(db: Session, documents: list[Document]) -> None:
    """Copia la última observación de cada documento a atributos de instancia.

    Se asignan como atributos normales (no son columnas del modelo) para que
    Pydantic los lea con `from_attributes` sin tocar el mapeo. Se resuelve todo
    con una sola consulta: sin N+1 aunque el lote traiga varios documentos.
    """
    ids = [doc.id for doc in documents]
    if not ids:
        return

    ultimas: dict[str, DocumentReview] = {}
    filas = (
        db.query(DocumentReview)
        .filter(DocumentReview.document_id.in_(ids))
        .order_by(DocumentReview.id.desc())
        .all()
    )
    for fila in filas:
        # El ORDER BY es descendente: la primera que aparece es la más reciente.
        ultimas.setdefault(fila.document_id, fila)

    for doc in documents:
        review = ultimas.get(doc.id)
        doc.ultima_observacion = review.observacion if review else None
        doc.ultima_observacion_fecha = review.created_at if review else None
        doc.ultima_observacion_accion = review.accion if review else None
        doc.ultima_observacion_estado_anterior = (
            review.estado_anterior if review else None
        )
        doc.ultima_observacion_estado_nuevo = review.estado_nuevo if review else None
        doc.ultima_observacion_admin = review.admin_username if review else None
