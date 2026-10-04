from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base

ACCION_APROBAR = "APROBAR"
ACCION_RECHAZAR = "RECHAZAR"
ACCION_PENDIENTE = "PENDIENTE"
ACCION_ELIMINAR = "ELIMINAR"
ACCIONES = (ACCION_APROBAR, ACCION_RECHAZAR, ACCION_PENDIENTE, ACCION_ELIMINAR)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DocumentReview(Base):
    """Observaciones del administrador sobre un documento.

    Deliberadamente NO hay FK hacia documents: cuando el admin borra un
    documento, su historial tiene que sobrevivir para que quede constancia
    de por qué se borró. Por eso se guardan también copies del nombre del
    archivo y de los usuarios involucrados.
    """

    __tablename__ = "document_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)

    admin_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, default=None
    )
    admin_username: Mapped[str] = mapped_column(String(100), nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    usuario_username: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None
    )

    accion: Mapped[str] = mapped_column(String(20), nullable=False)
    estado_anterior: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    estado_nuevo: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)

    observacion: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
