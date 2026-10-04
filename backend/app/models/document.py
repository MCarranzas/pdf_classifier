from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .batch import Batch

ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_APROBADO = "APROBADO"
ESTADO_RECHAZADO = "RECHAZADO"
ESTADOS = (ESTADO_PENDIENTE, ESTADO_APROBADO, ESTADO_RECHAZADO)
ESTADOS_FINALES = (ESTADO_APROBADO, ESTADO_RECHAZADO)


def estado_desde_revision(requiere_revision: bool) -> str:
    return ESTADO_PENDIENTE if requiere_revision else ESTADO_APROBADO


def requiere_revision_desde_estado(estado: str) -> bool:
    return estado == ESTADO_PENDIENTE


def es_estado_final(estado: str) -> bool:
    """Aprobado y rechazado son terminales: no admiten ninguna transición."""
    return estado in ESTADOS_FINALES


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("batches.id"), nullable=True, default=None
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, default=None
    )
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_fisica: Mapped[str] = mapped_column(String(512), nullable=False)
    hash_archivo: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    clasificacion: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    confianza: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    motivo: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    palabras: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    requiere_revision: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ESTADO_APROBADO,
        server_default=text(f"'{ESTADO_APROBADO}'"),
    )

    batch: Mapped[Batch | None] = relationship(back_populates="documents", foreign_keys=[batch_id])