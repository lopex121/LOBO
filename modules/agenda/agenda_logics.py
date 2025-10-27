# modules/agenda/agenda_logics.py
from datetime import datetime, date, time, timedelta
from sqlalchemy import or_
from core.db.schema import Evento, RecurrenciaEnum
from core.db.sessions import SessionLocal as Session
from core.lobo_google.lobo_sheets import get_sheet
from gspread.utils import rowcol_to_a1
import logging
from sqlalchemy import and_

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

    Args:
        color_fondo_rgb: tuple (r, g, b) valores 0-1

    Returns:
        tuple: (r, g, b) para el color de texto
    """
    r, g, b = color_fondo_rgb
    # Fórmula de luminosidad
    luminosidad = (0.299 * r + 0.587 * g + 0.114 * b)

    if luminosidad > 0.7:  # Fondo claro
        return (0, 0, 0)  # Texto negro
    else:  # Fondo oscuro
        return (1, 1, 1)  # Texto blanco

# Layout del Sheet
DIAS = ["Hora", "Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
SPANISH_WEEKDAY = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}

logger = logging.getLogger(__name__)

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
    # Recibe datetime.time o 'HH:MM' y devuelve la fila en la hoja (1-indexed)
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
    # Devuelve la columna numérica (1-indexed) de acuerdo al DIAS
    weekday = fecha.weekday()  # 0 = Lunes
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
    Crea un evento ÚNICO en la base de datos (actualizado con nuevos campos)

    Args:
        nombre: Nombre del evento
        descripcion: Descripción opcional
        fecha_inicio: date o str YYYY-MM-DD
        hora_inicio: time o str HH:MM
        hora_fin: time o str HH:MM
        recurrencia: RecurrenciaEnum (default: unico)
        etiquetas: list[str] (default: [])
        tipo_evento: str - clase, trabajo, personal, deporte, estudio, reunion (default: personal)
        alarma_minutos: int - Minutos antes para alarma (default: 5)
        alarma_activa: bool - Si tiene alarma activa (default: True)

    Returns:
        Evento: objeto evento creado
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
        # NUEVOS CAMPOS
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
    # aceptar strings para fecha/hora si vienen así
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

    Args:
        id_parcial: str - Primeros caracteres del ID (ej: "5776c444")

    Returns:
        Evento o None: El evento encontrado o None si no existe o hay ambigüedad
    """
    if len(id_parcial) < 6:
        return None

    session = Session()

    try:
        # Buscar eventos cuyo ID empiece con el fragmento
        eventos = session.query(Evento).filter(
            Evento.id.like(f"{id_parcial}%")
        ).all()

        if len(eventos) == 0:
            return None
        elif len(eventos) == 1:
            # FORZAR CARGA DE TODOS LOS ATRIBUTOS antes de cerrar sesión
            ev = eventos[0]
            # Acceder a todos los atributos para cargarlos
            _ = ev.id, ev.nombre, ev.descripcion, ev.fecha_inicio
            _ = ev.hora_inicio, ev.hora_fin, ev.recurrencia, ev.etiquetas
            _ = ev.es_maestro, ev.master_id, ev.tipo_evento
            session.expunge(ev)  # Desconectar del session pero mantener datos
            return ev
        else:
            # Múltiples coincidencias - retornar None para indicar ambigüedad
            print(f"⚠️  ID ambiguo '{id_parcial}'. Coincidencias:")
            for ev in eventos:
                print(f"   • {ev.id} - {ev.nombre} ({ev.fecha_inicio})")
            print("   Usa más caracteres del ID para especificar.")
            return None
    finally:
        session.close()


# TAMBIÉN AGREGA ESTA FUNCIÓN (wrapper mejorado)
def get_evento_by_id_flexible(evento_id: str):
    """
    Obtiene evento por ID completo o parcial

    Args:
        evento_id: str - ID completo o parcial (mínimo 6 caracteres)

    Returns:
        Evento o None
    """
    session = Session()

    try:
        # Primero intentar con ID completo
        evento = session.query(Evento).filter_by(id=evento_id).first()

        if evento:
            # FORZAR CARGA de atributos
            _ = evento.id, evento.nombre, evento.descripcion
            _ = evento.fecha_inicio, evento.hora_inicio, evento.hora_fin
            _ = evento.recurrencia, evento.etiquetas, evento.es_maestro
            _ = evento.master_id, evento.tipo_evento
            session.expunge(evento)
            return evento

        # Si no se encuentra, intentar con ID parcial
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

# Sheets: pintar, borrar, actualizar, sync
def pintar_evento_sheets(evento, color_rgb=None):
    """
    Pinta un evento en Google Sheets con color según tipo

    Args:
        evento: Objeto Evento
        color_rgb: tuple (r, g, b) opcional. Si None, usa color según tipo_evento
    """
    sheet = get_sheet()
    start_row = _time_to_row(sheet, evento.hora_inicio)
    end_row = _time_to_row(sheet, evento.hora_fin)
    col = _date_to_col(evento.fecha_inicio)

    first_a1 = rowcol_to_a1(start_row, col)
    full_range = f"{rowcol_to_a1(start_row, col)}:{rowcol_to_a1(end_row, col)}"

    # Limpiar contenido en rango
    sheet.batch_clear([full_range])

    # Escribir texto solo en primera celda
    texto = evento.nombre
    if evento.descripcion:
        texto = f"{evento.nombre}\n{evento.descripcion}"
    sheet.update(first_a1, [[texto]])

    # ===== DETERMINAR COLOR =====
    if color_rgb is None:
        # Usar color según tipo de evento
        tipo = getattr(evento, 'tipo_evento', 'personal')
        color_rgb = COLORES_TIPO_EVENTO.get(tipo, COLORES_TIPO_EVENTO['default'])

    # Calcular color de texto
    color_texto = calcular_color_texto(color_rgb)

    # Aplicar color de fondo y texto
    sheet_id = sheet._properties["sheetId"]
    r, g, b = color_rgb
    tr, tg, tb = color_texto

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
                "top": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
                "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
                "left": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
                "right": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}},
            }
        }
    ]
    sheet.spreadsheet.batch_update({"requests": requests})
    sheet.format(first_a1, {"wrapStrategy": "WRAP"})

    logger.info(f"Pintado evento en Sheets: {evento.nombre} ({first_a1} -> {full_range}) - Color: {evento.tipo_evento}")
    return True

def borrar_evento_sheets(evento):
    sheet = get_sheet()
    start_row = _time_to_row(sheet, evento.hora_inicio)
    end_row = _time_to_row(sheet, evento.hora_fin)
    col = _date_to_col(evento.fecha_inicio)
    full_range = f"{rowcol_to_a1(start_row, col)}:{rowcol_to_a1(end_row, col)}"
    sheet_id = sheet._properties["sheetId"]

    sheet.batch_clear([full_range])
    requests = [
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": start_row-1, "endRowIndex": end_row,
                          "startColumnIndex": col-1, "endColumnIndex": col},
                "cell": {"userEnteredFormat": {}},
                "fields": "userEnteredFormat"
            }
        },
        {
            "updateBorders": {
                "range": {"sheetId": sheet_id, "startRowIndex": start_row-1, "endRowIndex": end_row,
                          "startColumnIndex": col-1, "endColumnIndex": col},
                "top": {"style": "NONE"},
                "bottom": {"style": "NONE"},
                "left": {"style": "NONE"},
                "right": {"style": "NONE"},
            }
        }
    ]
    sheet.spreadsheet.batch_update({"requests": requests})
    logger.info(f"Borrado evento en Sheets: {evento.nombre} ({full_range})")
    return True

def actualizar_evento_sheets(old_evento, new_evento):
    try:
        borrar_evento_sheets(old_evento)
    except Exception as e:
        logger.warning("No se pudo borrar evento antiguo en sheets: %s", e)
    return pintar_evento_sheets(new_evento)

def clear_sheets():
    sheet = get_sheet()
    filas = len(sheet.col_values(1))
    columnas = len(sheet.row_values(1))
    rango = f"B2:{chr(64+columnas)}{filas}"
    sheet.batch_clear([rango])

    session = Session()
    eventos = session.query(Evento).order_by(Evento.fecha_inicio, Evento.hora_inicio).all()
    session.close()
    for ev in eventos:
        try:
            pintar_evento_sheets(ev)
        except Exception as e:
            logger.exception("No se pudo pintar evento %s: %s", ev.id, e)
    return True

def importar_eventos_desde_sheets():
    sheet = get_sheet()
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
                hoy = datetime.today().date()
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
