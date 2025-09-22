# modules/agenda/agenda_logics.py
from datetime import datetime, date, time, timedelta
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker
from core.db.schema import Base, Evento, RecurrenciaEnum
from core.lobo_google.lobo_sheets import get_sheet
from gspread.utils import rowcol_to_a1
import logging

# DB
engine = create_engine("sqlite:///lobo_agenda.db", echo=False)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# Layout del Sheet
DIAS = ["Hora", "Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
SPANISH_WEEKDAY = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}

logger = logging.getLogger(__name__)

# Utils internos
def _ensure_date(obj):
    if isinstance(obj, date):
        return obj
    return date.fromisoformat(obj)

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
    ev.modificado_en = datetime.utcnow().isoformat()
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

#    Pinta el evento en el Sheet:
#    - texto solo en primera celda (nombre + descripcion)
#    - celdas abarcadas con color uniforme
#    - bordes exteriores SOLID

    sheet = get_sheet()
    start_row = _time_to_row(sheet, evento.hora_inicio)
    end_row = _time_to_row(sheet, evento.hora_fin)
    col = _date_to_col(evento.fecha_inicio)

    # a1 ranges
    first_a1 = rowcol_to_a1(start_row, col)
    full_range = f"{rowcol_to_a1(start_row, col)}:{rowcol_to_a1(end_row, col)}"

    # 1) limpiar contenido en rango (por si edit)
    sheet.batch_clear([full_range])

    # 2) escribir texto solo en primera celda
    texto = evento.nombre
    if evento.descripcion:
        texto = f"{evento.nombre}\n{evento.descripcion}"
    sheet.update(first_a1, [[texto]])

    # 3) aplicar color y bordes mediante batch_update requests
    sheet_id = sheet._properties["sheetId"]
    r, g, b = color_rgb

    requests = [
        # background
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
                        # Mantener texto tal cual; el texto lo dejamos en la primera celda
                    }
                },
                "fields": "userEnteredFormat.backgroundColor"
            }
        },
        # bordes exteriores sólidos
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

    # 4) dar formato de texto a la primera celda (wrap + bold)
    sheet.format(first_a1, {"wrapStrategy": "WRAP", "textFormat": {"bold": True}})

    logger.info(f"Pintado evento en Sheets: {evento.nombre} ({first_a1} -> {full_range})")
    return True

def borrar_evento_sheets(evento):
    # Limpia contenido, quita color y quita bordes del rango del evento.
    sheet = get_sheet()
    start_row = _time_to_row(sheet, evento.hora_inicio)
    end_row = _time_to_row(sheet, evento.hora_fin)
    col = _date_to_col(evento.fecha_inicio)
    full_range = f"{rowcol_to_a1(start_row, col)}:{rowcol_to_a1(end_row, col)}"
    sheet_id = sheet._properties["sheetId"]

    # 1) borrar contenido
    sheet.batch_clear([full_range])

    # 2) quitar formatos (reset userEnteredFormat) y quitar bordes
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
    logger.info(f"Borrado evento en Sheets: {evento.nombre} ({full_range})")
    return True

def actualizar_evento_sheets(old_evento, new_evento):
    # Simple: borra el rango anterior y pinta el nuevo.
    try:
        borrar_evento_sheets(old_evento)
    except Exception as e:
        logger.warning("No se pudo borrar evento antiguo en sheets: %s", e)
    return pintar_evento_sheets(new_evento)

def clear_sheets():
    # Limpia por completo el Sheet y repinta desde la DB (útil en reinicio).
    sheet = get_sheet()

    # Obtén número de filas y columnas
    filas = len(sheet.col_values(1))  # cuántas horas hay
    columnas = len(sheet.row_values(1))  # cuántos días hay

    # Limpia desde fila 2 y columna 2 (evita horas y encabezados)
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
    # Lee todos los eventos escritos en el Google Sheets y los inserta en la DB.
    # Formato esperado:
    # - Columna A = horas ("08:00", "09:00", ...)
    # - Fila 1 = días ("Lunes", "Martes", ...)
    # - Celdas = "Nombre" o "Nombre\\nDescripcion"

    sheet = get_sheet()

    horas = sheet.col_values(1)[1:]   # todas las horas menos encabezado "Hora"
    dias = sheet.row_values(1)[1:]   # todos los días menos encabezado "Hora"

    session = Session()
    nuevos = 0

    for col_idx, dia in enumerate(dias, start=2):  # columna 2 = Domingo, etc
        for row_idx, hora in enumerate(horas, start=2):  # fila 2 = primera hora
            valor = sheet.cell(row_idx, col_idx).value
            if not valor:
                continue

            partes = valor.split("\n", 1)
            nombre = partes[0]
            descripcion = partes[1] if len(partes) > 1 else ""

            try:
                hora_inicio = datetime.strptime(horas[row_idx - 2], "%H:%M").time()
                if row_idx - 1 < len(horas):
                    hora_fin = datetime.strptime(horas[row_idx - 1], "%H:%M").time()
                else:
                    hora_fin = (datetime.combine(date.today(), hora_inicio) + timedelta(hours=1)).time()

                # Calcular fecha exacta a partir del nombre del día
                hoy = date.today()
                weekday_target = list(SPANISH_WEEKDAY.values()).index(dia)
                # Buscar el próximo día que coincida
                fecha = hoy + timedelta((weekday_target - hoy.weekday()) % 7)

                # Verificar si ya existe en DB (mismo nombre, fecha y hora)
                existente = session.query(Evento).filter_by(
                    nombre=nombre,
                    fecha_inicio=fecha,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin
                ).first()

                if existente:
                    continue

                ev = Evento(
                    nombre=nombre,
                    descripcion=descripcion,
                    fecha_inicio=fecha,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    recurrencia=RecurrenciaEnum.unico,
                    etiquetas=[],
                    creado_en=datetime.utcnow(),
                    modificado_en=datetime.utcnow()
                )
                session.add(ev)
                nuevos += 1

            except Exception as e:
                logger.exception(f"No se pudo importar celda {row_idx},{col_idx}: {e}")

    session.commit()
    session.close()
    return nuevos
