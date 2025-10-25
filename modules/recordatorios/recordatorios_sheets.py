# modules/recordatorios/recordatorios_sheets.py
"""
Integración de recordatorios con Google Sheets
Pinta recordatorios debajo del horario semanal y en columna lateral
"""

from core.lobo_google.lobo_sheets import get_sheet
from core.memory import Memory
from datetime import datetime, timedelta, date
from gspread.utils import rowcol_to_a1
import logging

logger = logging.getLogger(__name__)

# Configuración
FILA_INICIO_RECORDATORIOS = 32  # Después del horario (fila 31)
COLUMNA_TODOS_PENDIENTES = 9  # Columna I (a la derecha del horario)

# Colores según prioridad (RGB 0-1)
COLORES_PRIORIDAD = {
    1: (1.0, 0.8, 0.8),  # Rojo claro (urgente)
    2: (1.0, 0.9, 0.6),  # Amarillo claro (importante)
    3: (1.0, 1.0, 0.8),  # Amarillo muy claro (normal-alto)
    4: (0.9, 1.0, 0.9),  # Verde muy claro (normal)
    5: (0.85, 0.95, 1.0)  # Azul muy claro (casual)
}


def pintar_recordatorios_semana(fecha_inicio_semana=None):
    """
    Pinta recordatorios de la semana debajo del horario

    Args:
        fecha_inicio_semana: datetime.date del lunes de la semana
    """
    if fecha_inicio_semana is None:
        # Obtener el lunes de esta semana
        hoy = date.today()
        fecha_inicio_semana = hoy - timedelta(days=hoy.weekday())

    sheet = get_sheet()
    memoria = Memory()

    # Obtener recordatorios de la semana
    recordatorios = memoria.recall_por_semana(fecha_inicio_semana)

    if not recordatorios:
        logger.info("No hay recordatorios para esta semana")
        return

    # Limpiar área de recordatorios primero
    limpiar_area_recordatorios(sheet)

    # Agrupar por día de la semana
    recordatorios_por_dia = {i: [] for i in range(7)}  # 0=Lunes, 6=Domingo

    for rec in recordatorios:
        if rec.fecha_limite:
            dia_semana = rec.fecha_limite.weekday()
            recordatorios_por_dia[dia_semana].append(rec)

    # Pintar encabezado
    fila = FILA_INICIO_RECORDATORIOS
    sheet.update(f"A{fila}", [["RECORDATORIOS PENDIENTES DE LA SEMANA"]])
    sheet.format(f"A{fila}:H{fila}", {
        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1

    # Encabezados de días
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    sheet.update(f"B{fila}:H{fila}", [dias])
    sheet.format(f"B{fila}:H{fila}", {
        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
        "textFormat": {"bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1
    fila_inicio_datos = fila

    # Calcular máximo de recordatorios por día
    max_recs = max(len(recs) for recs in recordatorios_por_dia.values())
    max_recs = min(max_recs, 20)  # Límite de 20

    # Pintar recordatorios por día
    for dia_idx in range(7):
        recs = recordatorios_por_dia[dia_idx]
        col = dia_idx + 2  # Columna B=2, C=3, ..., H=8
        fila_actual = fila_inicio_datos

        for rec in recs[:20]:  # Máximo 20 por día
            # Formato del recordatorio
            emoji = {
                "urgente": "⚠️",
                "importante": "📌",
                "tarea": "✅",
                "nota": "📝",
                "idea": "💡"
            }.get(rec.type, "•")

            # Construir texto
            texto = f"[P:{rec.prioridad}] {emoji}\n"
            texto += f"{rec.content[:40]}"  # Limitar a 40 chars
            if len(rec.content) > 40:
                texto += "..."

            if rec.hora_limite:
                texto += f"\n⏰ {rec.hora_limite.strftime('%H:%M')}"

            # Escribir en celda
            celda = rowcol_to_a1(fila_actual, col)
            sheet.update(celda, [[texto]])

            # Aplicar color según prioridad
            color = COLORES_PRIORIDAD.get(rec.prioridad, (1.0, 1.0, 1.0))
            sheet.format(celda, {
                "backgroundColor": {"red": color[0], "green": color[1], "blue": color[2]},
                "textFormat": {"fontSize": 9},
                "wrapStrategy": "WRAP",
                "verticalAlignment": "TOP"
            })

            fila_actual += 1

    logger.info(f"Recordatorios de la semana pintados (filas {fila_inicio_datos}-{fila_actual})")


def pintar_todos_pendientes():
    """
    Pinta TODOS los recordatorios pendientes en la columna lateral derecha
    """
    sheet = get_sheet()
    memoria = Memory()

    # Obtener TODOS los pendientes ordenados por fecha y prioridad
    todos = memoria.recall(estado="pendiente")

    # Filtrar solo los que tienen fecha
    con_fecha = [r for r in todos if r.fecha_limite]
    con_fecha.sort(key=lambda x: (x.fecha_limite, x.hora_limite or datetime.min.time(), x.prioridad))

    # Limpiar columna primero
    limpiar_columna_todos_pendientes(sheet)

    if not con_fecha:
        logger.info("No hay recordatorios pendientes con fecha")
        return

    # Encabezado
    col = COLUMNA_TODOS_PENDIENTES
    fila = 1

    sheet.update(rowcol_to_a1(fila, col), [["📋 TODOS LOS PENDIENTES"]])
    sheet.format(rowcol_to_a1(fila, col), {
        "backgroundColor": {"red": 0.2, "green": 0.3, "blue": 0.5},
        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1
    hoy = date.today()

    # Pintar cada recordatorio
    for rec in con_fecha[:50]:  # Máximo 50 para no saturar
        emoji = {
            "urgente": "⚠️",
            "importante": "📌",
            "tarea": "✅",
            "nota": "📝",
            "idea": "💡"
        }.get(rec.type, "•")

        # Calcular días restantes
        dias_restantes = (rec.fecha_limite - hoy).days

        if dias_restantes < 0:
            fecha_texto = f"🔴 Vencido"
        elif dias_restantes == 0:
            fecha_texto = "¡HOY!"
        elif dias_restantes == 1:
            fecha_texto = "Mañana"
        else:
            fecha_texto = f"En {dias_restantes}d"

        # Texto completo
        texto = f"[P:{rec.prioridad}] {emoji}\n"
        texto += f"{rec.content[:30]}\n"
        texto += f"📅 {fecha_texto}"

        if rec.hora_limite:
            texto += f"\n⏰ {rec.hora_limite.strftime('%H:%M')}"

        # Escribir
        celda = rowcol_to_a1(fila, col)
        sheet.update(celda, [[texto]])

        # Color
        color = COLORES_PRIORIDAD.get(rec.prioridad, (1.0, 1.0, 1.0))

        # Si está vencido, sobrescribir con rojo intenso
        if dias_restantes < 0:
            color = (1.0, 0.6, 0.6)

        sheet.format(celda, {
            "backgroundColor": {"red": color[0], "green": color[1], "blue": color[2]},
            "textFormat": {"fontSize": 8},
            "wrapStrategy": "WRAP",
            "verticalAlignment": "TOP"
        })

        fila += 1

    logger.info(f"Todos los pendientes pintados en columna {col}")


def limpiar_area_recordatorios(sheet):
    """Limpia el área de recordatorios debajo del horario"""
    # Limpiar desde fila 32 hasta 60 (sobrado)
    rango = f"A{FILA_INICIO_RECORDATORIOS}:H60"
    sheet.batch_clear([rango])

    # Restablecer formato
    sheet_id = sheet._properties["sheetId"]
    requests = [{
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": FILA_INICIO_RECORDATORIOS - 1,
                "endRowIndex": 60,
                "startColumnIndex": 0,
                "endColumnIndex": 8
            },
            "cell": {"userEnteredFormat": {}},
            "fields": "userEnteredFormat"
        }
    }]
    sheet.spreadsheet.batch_update({"requests": requests})


def limpiar_columna_todos_pendientes(sheet):
    """Limpia la columna de todos los pendientes"""
    col = COLUMNA_TODOS_PENDIENTES
    rango = f"{rowcol_to_a1(1, col)}:{rowcol_to_a1(60, col)}"
    sheet.batch_clear([rango])

    # Restablecer formato
    sheet_id = sheet._properties["sheetId"]
    requests = [{
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 60,
                "startColumnIndex": col - 1,
                "endColumnIndex": col
            },
            "cell": {"userEnteredFormat": {}},
            "fields": "userEnteredFormat"
        }
    }]
    sheet.spreadsheet.batch_update({"requests": requests})


def actualizar_recordatorios_sheets():
    """
    Función principal: actualiza ambas secciones de recordatorios en Sheets
    """
    try:
        logger.info("Actualizando recordatorios en Sheets...")
        pintar_recordatorios_semana()
        pintar_todos_pendientes()
        logger.info("✅ Recordatorios actualizados en Sheets")
        return True
    except Exception as e:
        logger.error(f"Error al actualizar recordatorios en Sheets: {e}")
        return False