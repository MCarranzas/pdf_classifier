import shutil

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Batch, User
from ..schemas.document import BatchRead
from ..security import get_current_user
from ..services.observaciones import adjuntar_ultima_observacion

router = APIRouter(
    prefix="/api/batches",
    tags=["batches"],
    dependencies=[Depends(get_current_user)],
)


def _get_batch_del_usuario(db: Session, batch_id: int, user: User) -> Batch:
    batch = (
        db.query(Batch)
        .filter(Batch.id == batch_id, Batch.user_id == user.id)
        .one_or_none()
    )
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")
    return batch


@router.get("", response_model=list[BatchRead])
def list_batches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    batches = (
        db.query(Batch)
        .filter(Batch.user_id == user.id)
        .order_by(Batch.fecha_creacion.desc())
        .all()
    )
    # El dueño también ve por qué el admin cambió el estado de sus documentos.
    adjuntar_ultima_observacion(db, [doc for b in batches for doc in b.documents])
    return batches


@router.get("/{batch_id}", response_model=BatchRead)
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    batch = _get_batch_del_usuario(db, batch_id, user)
    adjuntar_ultima_observacion(db, list(batch.documents))
    return batch


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    batch = _get_batch_del_usuario(db, batch_id, user)

    upload_dir = get_settings().uploads_path / str(batch.id)
    db.delete(batch)
    db.commit()
    shutil.rmtree(upload_dir, ignore_errors=True)