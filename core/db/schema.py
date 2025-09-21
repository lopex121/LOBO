# core/db/schema.py

from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)  # cambio de nombre
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    role = Column(String, default="visita")

    def __repr__(self):
        return f"<User(username='{self.username}', active={self.is_active})>"

class MemoryNote(Base):
    __tablename__ = "memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<MemoryNote(type='{self.type}', content='{self.content}')>"

class BitacoraRegistro(Base):
    __tablename__ = "bitacora"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    modulo = Column(String, nullable=False)
    accion = Column(String, nullable=False)
    descripcion = Column(String)
    usuario = Column(String)

class BitacoraGlobal(Base):
    __tablename__ = "bitacoraglobal"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    session_id = Column(String)
    nivel = Column(String)
    mensaje = Column(String)