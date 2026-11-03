"""Conexión a la base de datos relacional (MySQL) con SQLAlchemy."""

import sys

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import make_url, URL
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


def _crear_base_si_no_existe():
    """Si la base (ej. 'kira') no existe en MySQL, la crea."""
    url = make_url(DATABASE_URL)
    if not url.drivername.startswith("mysql") or not url.database:
        return
    sin_base = URL.create(
        drivername=url.drivername, username=url.username, password=url.password,
        host=url.host, port=url.port, query=url.query,
    )
    servidor = create_engine(sin_base, future=True)
    try:
        with servidor.connect() as con:
            con.execute(text(
                f"CREATE DATABASE IF NOT EXISTS `{url.database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            ))
    except OperationalError as e:
        # 1044: el usuario de privilegio mínimo (kira_app) no puede crear bases.
        # No es un problema si la base ya existe (la creó el administrador).
        if not (getattr(e, "orig", None) and e.orig.args and e.orig.args[0] == 1044):
            raise
    finally:
        servidor.dispose()


# Columnas agregadas después de la primera versión. create_all() no modifica
# tablas que ya existen, así que se agregan aquí con ALTER TABLE si faltan.
COLUMNAS_NUEVAS = {
    "usuarios": {
        "email_verificado": "BOOLEAN NOT NULL DEFAULT 0",
        "codigo_hash": "VARCHAR(255) NULL",
        "codigo_expira": "DATETIME NULL",
        "codigo_intentos": "INTEGER NOT NULL DEFAULT 0",
        "codigo_enviado_en": "DATETIME NULL",
        "acepta_privacidad_en": "DATETIME NULL",
    },
    "historial_chat": {
        "tokens_entrada": "INTEGER NOT NULL DEFAULT 0",
        "tokens_salida": "INTEGER NOT NULL DEFAULT 0",
        "latencia_ms": "INTEGER NOT NULL DEFAULT 0",
    },
}


def _migrar_columnas():
    insp = inspect(engine)
    for tabla, columnas in COLUMNAS_NUEVAS.items():
        if not insp.has_table(tabla):
            continue
        existentes = {c["name"] for c in insp.get_columns(tabla)}
        for nombre, tipo in columnas.items():
            if nombre in existentes:
                continue
            try:
                with engine.begin() as con:
                    con.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}"))
                print(f"  · columna agregada: {tabla}.{nombre}")
            except (OperationalError, ProgrammingError) as e:
                # Con el usuario de privilegio mínimo (kira_app) la app no puede alterar
                # tablas: la estructura la actualiza el administrador con database/schema.sql
                print(f"✗ Falta la columna {tabla}.{nombre} y este usuario no puede crearla ({e.orig}).")
                print("  Pídele al administrador que ejecute database/schema.sql con el usuario root.")
                sys.exit(1)


def crear_tablas():
    """Crea la base y las tablas si no existen (equivalente a database/schema.sql)."""
    from backend.models import usuario, chat  # noqa: F401  (registra los modelos)
    try:
        _crear_base_si_no_existe()
        Base.metadata.create_all(bind=engine)
        _migrar_columnas()
        print(f"✓ Conectado a la base de datos: {make_url(DATABASE_URL).render_as_string(hide_password=True)}")
    except OperationalError as e:
        codigo = e.orig.args[0] if getattr(e, "orig", None) and e.orig.args else None
        print("\n✗ No se pudo conectar a MySQL.")
        if codigo == 1045:
            print("  Usuario o contraseña incorrectos. Revisa DATABASE_URL en el archivo .env")
        elif codigo in (2003, 2002):
            print("  MySQL no está encendido o no está instalado en este computador.")
            print("  Enciéndelo (Servicios de Windows → MySQL80 → Iniciar, o desde XAMPP) y vuelve a intentar.")
        else:
            print(f"  Detalle: {e.orig if getattr(e, 'orig', None) else e}")
        sys.exit(1)
