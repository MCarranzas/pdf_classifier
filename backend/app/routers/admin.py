from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role, User
from ..schemas.auth import RolesAssignRequest, UserCreateRequest, UserRead
from ..security import hash_password, require_admin

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return user


def _roles_validas(db: Session, nombres: list[str] | None) -> list[Role]:
    nombres = [n.strip().lower() for n in (nombres or []) if n.strip()]
    if not nombres:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Debe asignarse al menos un rol")
    roles_bd = {rol.nombre: rol for rol in db.scalars(select(Role)).all()}
    desconocidas = set(nombres) - set(roles_bd)
    if desconocidas:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Rol(es) no válidos: {', '.join(sorted(desconocidas))}",
        )
    return [roles_bd[nombre] for nombre in dict.fromkeys(nombres)]


@router.get("/users", response_model=list[UserRead])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.created_at.desc())).all()


@router.get("/roles", response_model=list[str])
def listar_roles(db: Session = Depends(get_db)):
    return [rol.nombre for rol in db.scalars(select(Role).order_by(Role.nombre)).all()]


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def crear_usuario(payload: UserCreateRequest, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El usuario ya existe")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    user.roles = _roles_validas(db, payload.roles)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/roles", response_model=UserRead)
def asignar_roles(user_id: int, payload: RolesAssignRequest, db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    nuevas = _roles_validas(db, payload.roles)

    nombres_actuales = {rol.nombre for rol in user.roles}
    es_admin = "admin" in nombres_actuales
    sigue_admin = any(rol.nombre == "admin" for rol in nuevas)
    if es_admin and not sigue_admin:
        total_admins = sum(
            1
            for u in db.scalars(select(User)).all()
            if "admin" in {r.nombre for r in u.roles}
        )
        if total_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede quitar el rol admin al último administrador del sistema",
            )

    user.roles = nuevas
    db.commit()
    db.refresh(user)
    return user