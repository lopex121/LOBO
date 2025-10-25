# core/db/schema.py

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Time, Enum as SAEnum, JSON
from sqlalchemy.orm import declarative_base
import datetime
import enum
import uuid

Base = declarative_base()

# Usuario
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

# Memoria
class MemoryNote(Base):
    __tablename__ = "memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String) # urgente, importante,idea, nota, tarea
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    fecha_limite = Column(Date, nullable=True) # Fecha de vencimiento
    hora_limite = Column(Time, nullable=True) # Hora de entrega/realización
    prioridad = Column(Integer, default=5) # 1 = urgente / 5 = normal
    estado = Column(String, default="pendiente") # pendiente, completada, cancelada
    creado_por =Column(String, default="system") # usuario que lo creó

    def __repr__(self):
        return f"<MemoryNote(type='{self.type}', content='{self.content}', estado='{self.estado}')>"

# Bitácoras
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

# Recurrencia (para eventos)
class RecurrenciaEnum(str, enum.Enum):
    unico = "unico"
    diario = "diario"
    semanal = "semanal"
    mensual = "mensual"

# Modelo Evento (agenda)
class Evento(Base):
    __tablename__ = "eventos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    descripcion = Column(String)
    fecha_inicio = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    recurrencia = Column(SAEnum(RecurrenciaEnum), default=RecurrenciaEnum.unico)
    etiquetas = Column(JSON, default=list)  # usa callable para evitar mutabilidad compartida
    creado_en = Column(DateTime, default=datetime.datetime.utcnow)
    modificado_en = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Evento(nombre='{self.nombre}', fecha={self.fecha_inicio}, {self.hora_inicio}-{self.hora_fin})>"