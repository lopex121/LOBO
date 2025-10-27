# modules/agenda/agenda_logics_recurrentes.py
"""
Sistema de eventos recurrentes - Opción C (Maestro + Instancias)

Este archivo contiene SOLO las funciones nuevas para recurrentes.
Debe usarse JUNTO con agenda_logics.py existente.
"""

from datetime import datetime, date, time, timedelta
from core.db.schema import Evento, RecurrenciaEnum
from core.db.sessions import SessionLocal as Session
import uuid
import logging

logger = logging.getLogger(__name__)


def crear_evento_recurrente(nombre, descripcion, fecha_inicio, hora_inicio, hora_fin,
                            recurrencia: RecurrenciaEnum, etiquetas=None, tipo_evento="personal",
                            alarma_minutos=5, semanas_futuras=12):
    """
    Crea un evento recurrente con sistema Maestro + Instancias

    Args:
        semanas_futuras: int - Número de semanas hacia adelante para generar instancias

    Returns:
        dict: {'maestro': Evento, 'instancias': [Evento, ...]}
    """
    etiquetas = etiquetas or []

    # Convertir tipos
    if isinstance(fecha_inicio, str):
        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    if isinstance(hora_inicio, str):
        hora_inicio = datetime.strptime(hora_inicio, "%H:%M").time()
    if isinstance(hora_fin, str):
        hora_fin = datetime.strptime(hora_fin, "%H:%M").time()

    session = Session()

    try:
        # 1. Crear evento MAESTRO
        master_id = str(uuid.uuid4())

        maestro = Evento(
            id=master_id,
            nombre=nombre,
            descripcion=descripcion,
            fecha_inicio=fecha_inicio,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            recurrencia=recurrencia,
            etiquetas=etiquetas,
            tipo_evento=tipo_evento,
            alarma_minutos=alarma_minutos,
            alarma_activa=True,
            es_maestro=True,
            master_id=None,
            modificado_manualmente=False,
            creado_en=datetime.utcnow(),
            modificado_en=datetime.utcnow()
        )

        session.add(maestro)

        # 2. Generar instancias según recurrencia
        instancias = []
        fecha_actual = fecha_inicio
        dias_totales = semanas_futuras * 7

        while (fecha_actual - fecha_inicio).days <= dias_totales:
            # Crear instancia
            instancia_id = str(uuid.uuid4())

            instancia = Evento(
                id=instancia_id,
                nombre=nombre,
                descripcion=descripcion,
                fecha_inicio=fecha_actual,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                recurrencia=recurrencia,
                etiquetas=etiquetas.copy(),
                tipo_evento=tipo_evento,
                alarma_minutos=alarma_minutos,
                alarma_activa=True,
                es_maestro=False,
                master_id=master_id,
                modificado_manualmente=False,
                creado_en=datetime.utcnow(),
                modificado_en=datetime.utcnow()
            )

            session.add(instancia)
            instancias.append(instancia)

            # Calcular siguiente fecha según recurrencia
            if recurrencia == RecurrenciaEnum.diario:
                fecha_actual += timedelta(days=1)
            elif recurrencia == RecurrenciaEnum.semanal:
                fecha_actual += timedelta(weeks=1)
            elif recurrencia == RecurrenciaEnum.mensual:
                # Siguiente mes, mismo día
                if fecha_actual.month == 12:
                    fecha_actual = fecha_actual.replace(year=fecha_actual.year + 1, month=1)
                else:
                    try:
                        fecha_actual = fecha_actual.replace(month=fecha_actual.month + 1)
                    except ValueError:
                        # Si el día no existe en el mes (ej: 31 feb), usar último día del mes
                        import calendar
                        ultimo_dia = calendar.monthrange(fecha_actual.year, fecha_actual.month + 1)[1]
                        fecha_actual = fecha_actual.replace(month=fecha_actual.month + 1, day=ultimo_dia)
            else:
                # Único: solo una instancia
                break

        session.commit()

        # Refresh para obtener IDs generados
        session.refresh(maestro)
        for inst in instancias:
            session.refresh(inst)

        logger.info(f"Serie creada: {nombre} con {len(instancias)} instancias")

        return {
            'maestro': maestro,
            'instancias': instancias
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Error al crear evento recurrente: {e}")
        raise
    finally:
        session.close()


def editar_instancia(instancia_id, **kwargs):
    """
    Edita UNA instancia específica y la marca como modificada manualmente

    Args:
        instancia_id: str - ID de la instancia a editar
        **kwargs: campos a actualizar
    """
    session = Session()

    try:
        instancia = session.query(Evento).filter_by(id=instancia_id).first()

        if not instancia:
            raise ValueError("Instancia no encontrada")

        if instancia.es_maestro:
            raise ValueError("No puedes editar el maestro directamente. Usa editar_serie()")

        # Actualizar campos
        for key, value in kwargs.items():
            if hasattr(instancia, key):
                setattr(instancia, key, value)

        # Marcar como modificada manualmente
        instancia.modificado_manualmente = True
        instancia.modificado_en = datetime.utcnow()

        session.commit()
        session.refresh(instancia)

        logger.info(f"Instancia {instancia_id} editada manualmente")

        return instancia

    except Exception as e:
        session.rollback()
        logger.error(f"Error al editar instancia: {e}")
        raise
    finally:
        session.close()


def editar_serie(master_id, **kwargs):
    """
    Edita el evento maestro y TODAS las instancias no modificadas manualmente

    Args:
        master_id: str - ID del evento maestro
        **kwargs: campos a actualizar
    """
    session = Session()

    try:
        # Obtener maestro
        maestro = session.query(Evento).filter_by(id=master_id, es_maestro=True).first()

        if not maestro:
            raise ValueError("Evento maestro no encontrado")

        # Actualizar maestro
        for key, value in kwargs.items():
            if hasattr(maestro, key):
                setattr(maestro, key, value)

        maestro.modificado_en = datetime.utcnow()

        # Obtener instancias NO modificadas manualmente
        instancias = session.query(Evento).filter_by(
            master_id=master_id,
            es_maestro=False,
            modificado_manualmente=False
        ).all()

        # Actualizar cada instancia
        for instancia in instancias:
            for key, value in kwargs.items():
                if hasattr(instancia, key):
                    setattr(instancia, key, value)
            instancia.modificado_en = datetime.utcnow()

        session.commit()

        logger.info(f"Serie {master_id} editada: maestro + {len(instancias)} instancias")

        return {
            'maestro': maestro,
            'instancias_actualizadas': len(instancias)
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Error al editar serie: {e}")
        raise
    finally:
        session.close()


def eliminar_instancia(instancia_id):
    """
    Elimina UNA instancia específica de una serie

    Returns:
        bool: True si se eliminó correctamente
    """
    session = Session()

    try:
        instancia = session.query(Evento).filter_by(id=instancia_id).first()

        if not instancia:
            return False

        if instancia.es_maestro:
            raise ValueError("No puedes eliminar el maestro directamente. Usa eliminar_serie()")

        session.delete(instancia)
        session.commit()

        logger.info(f"Instancia {instancia_id} eliminada")

        return True

    except Exception as e:
        session.rollback()
        logger.error(f"Error al eliminar instancia: {e}")
        raise
    finally:
        session.close()


def eliminar_serie(master_id, incluir_pasadas=False):
    """
    Elimina el maestro y TODAS sus instancias (o solo futuras)

    Args:
        master_id: str - ID del evento maestro
        incluir_pasadas: bool - Si True, elimina también instancias pasadas

    Returns:
        int: Número de instancias eliminadas
    """
    session = Session()

    try:
        # Obtener maestro
        maestro = session.query(Evento).filter_by(id=master_id, es_maestro=True).first()

        if not maestro:
            raise ValueError("Evento maestro no encontrado")

        # Obtener instancias
        query = session.query(Evento).filter_by(master_id=master_id, es_maestro=False)

        if not incluir_pasadas:
            hoy = date.today()
            query = query.filter(Evento.fecha_inicio >= hoy)

        instancias = query.all()

        # Eliminar instancias
        for instancia in instancias:
            session.delete(instancia)

        # Eliminar maestro
        session.delete(maestro)

        session.commit()

        logger.info(f"Serie {master_id} eliminada: maestro + {len(instancias)} instancias")

        return len(instancias)

    except Exception as e:
        session.rollback()
        logger.error(f"Error al eliminar serie: {e}")
        raise
    finally:
        session.close()


def obtener_info_serie(evento_id):
    """
    Obtiene información sobre si un evento es parte de una serie

    Returns:
        dict o None: {
            'es_serie': bool,
            'es_maestro': bool,
            'master_id': str,
            'instancias_totales': int,
            'instancias_futuras': int,
            'modificado_manualmente': bool
        }
    """
    session = Session()

    try:
        evento = session.query(Evento).filter_by(id=evento_id).first()

        if not evento:
            session.close()
            return None

        # Forzar carga de atributos antes de cerrar sesión
        es_maestro = evento.es_maestro
        master_id = evento.master_id
        modificado_manualmente = evento.modificado_manualmente
        recurrencia_value = evento.recurrencia.value if evento.recurrencia else 'unico'

        if es_maestro:
            # Es un maestro
            instancias_totales = session.query(Evento).filter_by(
                master_id=evento.id,
                es_maestro=False
            ).count()

            hoy = date.today()
            instancias_futuras = session.query(Evento).filter(
                Evento.master_id == evento.id,
                Evento.es_maestro == False,
                Evento.fecha_inicio >= hoy
            ).count()

            session.close()

            return {
                'es_serie': True,
                'es_maestro': True,
                'master_id': evento.id,
                'instancias_totales': instancias_totales,
                'instancias_futuras': instancias_futuras,
                'modificado_manualmente': False,
                'recurrencia': recurrencia_value
            }

        elif master_id:
            # Es una instancia
            instancias_totales = session.query(Evento).filter_by(
                master_id=master_id,
                es_maestro=False
            ).count()

            hoy = date.today()
            instancias_futuras = session.query(Evento).filter(
                Evento.master_id == master_id,
                Evento.es_maestro == False,
                Evento.fecha_inicio >= hoy
            ).count()

            # Obtener info del maestro
            maestro = session.query(Evento).filter_by(id=master_id).first()
            maestro_recurrencia = maestro.recurrencia.value if maestro and maestro.recurrencia else 'unico'

            session.close()

            return {
                'es_serie': True,
                'es_maestro': False,
                'master_id': master_id,
                'instancias_totales': instancias_totales,
                'instancias_futuras': instancias_futuras,
                'modificado_manualmente': modificado_manualmente,
                'recurrencia': maestro_recurrencia
            }

        else:
            # Es un evento único
            session.close()

            return {
                'es_serie': False,
                'es_maestro': False,
                'master_id': None,
                'instancias_totales': 0,
                'instancias_futuras': 0,
                'modificado_manualmente': False,
                'recurrencia': 'unico'
            }

    except Exception as e:
        logger.error(f"Error en obtener_info_serie: {e}")
        session.close()
        return None