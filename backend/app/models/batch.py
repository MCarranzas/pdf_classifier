from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .document import Document


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, default=None
    )
    nombre_lote: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    documents: Mapped[list[Document]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="Document.nombre_archivo",
    )