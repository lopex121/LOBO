# core/db/db.py
#
# ÚNICA fuente de verdad para el motor de base de datos de LOBO.
# core/db/sessions.py fue eliminado; todos los imports deben apuntar aquí.
#
# Uso:
#   from core.db.db import SessionLocal, engine, init_db

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from core.db.schema import Base
from core.exceptions import DatabaseError
import os
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Ruta de la base de datos
# ─────────────────────────────────────────────

DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../database/lobo.db")
)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# ─────────────────────────────────────────────
# Motor y fábrica de sesiones
# ─────────────────────────────────────────────

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ─────────────────────────────────────────────
# Inicialización de tablas
# ─────────────────────────────────────────────

def init_db() -> None:
    """
    Crea todas las tablas definidas en schema.py si no existen.
    Debe llamarse una vez al arrancar LOBO (ver main.py).
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Base de datos inicializada correctamente en: %s", DB_PATH)
    except Exception as e:
        raise DatabaseError(
            "No se pudo inicializar la base de datos.",
            details=str(e)
        )


# ─────────────────────────────────────────────
# Helper de contexto (uso recomendado)
# ─────────────────────────────────────────────

def get_db() -> Session:
    """
    Generador de sesión para uso con context manager.

    Uso recomendado:
        with get_db() as db:
            db.query(...)

    Garantiza cierre de sesión aunque ocurra una excepción.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise DatabaseError("Error durante operación de base de datos.", details=str(e))
    finally:
        db.close()
