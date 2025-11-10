# modules/agenda/agenda_logics.py
from datetime import datetime, date, time, timedelta
from sqlalchemy import or_, and_
from core.db.schema import Evento, RecurrenciaEnum
from core.db.sessions import SessionLocal as Session
from core.lobo_google.lobo_sheets import get_sheet
from gspread.utils import rowcol_to_a1
import logging

from modules.agenda.sheets_manager import get_sheets_manager

logger = logging.getLogger(__name__)

# Paleta de colores por tipo de evento (RGB 0-1)
COLORES_TIPO_EVENTO = {
    "clase": (0.6, 0.8, 1.0),  # Azul claro
    "trabajo": (1.0, 0.9, 0.6),  # Amarillo
    "personal": (0.8, 1.0, 0.8),  # Verde claro
    "deporte": (1.0, 0.8, 0.6),  # Naranja claro
    "estudio": (0.9, 0.8, 1.0),  # Morado claro
    "reunion": (1.0, 0.7, 0.7),  # Rosa claro
    "default": (0.9, 0.9, 0.9)  # Gris claro
}


def calcular_color_texto(color_fondo_rgb):
    """
    Calcula si el texto debe ser negro o blanco según el fondo
    """
    r, g, b = color_fondo_rgb
    luminosidad = (0.299 * r + 0.587 * g + 0.114 * b)

    if luminosidad > 0.7:
        return (0, 0, 0)  # Texto negro
    else:
        return (1, 1, 1)  # Texto blanco


# Layout del Sheet
DIAS = ["Hora", "Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
SPANISH_WEEKDAY = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}


# Utils internos
def _ensure_date(obj):
    if isinstance(obj, date):
        return obj
    return datetime.strptime(obj, "%Y-%m-%d").date()


def _ensure_time(obj):
    if isinstance(obj, time):
        return obj
    return datetime.strptime(obj, "%H:%M").time()


def _time_to_row(sheet, hora):
    if isinstance(hora, str):
        hora_str = hora
    else:
        hora_str = hora.strftime("%H:%M")
    col1 = sheet.col_values(1)
    try:
        fila = col1.index(hora_str) + 1
    except ValueError:
        raise ValueError(f"Hora {hora_str} no encontrada en la primera columna del Sheet.")
    return fila


def _date_to_col(fecha: date):
    weekday = fecha.weekday()
    dia = SPANISH_WEEKDAY[weekday]
    try:
        col = DIAS.index(dia) + 1
    except ValueError:
        raise ValueError(f"El día {dia} no existe en la configuración DIAS.")
    return col


# DB: CRUD
def crear_evento_db(nombre: str, descripcion: str, fecha_inicio, hora_inicio, hora_fin,
                    recurrencia: RecurrenciaEnum = RecurrenciaEnum.unico, etiquetas=None,
                    tipo_evento="personal", alarma_minutos=5, alarma_activa=True):
    """
    Crea un evento ÚNICO en la base de datos
    """
    etiquetas = etiquetas or []
    fecha_inicio = _ensure_date(fecha_inicio)
    hora_inicio = _ensure_time(hora_inicio)
    hora_fin = _ensure_time(hora_fin)

    session = Session()
    evento = Evento(
        nombre=nombre,
        descripcion=descripcion,
        fecha_inicio=fecha_inicio,
        hora_inicio=hora_inicio,
        hora_fin=hora_fin,
        recurrencia=recurrencia,
        etiquetas=etiquetas,
        creado_en=datetime.utcnow(),
        modificado_en=datetime.utcnow(),
        tipo_evento=tipo_evento,
        alarma_minutos=alarma_minutos,
        alarma_activa=alarma_activa,
        es_maestro=False,
        master_id=None,
        modificado_manualmente=False,
        color_custom=None
    )
    session.add(evento)
    session.commit()
    session.refresh(evento)
    session.close()
    return evento


def get_evento_by_id(evento_id):
    session = Session()
    ev = session.query(Evento).filter_by(id=evento_id).first()
    session.close()
    return ev


def editar_evento_db(evento_id, **kwargs):
    session = Session()
    ev = session.query(Evento).filter_by(id=evento_id).first()
    if not ev:
        session.close()
        raise ValueError("Evento no encontrado")
    if "fecha_inicio" in kwargs:
        kwargs["fecha_inicio"] = _ensure_date(kwargs["fecha_inicio"])
    if "hora_inicio" in kwargs:
        kwargs["hora_inicio"] = _ensure_time(kwargs["hora_inicio"])
    if "hora_fin" in kwargs:
        kwargs["hora_fin"] = _ensure_time(kwargs["hora_fin"])
    for k, v in kwargs.items():
        setattr(ev, k, v)
    ev.modificado_en = datetime.utcnow()
    session.commit()
    session.refresh(ev)
    session.close()
    return ev


def eliminar_evento_db(evento_id):
    session = Session()
    ev = session.query(Evento).filter_by(id=evento_id).first()
    if not ev:
        session.close()
        return False
    session.delete(ev)
    session.commit()
    session.close()
    return True


def buscar_eventos_db(query_str):
    session = Session()
    q = f"%{query_str}%"
    results = session.query(Evento).filter(
        or_(Evento.nombre.ilike(q), Evento.descripcion.ilike(q))
    ).all()
    session.close()
    return results


def buscar_evento_por_id_parcial(id_parcial: str):
    """
    Busca un evento por ID parcial (mínimo 6 caracteres)
    """
    if len(id_parcial) < 6:
        return None

    session = Session()

    try:
        eventos = session.query(Evento).filter(
            Evento.id.like(f"{id_parcial}%")
        ).all()

        if len(eventos) == 0:
            return None
        elif len(eventos) == 1:
            ev = eventos[0]
            _ = ev.id, ev.nombre, ev.descripcion, ev.fecha_inicio
            _ = ev.hora_inicio, ev.hora_fin, ev.recurrencia, ev.etiquetas
            _ = ev.es_maestro, ev.master_id, ev.tipo_evento
            session.expunge(ev)
            return ev
        else:
            print(f"⚠️  ID ambiguo '{id_parcial}'. Coincidencias:")
            for ev in eventos:
                print(f"   • {ev.id} - {ev.nombre} ({ev.fecha_inicio})")
            print("   Usa más caracteres del ID para especificar.")
            return None
    finally:
        session.close()


def get_evento_by_id_flexible(evento_id: str):
    """
    Obtiene evento por ID completo o parcial
    """
    session = Session()

    try:
        evento = session.query(Evento).filter_by(id=evento_id).first()

        if evento:
            _ = evento.id, evento.nombre, evento.descripcion
            _ = evento.fecha_inicio, evento.hora_inicio, evento.hora_fin
            _ = evento.recurrencia, evento.etiquetas, evento.es_maestro
            _ = evento.master_id, evento.tipo_evento
            session.expunge(evento)
            return evento

        if len(evento_id) >= 6:
            return buscar_evento_por_id_parcial(evento_id)

        return None
    finally:
        session.close()


def listar_eventos_por_fecha(fecha: date):
    fecha = _ensure_date(fecha)
    session = Session()
    results = session.query(Evento).filter_by(fecha_inicio=fecha).all()
    session.close()
    return results


# ===== SHEETS: OPTIMIZADO CON BATCH + RATE LIMITING =====

def pintar_evento_sheets(evento, color_rgb=None):
    """
    Pinta un evento en Google Sheets con color según tipo
    Soporta hojas múltiples + Rate limiting automático
    """
    try:
        # ✅ CORRECCIÓN: Agregar () para llamar la función
        sheet = get_sheets_manager().obtener_hoja_por_fecha(evento.fecha_inicio)
    except Exception as e:
        logger.error(f"Error al obtener hoja para {evento.fecha_inicio}: {e}")
        sheet = get_sheet()

    start_row = _time_to_row(sheet, evento.hora_inicio)
    end_row = _time_to_row(sheet, evento.hora_fin)
    col = _date_to_col(evento.fecha_inicio)

    first_a1 = rowcol_to_a1(start_row, col)
    full_range = f"{rowcol_to_a1(start_row, col)}:{rowcol_to_a1(end_row, col)}"

    # Determinar color
    if color_rgb is None:
        tipo = getattr(evento, 'tipo_evento', 'personal')
        color_rgb = COLORES_TIPO_EVENTO.get(tipo, COLORES_TIPO_EVENTO['default'])

    color_texto = calcular_color_texto(color_rgb)

    # Preparar texto
    texto = evento.nombre
    if evento.descripcion:
        texto = f"{evento.nombre}\n{evento.descripcion}"

    # Preparar requests
    sheet_id = sheet._properties["sheetId"]
    r, g, b = color_rgb
    tr, tg, tb = color_texto

    requests = [
        {
            "updateCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row - 1,
                    "endRowIndex": start_row,
                    "startColumnIndex": col - 1,
                    "endColumnIndex": col
                },
                "rows": [{
                    "values": [{
                        "userEnteredValue": {"stringValue": texto},
                        "userEnteredFormat": {
                            "backgroundColor": {"red": r, "green": g, "blue": b},
                            "textFormat": {
                                "foregroundColor": {"red": tr, "green": tg, "blue": tb},
                                "bold": True
                            },
                            "wrapStrategy": "WRAP"
                        }
                    }]
                }],
                "fields": "userEnteredValue,userEnteredFormat"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": col - 1,
                    "endColumnIndex": col
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": r, "green": g, "blue": b},
                        "textFormat": {
                            "foregroundColor": {"red": tr, "green": tg, "blue": tb},
                            "bold": True
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        } if end_row > start_row else {},
        {
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row - 1,
                    "endRowIndex": end_row,
                    "startColumnIndex": col - 1,
                    "endColumnIndex": col
                },
                "top": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
                "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
                "left": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
                "right": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
            }
        }
    ]

    requests = [r for r in requests if r]

    # ===== APLICAR RATE LIMITING =====
    from core.lobo_google.rate_limiter import RATE_LIMITER
    RATE_LIMITER.wait_if_needed()

    sheet.spreadsheet.batch_update({"requests": requests})

    logger.info(f"Pintado evento: {evento.nombre} ({first_a1} -> {full_range}) - {evento.tipo_evento}")
    return True


def borrar_evento_sheets(evento):
    """Borra un evento de Google Sheets con rate limiting"""
    try:
        # ✅ CORRECCIÓN: Agregar ()
        sheet = get_sheets_manager().obtener_hoja_por_fecha(evento.fecha_inicio)
    except Exception as e:
        logger.error(f"Error al obtener hoja para borrar: {e}")
        sheet = get_sheet()

    start_row = _time_to_row(sheet, evento.hora_inicio)
    end_row = _time_to_row(sheet, evento.hora_fin)
    col = _date_to_col(evento.fecha_inicio)
    full_range = f"{rowcol_to_a1(start_row, col)}:{rowcol_to_a1(end_row, col)}"
    sheet_id = sheet._properties["sheetId"]

    # ===== RATE LIMITING =====
    from core.lobo_google.rate_limiter import RATE_LIMITER
    RATE_LIMITER.wait_if_needed()

    sheet.batch_clear([full_range])

    RATE_LIMITER.wait_if_needed()

    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row - 1,
                    "endRowIndex": end_row,
                    "startColumnIndex": col - 1,
                    "endColumnIndex": col
                },
                "cell": {"userEnteredFormat": {}},
                "fields": "userEnteredFormat"
            }
        },
        {
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row - 1,
                    "endRowIndex": end_row,
                    "startColumnIndex": col - 1,
                    "endColumnIndex": col
                },
                "top": {"style": "NONE"},
                "bottom": {"style": "NONE"},
                "left": {"style": "NONE"},
                "right": {"style": "NONE"},
            }
        }
    ]
    sheet.spreadsheet.batch_update({"requests": requests})
    logger.info(f"Borrado evento: {evento.nombre} ({full_range})")
    return True


def actualizar_evento_sheets(old_evento, new_evento):
    """Actualiza un evento en Sheets"""
    try:
        borrar_evento_sheets(old_evento)
    except Exception as e:
        logger.warning("No se pudo borrar evento antiguo en sheets: %s", e)
    return pintar_evento_sheets(new_evento)


def clear_sheets():
    """Limpia y sincroniza TODAS las hojas semanales con rate limiting"""
    session = Session()
    eventos = session.query(Evento).filter(
        Evento.es_maestro == False
    ).order_by(Evento.fecha_inicio, Evento.hora_inicio).all()
    session.close()

    # Agrupar eventos por semana
    eventos_por_semana = {}

    for ev in eventos:
        # ✅ CORRECCIÓN: Agregar ()
        lunes = get_sheets_manager().obtener_lunes_semana(ev.fecha_inicio)
        if lunes not in eventos_por_semana:
            eventos_por_semana[lunes] = []
        eventos_por_semana[lunes].append(ev)

    hojas_procesadas = 0
    eventos_pintados = 0

    for lunes, eventos_semana in eventos_por_semana.items():
        try:
            # ✅ CORRECCIÓN: Agregar ()
            sheet = get_sheets_manager().obtener_hoja_por_fecha(lunes)

            # ===== RATE LIMITING =====
            from core.lobo_google.rate_limiter import RATE_LIMITER
            RATE_LIMITER.wait_if_needed()

            rango = f"B2:H31"
            sheet.batch_clear([rango])

            logger.info(f"Limpiando hoja '{sheet.title}'")

            # Repintar eventos de esta semana
            for ev in eventos_semana:
                try:
                    pintar_evento_sheets(ev)
                    eventos_pintados += 1
                except Exception as e:
                    logger.exception(f"Error al pintar evento {ev.id}: {e}")

            hojas_procesadas += 1

        except Exception as e:
            logger.exception(f"Error al procesar semana {lunes}: {e}")

    logger.info(f"Clear sheets completado: {hojas_procesadas} hojas, {eventos_pintados} eventos")
    return True


def importar_eventos_desde_sheets():
    """Importa eventos desde la hoja actual"""
    hoy = date.today()
    # ✅ CORRECCIÓN: Agregar ()
    sheet = get_sheets_manager().obtener_hoja_por_fecha(hoy)
    data = sheet.get_all_values()

    if not data:
        return "[AGENDA] Hoja vacía."

    encabezados = data[0]
    horas = [row[0] for row in data]

    session = Session()
    creados = 0
    try:
        for fila_idx in range(1, len(data)):
            hora_str = horas[fila_idx]
            if not hora_str:
                continue
            try:
                hora_inicio = datetime.strptime(hora_str.strip(), "%H:%M").time()
            except ValueError:
                try:
                    hora_inicio = datetime.strptime(hora_str.strip().upper(), "%I:%M %p").time()
                except ValueError:
                    continue

            if fila_idx + 1 < len(horas):
                next_hora_str = horas[fila_idx + 1].strip()
                try:
                    hora_fin = datetime.strptime(next_hora_str, "%H:%M").time()
                except ValueError:
                    try:
                        hora_fin = datetime.strptime(next_hora_str.upper(), "%I:%M %p").time()
                    except ValueError:
                        hora_fin = (datetime.combine(datetime.today(), hora_inicio) + timedelta(hours=1)).time()
            else:
                hora_fin = (datetime.combine(datetime.today(), hora_inicio) + timedelta(hours=1)).time()

            for col_idx in range(1, len(encabezados)):
                dia = encabezados[col_idx]
                if not dia:
                    continue
                contenido = data[fila_idx][col_idx] if col_idx < len(data[fila_idx]) else ""
                if not contenido.strip():
                    continue
                partes = contenido.split("\n", 1)
                nombre = partes[0].strip()
                descripcion = partes[1].strip() if len(partes) > 1 else ""

                weekday_map = {
                    "Lunes": 0, "Martes": 1, "Miércoles": 2,
                    "Jueves": 3, "Viernes": 4, "Sábado": 5, "Domingo": 6
                }
                if dia not in weekday_map:
                    continue

                delta = (weekday_map[dia] - hoy.weekday()) % 7
                fecha = hoy + timedelta(days=delta)

                ev = Evento(
                    nombre=nombre,
                    descripcion=descripcion,
                    fecha_inicio=fecha,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    recurrencia=RecurrenciaEnum.unico,
                    etiquetas=[],
                    creado_en=datetime.utcnow(),
                    modificado_en=datetime.utcnow(),
                )
                session.add(ev)
                creados += 1
        session.commit()
    finally:
        session.close()
    return creados


def listar_eventos_por_rango(fecha_inicio: str, fecha_fin: str):
    with Session() as session:
        return session.query(Evento).filter(
            and_(
                Evento.fecha_inicio >= fecha_inicio,
                Evento.fecha_inicio <= fecha_fin
            )
        ).all()
