# core/memory.py

from core.db.sessions import SessionLocal
from core.db.schema import MemoryNote
from sqlalchemy import and_, func
from sqlalchemy.orm.exc import NoResultFound
from core.context.logs import BITACORA
from core.context.global_session import SESSION
from datetime import datetime, date

class Memory:
    def __init__(self):
        self.db = SessionLocal()

    def remember(self, content, mem_type="nota", fecha_limite=None, hora_limite=None,
                 prioridad=None, usuario=None):
        """
        Guarda un recordatorio con campos extendidos

        Args:
            content: Texto del recordatorio
            mem_type: Tipo (urgente, importante, tarea, nota, idea)
            fecha_limite: datetime.date o str 'DD/MM/YYYY'
            hora_limite: datetime.time o str 'HH:MM'
            prioridad: int (1=urgente, 5=normal)
            usuario: str username
        """
        # Convertir fecha si viene como string
        if isinstance(fecha_limite, str):
            try:
                fecha_limite = datetime.strptime(fecha_limite, "%d/%m/%Y").date()
            except ValueError:
                print(f"⚠️  Formato de fecha inválido: {fecha_limite}. Usa DD/MM/YYYY")
                fecha_limite = None

        # Convertir hora si viene como string
        if isinstance(hora_limite, str):
            try:
                hora_limite = datetime.strptime(hora_limite, "%H:%M").time()
            except ValueError:
                print(f"⚠️  Formato de hora inválido: {hora_limite}. Usa HH:MM")
                hora_limite = None

        # Asignar prioridad por defecto según tipo si no se especifica
        if prioridad is None:
            prioridad_defaults = {
                "urgente": 1,
                "importante": 2,
                "tarea": 3,
                "nota": 5,
                "idea": 5
            }
            prioridad = prioridad_defaults.get(mem_type, 5)

        # Usuario actual
        if usuario is None and SESSION.user:
            usuario = SESSION.user.username

        BITACORA.registrar("recordatorios", "guardar", f"Guardando: {content[:50]}...",
                           usuario or "system")

        nota = MemoryNote(
            content=content,
            type=mem_type,
            fecha_limite=fecha_limite,
            hora_limite=hora_limite,
            prioridad=prioridad,
            estado="pendiente",
            creado_por=usuario or "system"
        )

        self.db.add(nota)
        self.db.commit()
        self.db.refresh(nota)
        return nota

    def recall(self, mem_type=None, estado="pendiente", incluir_completadas=False):
        """
        Recupera recordatorios con filtros
        Args:
            mem_type: Tipo de recordatorio
            estado: pendiente, completada, cancelada, o None para todos
            incluir_completadas: Si es True, ignora el filtro de estado
        """
        query = self.db.query(MemoryNote)
        if mem_type:
            query = query.filter_by(type=mem_type)
        if not incluir_completadas and estado:
            query = query.filter_by(estado=estado)
        return query.order_by(MemoryNote.timestamp.desc()).all()

    def recall_vencidos(self):
        """Retorna recordatorios con fecha límite pasada y estado pendiente"""
        hoy = date.today()
        return self.db.query(MemoryNote).filter(
            and_(
                MemoryNote.fecha_limite < hoy,
                MemoryNote.estado == "pendiente"
            )
        ).order_by(MemoryNote.fecha_limite.asc()).all()

    def recall_proximos(self, dias=3):
        """Retorna recordatorios que vencen en los próximos N días"""
        hoy = date.today()
        fecha_limite = date.today()
        # Calcular fecha_limite sumando días
        from datetime import timedelta
        fecha_limite = hoy + timedelta(days=dias)

        return self.db.query(MemoryNote).filter(
            and_(
                MemoryNote.fecha_limite.between(hoy, fecha_limite),
                MemoryNote.estado == "pendiente"
            )
        ).order_by(MemoryNote.fecha_limite.asc(), MemoryNote.prioridad.asc()).all()

    def recall_por_fecha(self, fecha):
        """Retorna recordatorios de una fecha específica"""
        if isinstance(fecha, str):
            fecha = datetime.strptime(fecha, "%d/%m/%Y").date()

        return self.db.query(MemoryNote).filter(
            and_(
                MemoryNote.fecha_limite == fecha,
                MemoryNote.estado == "pendiente"
            )
        ).order_by(MemoryNote.hora_limite.asc(), MemoryNote.prioridad.asc()).all()

    def recall_por_semana(self, fecha_inicio):
        """Retorna recordatorios de una semana completa"""
        from datetime import timedelta

        if isinstance(fecha_inicio, str):
            fecha_inicio = datetime.strptime(fecha_inicio, "%d/%m/%Y").date()

        fecha_fin = fecha_inicio + timedelta(days=6)

        return self.db.query(MemoryNote).filter(
            and_(
                MemoryNote.fecha_limite.between(fecha_inicio, fecha_fin),
                MemoryNote.estado == "pendiente"
            )
        ).order_by(
            MemoryNote.fecha_limite.asc(),
            MemoryNote.hora_limite.asc(),
            MemoryNote.prioridad.asc()
        ).all()

    def recall_por_prioridad(self, prioridad_min=1, prioridad_max=5):
        """Retorna recordatorios en un rango de prioridad"""
        return self.db.query(MemoryNote).filter(
            and_(
                MemoryNote.prioridad.between(prioridad_min, prioridad_max),
                MemoryNote.estado == "pendiente"
            )
        ).order_by(MemoryNote.prioridad.asc(), MemoryNote.fecha_limite.asc()).all()

    def completar(self, note_id):
        """Marca un recordatorio como completado"""
        try:
            nota = self.db.query(MemoryNote).filter(MemoryNote.id == note_id).one()
            nota.estado = "completada"
            self.db.commit()

            BITACORA.registrar("recordatorios", "completar",
                               f"Completado: {nota.content[:50]}...",
                               SESSION.user.username if SESSION.user else "system")
            return True
        except NoResultFound:
            return False

    def cancelar(self, note_id):
        """Marca un recordatorio como cancelado"""
        try:
            nota = self.db.query(MemoryNote).filter(MemoryNote.id == note_id).one()
            nota.estado = "cancelada"
            self.db.commit()

            BITACORA.registrar("recordatorios", "cancelar",
                               f"Cancelado: {nota.content[:50]}...",
                               SESSION.user.username if SESSION.user else "system")
            return True
        except NoResultFound:
            return False

    def delete(self, contenido: str, mem_type=None) -> bool:
        if mem_type is None:
            print("[LOBO] Debes especificar la etiqueta para usar búsqueda parcial.")
            return False

        if len(contenido.split()) >= 0:
            print("[LOBO] Escribe al menos 1 palabra para eliminar con coincidencia parcial.")
            return False

        pattern = f"%{contenido.strip()}%"
        query = self.db.query(MemoryNote).filter(
            and_(
                MemoryNote.type == mem_type,
                func.lower(MemoryNote.content).like(pattern.lower())
            )
        )
        resultado = query.first()

        if resultado:
            self.db.delete(resultado)
            BITACORA.registrar("recordatorios", "eliminar",
                             f"Eliminado: {resultado.content[:50]}...",
                             SESSION.user.username if SESSION.user else "system")
            self.db.commit()
            return True
        return False

    def buscar_por_contenido(self, texto: str, mem_type: str = None, estado: str = "pendiente"):
        """Busca recordatorios por contenido con filtros opcionales"""
        patron = f"%{texto}%"
        query = self.db.query(MemoryNote).filter(
            func.lower(MemoryNote.content).like(func.lower(patron))
        )

        if mem_type:
            query = query.filter(MemoryNote.type == mem_type)

        if estado:
            query = query.filter(MemoryNote.estado == estado)

        return query.all()

    def eliminar_por_id(self, note_id: int) -> bool:
        """Elimina permanentemente un recordatorio por ID"""
        try:
            nota = self.db.query(MemoryNote).filter(MemoryNote.id == note_id).one()
            contenido = nota.content
            self.db.delete(nota)
            self.db.commit()

            BITACORA.registrar("recordatorios", "eliminar",
                               f"Eliminado por ID {note_id}: {contenido[:50]}...",
                               SESSION.user.username if SESSION.user else "system")
            return True
        except NoResultFound:
            return False

    def obtener_por_id(self, note_id: int):
        """Obtiene un recordatorio por ID"""
        try:
            return self.db.query(MemoryNote).filter(MemoryNote.id == note_id).one()
        except NoResultFound:
            return None