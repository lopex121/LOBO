# core/db/manager.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .schema import Base

import os

DB_PATH = os.path.join(os.path.dirname(__file__), '../../core/database/lobo.db')
DB_URL = f"sqlite:///{DB_PATH}"

# Crear el engine y el session maker
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Crea todas las tablas definidas en schema.py usando el ORM."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Proporciona una sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
