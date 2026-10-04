from sqlalchemy import select

from .config import get_settings
from .database import SessionLocal
from .models import Role, User, user_roles
from .security import hash_password

ROLES_DISPONIBLES = ("admin", "user")


def seed_admin() -> None:
    settings = get_settings()
    username = settings.admin_username.strip()
    password = settings.admin_password
    if not username or not password:
        return

    with SessionLocal() as db:
        existe = db.scalar(select(User).where(User.username == username))
        if existe is not None:
            return
        rol_admin = db.scalar(select(Role).where(Role.nombre == "admin"))
        if rol_admin is None:
            return
        admin = User(username=username, password_hash=hash_password(password))
        admin.roles.append(rol_admin)
        db.add(admin)
        db.commit()


def seed_roles() -> None:
    with SessionLocal() as db:
        existentes = set(db.scalars(select(Role.nombre)).all())
        for nombre in ROLES_DISPONIBLES:
            if nombre not in existentes:
                db.add(Role(nombre=nombre))
        db.commit()

        rol_user = db.scalar(select(Role).where(Role.nombre == "user"))
        usuarios_sin_rol = db.scalars(
            select(User)
            .outerjoin(user_roles, user_roles.c.user_id == User.id)
            .where(user_roles.c.user_id.is_(None))
        ).all()
        for usuario in usuarios_sin_rol:
            usuario.roles.append(rol_user)
        db.commit()

        hay_admin = (
            db.scalar(
                select(Role)
                .where(Role.nombre == "admin")
                .join(user_roles, user_roles.c.role_id == Role.id)
                .limit(1)
            )
            is not None
        )
        if not hay_admin:
            rol_admin = db.scalar(select(Role).where(Role.nombre == "admin"))
            primer_usuario = db.scalars(
                select(User).order_by(User.created_at.asc(), User.username.asc()).limit(1)
            ).first()
            if primer_usuario is not None and rol_admin is not None:
                primer_usuario.roles.append(rol_admin)
                db.commit()