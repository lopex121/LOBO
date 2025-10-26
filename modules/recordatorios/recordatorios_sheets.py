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
COLUMNA_RECORDATORIOS_FECHA = 9  # Columna I (recordatorios con fecha/hora)
COLUMNA_PENDIENTES_GENERALES = 10  # Columna J (recordatorios sin fecha)

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
    Pinta recordatorios pendientes en dos columnas:
    - Columna I: Recordatorios CON fecha/hora (ordenados por fecha)
    - Columna J: Pendientes SIN fecha (ordenados por ID)
    """
    sheet = get_sheet()
    memoria = Memory()

    # Obtener TODOS los pendientes
    todos = memoria.recall(estado="pendiente")

    # Separar en dos grupos
    con_fecha = [r for r in todos if r.fecha_limite]
    sin_fecha = [r for r in todos if not r.fecha_limite]

    # Ordenar con_fecha por fecha, hora y prioridad
    con_fecha.sort(key=lambda x: (x.fecha_limite, x.hora_limite or datetime.min.time(), x.prioridad))

    # Ordenar sin_fecha por ID (menor a mayor)
    sin_fecha.sort(key=lambda x: x.id)

    # Limpiar ambas columnas primero
    limpiar_columnas_pendientes(sheet)

    # ===== COLUMNA I: RECORDATORIOS CON FECHA =====
    _pintar_columna_con_fecha(sheet, con_fecha)

    # ===== COLUMNA J: PENDIENTES GENERALES (SIN FECHA) =====
    _pintar_columna_sin_fecha(sheet, sin_fecha)

    logger.info(f"Recordatorios pintados: {len(con_fecha)} con fecha, {len(sin_fecha)} sin fecha")


def _pintar_columna_con_fecha(sheet, recordatorios):
    """Pinta la columna de recordatorios CON fecha"""
    col = COLUMNA_RECORDATORIOS_FECHA
    fila = 1
    hoy = date.today()

    # Encabezado
    sheet.update(rowcol_to_a1(fila, col), [["📅 RECORDATORIOS POR HACER"]])
    sheet.format(rowcol_to_a1(fila, col), {
        "backgroundColor": {"red": 0.2, "green": 0.3, "blue": 0.5},
        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1

    if not recordatorios:
        sheet.update(rowcol_to_a1(fila, col), [["(Sin recordatorios)"]])
        sheet.format(rowcol_to_a1(fila, col), {
            "textFormat": {"italic": True, "fontSize": 9},
            "horizontalAlignment": "CENTER"
        })
        return

    # Pintar cada recordatorio
    for rec in recordatorios[:50]:  # Máximo 50
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


def _pintar_columna_sin_fecha(sheet, recordatorios):
    """Pinta la columna de pendientes SIN fecha (ordenados por ID)"""
    col = COLUMNA_PENDIENTES_GENERALES
    fila = 1

    # Encabezado
    sheet.update(rowcol_to_a1(fila, col), [["📋 PENDIENTES GENERALES"]])
    sheet.format(rowcol_to_a1(fila, col), {
        "backgroundColor": {"red": 0.3, "green": 0.3, "blue": 0.3},
        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1

    if not recordatorios:
        sheet.update(rowcol_to_a1(fila, col), [["(Sin pendientes)"]])
        sheet.format(rowcol_to_a1(fila, col), {
            "textFormat": {"italic": True, "fontSize": 9},
            "horizontalAlignment": "CENTER"
        })
        return

    # Pintar cada recordatorio
    for rec in recordatorios[:50]:  # Máximo 50
        emoji = {
            "urgente": "⚠️",
            "importante": "📌",
            "tarea": "✅",
            "nota": "📝",
            "idea": "💡"
        }.get(rec.type, "•")

        # Texto completo (sin fecha porque no tiene)
        texto = f"[ID:{rec.id}] [P:{rec.prioridad}]\n"
        texto += f"{emoji} {rec.content[:35]}"

        if len(rec.content) > 35:
            texto += "..."

        # Escribir
        celda = rowcol_to_a1(fila, col)
        sheet.update(celda, [[texto]])

        # Color según prioridad
        color = COLORES_PRIORIDAD.get(rec.prioridad, (1.0, 1.0, 1.0))

        sheet.format(celda, {
            "backgroundColor": {"red": color[0], "green": color[1], "blue": color[2]},
            "textFormat": {"fontSize": 8},
            "wrapStrategy": "WRAP",
            "verticalAlignment": "TOP"
        })

        fila += 1


def limpiar_columnas_pendientes(sheet):
    """Limpia ambas columnas de pendientes"""
    col_fecha = COLUMNA_RECORDATORIOS_FECHA
    col_general = COLUMNA_PENDIENTES_GENERALES

    # Limpiar columna de recordatorios con fecha
    rango1 = f"{rowcol_to_a1(1, col_fecha)}:{rowcol_to_a1(60, col_fecha)}"
    sheet.batch_clear([rango1])

    # Limpiar columna de pendientes generales
    rango2 = f"{rowcol_to_a1(1, col_general)}:{rowcol_to_a1(60, col_general)}"
    sheet.batch_clear([rango2])

    # Restablecer formato de ambas columnas
    sheet_id = sheet._properties["sheetId"]
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 60,
                    "startColumnIndex": col_fecha - 1,
                    "endColumnIndex": col_fecha
                },
                "cell": {"userEnteredFormat": {}},
                "fields": "userEnteredFormat"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 60,
                    "startColumnIndex": col_general - 1,
                    "endColumnIndex": col_general
                },
                "cell": {"userEnteredFormat": {}},
                "fields": "userEnteredFormat"
            }
        }
    ]
    sheet.spreadsheet.batch_update({"requests": requests})


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
    """DEPRECATED - Usar limpiar_columnas_pendientes en su lugar"""
    limpiar_columnas_pendientes(sheet)


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