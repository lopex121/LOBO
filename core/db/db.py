# core/db/db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.db.schema import Base
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../database/lobo.db'))
DB_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
