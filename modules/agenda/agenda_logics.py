# modules/agenda/agenda_logics.py
from datetime import datetime, date, time, timedelta
from sqlalchemy import or_
from core.db.schema import Evento, RecurrenciaEnum
from core.db.sessions import SessionLocal as Session
from core.lobo_google.lobo_sheets import get_sheet
from gspread.utils import rowcol_to_a1
import logging
from sqlalchemy import and_

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
                    recurrencia: RecurrenciaEnum = RecurrenciaEnum.unico, etiquetas=None):
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

def listar_eventos_por_fecha(fecha: date):
    fecha = _ensure_date(fecha)
    session = Session()
    results = session.query(Evento).filter_by(fecha_inicio=fecha).all()
    session.close()
    return results

# Sheets: pintar, borrar, actualizar, sync
def pintar_evento_sheets(evento, color_rgb=(0.9, 0.9, 0.9)):
    sheet = get_sheet()
    start_row = _time_to_row(sheet, evento.hora_inicio)
    end_row = _time_to_row(sheet, evento.hora_fin)
    col = _date_to_col(evento.fecha_inicio)

    first_a1 = rowcol_to_a1(start_row, col)
    full_range = f"{rowcol_to_a1(start_row, col)}:{rowcol_to_a1(end_row, col)}"

    # limpiar contenido en rango
    sheet.batch_clear([full_range])

    # escribir texto solo en primera celda
    texto = evento.nombre
    if evento.descripcion:
        texto = f"{evento.nombre}\n{evento.descripcion}"
    sheet.update(first_a1, [[texto]])

    # aplicar color y bordes
    sheet_id = sheet._properties["sheetId"]
    r, g, b = color_rgb
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
                "cell": {"userEnteredFormat": {"backgroundColor": {"red": r, "green": g, "blue": b}}},
                "fields": "userEnteredFormat.backgroundColor"
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
    sheet.format(first_a1, {"wrapStrategy": "WRAP", "textFormat": {"bold": True}})

    logger.info(f"Pintado evento en Sheets: {evento.nombre} ({first_a1} -> {full_range})")
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
