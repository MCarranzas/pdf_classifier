import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

COLUMN_DEFINITIONS: dict[str, dict[str, str]] = {
    "documents": {
        "confianza": "FLOAT NULL",
        "motivo": "VARCHAR(500) NULL",
        "requiere_revision": "BOOLEAN NOT NULL DEFAULT 0",
        "user_id": "INT NULL",
        "hash_archivo": "VARCHAR(64) NULL",
        "estado": "VARCHAR(20) NOT NULL DEFAULT 'APROBADO'",
        "palabras": "TEXT NULL",
    },
    "batches": {
        "user_id": "INT NULL",
    },
}

INDEXED_COLUMNS = ("user_id", "hash_archivo")

TABLAS_A_MIGRAR = ("users", "roles")
TABLAS_CON_DONO = ("batches", "documents")


class Base(DeclarativeBase):
    pass


def _ensure_columns(table: str, definitions: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table)}
    existing_indexes = {index["name"] for index in inspector.get_indexes(table)}
    has_user_fk = any(
        fk["referred_table"] == "users" for fk in inspector.get_foreign_keys(table)
    )

    with engine.begin() as connection:
        for column_name, definition in definitions.items():
            if column_name in existing_columns:
                continue
            connection.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column_name} {definition}")
            )

        for column_name in INDEXED_COLUMNS:
            index_name = f"ix_{table}_{column_name}"
            if column_name not in definitions or index_name in existing_indexes:
                continue
            connection.execute(
                text(f"CREATE INDEX {index_name} ON {table} ({column_name})")
            )

        if "user_id" in definitions and not has_user_fk:
            connection.execute(
                text(
                    f"ALTER TABLE {table} ADD CONSTRAINT {table}_user_id_fk "
                    f"FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
                )
            )


def _normalize_categories() -> None:
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE documents SET clasificacion = UPPER(clasificacion) "
                "WHERE clasificacion IS NOT NULL "
                "AND BINARY clasificacion <> BINARY UPPER(clasificacion)"
            )
        )


def _backfill_hash_archivo() -> None:
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return
    columnas = {col["name"] for col in inspector.get_columns("documents")}
    if "hash_archivo" not in columnas:
        return
    with engine.begin() as connection:
        filas = connection.execute(
            text("SELECT id, ruta_fisica FROM documents WHERE hash_archivo IS NULL")
        ).fetchall()
        for doc_id, ruta in filas:
            try:
                digest = hashlib.sha256(Path(ruta).read_bytes()).hexdigest()
            except OSError:
                continue
            connection.execute(
                text("UPDATE documents SET hash_archivo = :h WHERE id = :i"),
                {"h": digest, "i": doc_id},
            )


def _ensure_hash_unique_index() -> None:
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return
    columnas = {col["name"] for col in inspector.get_columns("documents")}
    if "hash_archivo" not in columnas:
        return
    if "uq_documents_hash_archivo" in {idx["name"] for idx in inspector.get_indexes("documents")}:
        return

    with engine.begin() as connection:
        con_duplicados = connection.execute(
            text(
                "SELECT 1 FROM documents WHERE hash_archivo IS NOT NULL "
                "GROUP BY hash_archivo HAVING COUNT(*) > 1 LIMIT 1"
            )
        ).scalar()
        if con_duplicados:
            return
        connection.execute(
            text("CREATE UNIQUE INDEX uq_documents_hash_archivo ON documents (hash_archivo)")
        )


def _backfill_estado() -> None:
    from .models import ESTADO_APROBADO, ESTADO_PENDIENTE

    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return
    columnas = {col["name"] for col in inspector.get_columns("documents")}
    if not {"estado", "requiere_revision"} <= columnas:
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE documents SET estado = :pendiente "
                "WHERE requiere_revision = 1 AND estado = :aprobado"
            ),
            {"pendiente": ESTADO_PENDIENTE, "aprobado": ESTADO_APROBADO},
        )


# --------------------------------------------------------------------------- #
# Migracion de users.id y roles.id: UUID (VARCHAR 36) -> entero AUTO_INCREMENT
# --------------------------------------------------------------------------- #

CHARSET = "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"


def _tipo_de_columna(connection, tabla: str, columna: str = "id") -> str:
    tipo = connection.execute(
        text(
            "SELECT DATA_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
        ),
        {"t": tabla, "c": columna},
    ).scalar()
    return (tipo or "").lower()


def _id_ya_es_entero(connection, tabla: str) -> bool:
    return _tipo_de_columna(connection, tabla) == "int"


def _volcar_respaldo(connection, tablas: tuple[str, ...], destino: Path, motivo: str) -> None:
    """Vuelca las tablas indicadas a un .sql por si la migracion sale mal."""
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    def literal(valor) -> str:
        if valor is None:
            return "NULL"
        return "'" + str(valor).replace("\\", "\\\\").replace("'", "''") + "'"

    lineas = [
        f"-- Respaldo automatico de {motivo} antes de migrar el id a entero.",
        f"-- Generado el {ahora} por app.database._volcar_respaldo.",
        "SET FOREIGN_KEY_CHECKS = 0;",
    ]
    for tabla in tablas:
        filas = connection.execute(text(f"SELECT * FROM {tabla}")).fetchall()
        if not filas:
            continue
        columnas = [
            fila[0]
            for fila in connection.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                    "ORDER BY ORDINAL_POSITION"
                ),
                {"t": tabla},
            )
        ]
        valores = [f"({', '.join(literal(v) for v in fila)})" for fila in filas]
        lineas.append(f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES")
        lineas.append(",\n".join(valores) + ";")

    lineas.append("SET FOREIGN_KEY_CHECKS = 1;")
    lineas.append("")

    try:
        destino.write_text("\n".join(lineas), encoding="utf-8")
    except OSError:
        pass


def _migrate_ids_a_entero() -> None:
    inspector = inspect(engine)
    tablas = set(inspector.get_table_names())
    if not set(TABLAS_A_MIGRAR) <= tablas:
        return

    with engine.begin() as connection:
        if all(_id_ya_es_entero(connection, tabla) for tabla in TABLAS_A_MIGRAR):
            return

        _volcar_respaldo(
            connection,
            ("users", "roles", "user_roles"),
            Path(__file__).resolve().parent.parent / "respaldo_usuarios_uuid.sql",
            "users/roles/user_roles",
        )

        # Mapa UUID -> entero, en orden estable (created_at, luego username, luego id).
        mapa_usuarios = {
            uuid_texto: nuevo
            for nuevo, uuid_texto in enumerate(
                connection.execute(
                    text("SELECT id FROM users ORDER BY created_at, username, id")
                ).scalars(),
                start=1,
            )
        }
        mapa_roles = {
            uuid_texto: nuevo
            for nuevo, uuid_texto in enumerate(
                connection.execute(text("SELECT id FROM roles ORDER BY nombre, id")).scalars(),
                start=1,
            )
        }

        # 1. Eliminar las FKs que apuntan a users/roles. Sin ellas el resto de la
        #    migracion no necesita FOREIGN_KEY_CHECKS (que en MariaDB es de sesion
        #    y se filtraria al pool de conexiones).
        fks = connection.execute(
            text(
                "SELECT TABLE_NAME, CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND REFERENCED_TABLE_NAME IN ('users', 'roles') "
                "AND TABLE_NAME IN ('batches', 'documents', 'user_roles')"
            )
        ).fetchall()
        for tabla, constraint in fks:
            connection.execute(text(f"ALTER TABLE `{tabla}` DROP FOREIGN KEY `{constraint}`"))

        # 2. users -> id entero
        connection.execute(
            text(
                "CREATE TABLE users_mig ("
                " id INT NOT NULL AUTO_INCREMENT,"
                " username VARCHAR(100) NOT NULL,"
                " password_hash VARCHAR(255) NOT NULL,"
                " created_at DATETIME NOT NULL,"
                " PRIMARY KEY (id),"
                " UNIQUE KEY uq_users_username (username)"
                f") {CHARSET}"
            )
        )
        for uuid_texto, nuevo in mapa_usuarios.items():
            origen = connection.execute(
                text("SELECT username, password_hash, created_at FROM users WHERE id = :i"),
                {"i": uuid_texto},
            ).one_or_none()
            if origen is None:
                continue
            connection.execute(
                text(
                    "INSERT INTO users_mig (id, username, password_hash, created_at) "
                    "VALUES (:id, :u, :p, :c)"
                ),
                {"id": nuevo, "u": origen[0], "p": origen[1], "c": origen[2]},
            )
        connection.execute(text("DROP TABLE users"))
        connection.execute(text("RENAME TABLE users_mig TO users"))

        # 3. roles -> id entero
        connection.execute(
            text(
                "CREATE TABLE roles_mig ("
                " id INT NOT NULL AUTO_INCREMENT,"
                " nombre VARCHAR(50) NOT NULL,"
                " PRIMARY KEY (id),"
                " UNIQUE KEY uq_roles_nombre (nombre)"
                f") {CHARSET}"
            )
        )
        for uuid_texto, nuevo in mapa_roles.items():
            origen = connection.execute(
                text("SELECT nombre FROM roles WHERE id = :i"), {"i": uuid_texto}
            ).one_or_none()
            if origen is None:
                continue
            connection.execute(
                text("INSERT INTO roles_mig (id, nombre) VALUES (:id, :n)"),
                {"id": nuevo, "n": origen[0]},
            )
        connection.execute(text("DROP TABLE roles"))
        connection.execute(text("RENAME TABLE roles_mig TO roles"))

        # 4. user_roles -> ambas columnas enteras
        if "user_roles" in tablas:
            asignaciones = connection.execute(
                text("SELECT user_id, role_id FROM user_roles")
            ).fetchall()
            connection.execute(text("DROP TABLE user_roles"))
            connection.execute(
                text(
                    "CREATE TABLE user_roles ("
                    " user_id INT NOT NULL,"
                    " role_id INT NOT NULL,"
                    " PRIMARY KEY (user_id, role_id),"
                    " KEY ix_user_roles_role_id (role_id),"
                    " CONSTRAINT user_roles_user_id_fk FOREIGN KEY (user_id) "
                    "REFERENCES users(id) ON DELETE CASCADE,"
                    " CONSTRAINT user_roles_role_id_fk FOREIGN KEY (role_id) "
                    f"REFERENCES roles(id) ON DELETE CASCADE) {CHARSET}"
                )
            )
            for user_antiguo, rol_antiguo in asignaciones:
                nuevo_usuario = mapa_usuarios.get(user_antiguo)
                nuevo_rol = mapa_roles.get(rol_antiguo)
                if nuevo_usuario is None or nuevo_rol is None:
                    continue
                connection.execute(
                    text("INSERT INTO user_roles (user_id, role_id) VALUES (:u, :r)"),
                    {"u": nuevo_usuario, "r": nuevo_rol},
                )

        # 5. batches.user_id y documents.user_id -> entero con el mapa.
        #    Al DROP COLUMN se van tambien sus indices, asi que se recrean.
        for tabla in TABLAS_CON_DONO:
            if tabla not in tablas:
                continue
            columnas = {col["name"] for col in inspect(engine).get_columns(tabla)}
            if "user_id" not in columnas:
                continue
            connection.execute(text(f"ALTER TABLE `{tabla}` ADD COLUMN user_id_mig INT NULL"))
            for uuid_texto, nuevo in mapa_usuarios.items():
                connection.execute(
                    text(f"UPDATE `{tabla}` SET user_id_mig = :n WHERE user_id = :v"),
                    {"n": nuevo, "v": uuid_texto},
                )
            connection.execute(text(f"ALTER TABLE `{tabla}` DROP COLUMN user_id"))
            connection.execute(
                text(f"ALTER TABLE `{tabla}` CHANGE user_id_mig user_id INT NULL")
            )
            connection.execute(text(f"CREATE INDEX ix_{tabla}_user_id ON `{tabla}` (user_id)"))
            connection.execute(
                text(
                    f"ALTER TABLE `{tabla}` ADD CONSTRAINT {tabla}_user_id_fk "
                    f"FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
                )
            )


# --------------------------------------------------------------------------- #
# Migracion de batches.id y documents.batch_id: UUID (VARCHAR 36) -> entero
# AUTO_INCREMENT. Implica renombrar las carpetas uploads/<uuid>/ a uploads/<id>/.
# --------------------------------------------------------------------------- #


def _soltar_fks(connection, tabla: str, referenciadas: tuple[str, ...]) -> None:
    """Quita las FKs de una tabla. Sin ellas el resto de la migracion no necesita
    FOREIGN_KEY_CHECKS (que en MariaDB es de sesion y se filtraria al pool)."""
    filtros = ", ".join(f"'{t}'" for t in referenciadas)
    constraints = connection.execute(
        text(
            "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
            f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{tabla}' "
            f"AND REFERENCED_TABLE_NAME IN ({filtros})"
        )
    ).scalars()
    for constraint in constraints:
        connection.execute(text(f"ALTER TABLE `{tabla}` DROP FOREIGN KEY `{constraint}`"))


def _mapa_batches_a_entero(connection) -> dict:
    """UUID (o id actual) -> entero, en orden estable (fecha_creacion, luego id)."""
    return {
        clave: nuevo
        for nuevo, clave in enumerate(
            connection.execute(
                text("SELECT id FROM batches ORDER BY fecha_creacion, id")
            ).scalars(),
            start=1,
        )
    }


def _recrear_batches_con_id_entero(connection, mapa_batches: dict) -> None:
    connection.execute(
        text(
            "CREATE TABLE batches_mig ("
            " id INT NOT NULL AUTO_INCREMENT,"
            " nombre_lote VARCHAR(255) NOT NULL,"
            " fecha_creacion DATETIME NOT NULL,"
            " user_id INT NULL,"
            " PRIMARY KEY (id),"
            " KEY ix_batches_user_id (user_id),"
            " CONSTRAINT batches_user_id_fk FOREIGN KEY (user_id) "
            "REFERENCES users(id) ON DELETE CASCADE"
            f") {CHARSET}"
        )
    )
    for clave, nuevo in mapa_batches.items():
        origen = connection.execute(
            text("SELECT nombre_lote, fecha_creacion, user_id FROM batches WHERE id = :i"),
            {"i": clave},
        ).one_or_none()
        if origen is None:
            continue
        connection.execute(
            text(
                "INSERT INTO batches_mig (id, nombre_lote, fecha_creacion, user_id) "
                "VALUES (:id, :n, :f, :u)"
            ),
            {"id": nuevo, "n": origen[0], "f": origen[1], "u": origen[2]},
        )
    connection.execute(text("DROP TABLE batches"))
    connection.execute(text("RENAME TABLE batches_mig TO batches"))


def _remapear_documents_batch_id(connection, mapa_batches: dict) -> None:
    # Al DROP COLUMN se van tambien sus indices, asi que se recrean.
    connection.execute(text("ALTER TABLE `documents` ADD COLUMN batch_id_mig INT NULL"))
    for clave, nuevo in mapa_batches.items():
        connection.execute(
            text("UPDATE `documents` SET batch_id_mig = :n WHERE batch_id = :v"),
            {"n": nuevo, "v": clave},
        )
    connection.execute(text("ALTER TABLE `documents` DROP COLUMN batch_id"))
    connection.execute(
        text("ALTER TABLE `documents` CHANGE batch_id_mig batch_id INT NULL")
    )
    connection.execute(
        text(
            "ALTER TABLE `documents` ADD CONSTRAINT documents_batch_id_fk "
            "FOREIGN KEY (batch_id) REFERENCES batches(id)"
        )
    )


def _reubicar_uploads_de_lotes(connection, mapa_batches: dict, documentos) -> None:
    """Renombra uploads/<uuid>/ a uploads/<entero>/ y sigue la ruta en la BD."""
    uploads_path = get_settings().uploads_path
    por_lote: dict = {}
    for doc_id, batch_id, ruta in documentos:
        por_lote.setdefault(batch_id, []).append((doc_id, ruta))

    for clave, nuevo in mapa_batches.items():
        origen = uploads_path / str(clave)
        destino = uploads_path / str(nuevo)
        if origen != destino and origen.is_dir() and not destino.exists():
            try:
                origen.rename(destino)
            except OSError:
                pass
        for doc_id, ruta in por_lote.get(clave, ()):
            carpeta = Path(ruta).parent if ruta else None
            if carpeta is None or carpeta.name != str(clave):
                continue
            connection.execute(
                text("UPDATE documents SET ruta_fisica = :r WHERE id = :i"),
                {"r": str(carpeta.parent / str(nuevo) / Path(ruta).name), "i": doc_id},
            )


def _migrate_batches_id_a_entero() -> None:
    inspector = inspect(engine)
    tablas = set(inspector.get_table_names())
    if "batches" not in tablas:
        return

    documentos = "documents" in tablas and "batch_id" in {
        col["name"] for col in inspector.get_columns("documents")
    }

    with engine.begin() as connection:
        batches_ya_es_entero = _id_ya_es_entero(connection, "batches")
        documentos_ya_es_entero = documentos and _tipo_de_columna(
            connection, "documents", "batch_id"
        ) == "int"
        if batches_ya_es_entero and (not documentos or documentos_ya_es_entero):
            return

        filas_documentos: list = []
        if documentos:
            _soltar_fks(connection, "documents", ("batches",))
            filas_documentos = connection.execute(
                text("SELECT id, batch_id, ruta_fisica FROM documents WHERE batch_id IS NOT NULL")
            ).fetchall()
        if not batches_ya_es_entero:
            # El nombre batches_user_id_fk esta ocupado hasta que se suelte la tabla
            # vieja: InnoDB exige nombres de constraint unicos en el esquema.
            _soltar_fks(connection, "batches", ("users", "roles"))

        _volcar_respaldo(
            connection,
            ("batches", "documents"),
            Path(__file__).resolve().parent.parent / "respaldo_lotes_uuid.sql",
            "batches/documents",
        )

        mapa_batches = _mapa_batches_a_entero(connection)

        if not batches_ya_es_entero:
            _recrear_batches_con_id_entero(connection, mapa_batches)
        if documentos and not documentos_ya_es_entero:
            _remapear_documents_batch_id(connection, mapa_batches)
        if documentos:
            _reubicar_uploads_de_lotes(connection, mapa_batches, filas_documentos)


def ensure_schema() -> None:
    _migrate_ids_a_entero()
    _migrate_batches_id_a_entero()
    for table, definitions in COLUMN_DEFINITIONS.items():
        _ensure_columns(table, definitions)
    _normalize_categories()
    _backfill_hash_archivo()
    _ensure_hash_unique_index()
    _backfill_estado()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
