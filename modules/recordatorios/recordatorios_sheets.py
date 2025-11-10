# modules/recordatorios/recordatorios_sheets.py
"""
Integración de recordatorios con Google Sheets
Pinta recordatorios debajo del horario semanal y en columna lateral
OPTIMIZADO con Batch Manager para reducir API calls
"""

from core.lobo_google.lobo_sheets import get_sheet
from core.memory import Memory
from core.db.sessions import SessionLocal
from core.db.schema import MemoryNote
from datetime import datetime, timedelta, date, time
from gspread.utils import rowcol_to_a1
from core.lobo_google.rate_limiter import RATE_LIMITER
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


def actualizar_recordatorios_todas_las_hojas():
    """
    Actualiza recordatorios en todas las hojas semanales existentes
    OPTIMIZADO: Usa batch operations para reducir API calls

    ANTES: 2*N requests (N = hojas)
    AHORA: N requests (1 por hoja)
    """
    from modules.agenda.sheets_manager import SHEETS_MANAGER
    from modules.agenda.sheets_batch_manager import SheetsBatchManager

    try:
        memoria = Memory()
        todos = memoria.recall(estado="pendiente")

        # Separar recordatorios
        con_fecha = [r for r in todos if r.fecha_limite]
        sin_fecha = [r for r in todos if not r.fecha_limite]

        # Ordenar
        con_fecha.sort(key=lambda x: (x.fecha_limite, x.hora_limite or datetime.min.time(), x.prioridad))
        sin_fecha.sort(key=lambda x: x.id)

        # Obtener hojas
        spreadsheet = SHEETS_MANAGER.spreadsheet
        hojas = spreadsheet.worksheets()
        hojas_validas = []

        for hoja in hojas:
            # Saltar template y hojas especiales
            if "Copia" in hoja.title or hoja.title in ["Sheet1", "Hoja 1", "26-1"]:
                continue
            hojas_validas.append(hoja.title)

        if not hojas_validas:
            logger.warning("No se encontraron hojas válidas para actualizar")
            return 0

        # ===== USAR BATCH MANAGER =====
        batch_manager = SheetsBatchManager(
            spreadsheet.client,
            spreadsheet.id
        )

        # Preparar TODAS las operaciones batch
        updates = []

        for hoja_nombre in hojas_validas:
            # Columna I: Con fecha
            valores_i = _preparar_valores_columna_fecha(con_fecha)
            updates.append({
                'worksheet': hoja_nombre,
                'range': 'I1:I60',
                'values': valores_i
            })

            # Columna J: Sin fecha
            valores_j = _preparar_valores_columna_sin_fecha(sin_fecha)
            updates.append({
                'worksheet': hoja_nombre,
                'range': 'J1:J60',
                'values': valores_j
            })

        # Ejecutar UNA SOLA operación batch para todas las hojas
        logger.info(f"🔄 Sincronizando {len(con_fecha) + len(sin_fecha)} recordatorios a {len(hojas_validas)} hojas...")

        # ===== APLICAR RATE LIMITING =====
        RATE_LIMITER.wait_if_needed()

        if batch_manager.batch_update_cells(updates):
            logger.info(f"✅ Recordatorios sincronizados exitosamente")
            batch_manager.print_stats()
            RATE_LIMITER.print_stats()  # Mostrar estadísticas
            return len(hojas_validas)
        else:
            logger.error("❌ Error en sincronización batch")
            return 0

    except Exception as e:
        logger.error(f"Error al actualizar recordatorios: {e}", exc_info=True)
        return 0


def _preparar_valores_columna_fecha(recordatorios):
    """
    Prepara valores para columna I (con fecha) en formato batch

    Returns:
        List[List[str]]: Lista de filas con valores
    """
    hoy = date.today()
    valores = []

    # Fila 1: Encabezado
    valores.append(["📅 RECORDATORIOS POR HACER"])

    if not recordatorios:
        valores.append(["(Sin recordatorios)"])
        # Rellenar hasta fila 60
        while len(valores) < 60:
            valores.append([""])
        return valores

    # Filas 2+: Recordatorios (máximo 50)
    for rec in recordatorios[:50]:
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

        # Construir texto
        texto = f"[P:{rec.prioridad}] {emoji}\n"
        texto += f"{rec.content[:30]}\n"
        texto += f"📅 {fecha_texto}"

        if rec.hora_limite:
            texto += f"\n⏰ {rec.hora_limite.strftime('%H:%M')}"

        valores.append([texto])

    # Rellenar hasta fila 60
    while len(valores) < 60:
        valores.append([""])

    return valores


def _preparar_valores_columna_sin_fecha(recordatorios):
    """
    Prepara valores para columna J (sin fecha) en formato batch

    Returns:
        List[List[str]]: Lista de filas con valores
    """
    valores = []

    # Fila 1: Encabezado
    valores.append(["📋 PENDIENTES GENERALES"])

    if not recordatorios:
        valores.append(["(Sin pendientes)"])
        while len(valores) < 60:
            valores.append([""])
        return valores

    # Filas 2+: Recordatorios (máximo 50)
    for rec in recordatorios[:50]:
        emoji = {
            "urgente": "⚠️",
            "importante": "📌",
            "tarea": "✅",
            "nota": "📝",
            "idea": "💡"
        }.get(rec.type, "•")

        texto = f"[ID:{rec.id}] [P:{rec.prioridad}]\n"
        texto += f"{emoji} {rec.content[:35]}"

        if len(rec.content) > 35:
            texto += "..."

        valores.append([texto])

    # Rellenar hasta fila 60
    while len(valores) < 60:
        valores.append([""])

    return valores


# ===== FUNCIONES ANTIGUAS MANTENIDAS PARA COMPATIBILIDAD =====

def pintar_todos_pendientes(sheet=None):
    """
    DEPRECATED: Usa actualizar_recordatorios_todas_las_hojas() en su lugar
    Mantenida por compatibilidad con código antiguo
    """
    logger.warning("pintar_todos_pendientes() está deprecated, usa actualizar_recordatorios_todas_las_hojas()")

    from modules.agenda.sheets_manager import SHEETS_MANAGER

    if sheet is None:
        sheet = SHEETS_MANAGER.obtener_hoja_por_fecha(date.today())

    memoria = Memory()
    todos = memoria.recall(estado="pendiente")
    con_fecha = [r for r in todos if r.fecha_limite]
    sin_fecha = [r for r in todos if not r.fecha_limite]

    con_fecha.sort(key=lambda x: (x.fecha_limite, x.hora_limite or datetime.min.time(), x.prioridad))
    sin_fecha.sort(key=lambda x: x.id)

    limpiar_columnas_pendientes(sheet)
    _pintar_columna_con_fecha(sheet, con_fecha)
    _pintar_columna_sin_fecha(sheet, sin_fecha)

    logger.info(f"Recordatorios pintados: {len(con_fecha)} con fecha, {len(sin_fecha)} sin fecha")


def pintar_recordatorios_semana(fecha_inicio_semana=None):
    """
    Pinta recordatorios de la semana debajo del horario
    ACTUALIZADO: Pinta en la hoja correcta de esa semana
    """
    from modules.agenda.sheets_manager import SHEETS_MANAGER

    if fecha_inicio_semana is None:
        hoy = date.today()
        fecha_inicio_semana = hoy - timedelta(days=hoy.weekday())

    try:
        sheet = SHEETS_MANAGER.obtener_hoja_por_fecha(fecha_inicio_semana)
    except Exception as e:
        logger.error(f"Error al obtener hoja para recordatorios: {e}")
        return

    memoria = Memory()
    recordatorios = memoria.recall_por_semana(fecha_inicio_semana)

    if not recordatorios:
        logger.info("No hay recordatorios para esta semana")
        return

    limpiar_area_recordatorios(sheet)

    recordatorios_por_dia = {i: [] for i in range(7)}

    for rec in recordatorios:
        if rec.fecha_limite:
            dia_semana = rec.fecha_limite.weekday()
            recordatorios_por_dia[dia_semana].append(rec)

    fila = FILA_INICIO_RECORDATORIOS
    sheet.update(f"A{fila}", [["RECORDATORIOS PENDIENTES DE LA SEMANA"]])
    sheet.format(f"A{fila}:H{fila}", {
        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    sheet.update(f"B{fila}:H{fila}", [dias])
    sheet.format(f"B{fila}:H{fila}", {
        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
        "textFormat": {"bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1
    fila_inicio_datos = fila
    max_recs = max(len(recs) for recs in recordatorios_por_dia.values())
    max_recs = min(max_recs, 20)

    for dia_idx in range(7):
        recs = recordatorios_por_dia[dia_idx]
        col = dia_idx + 2
        fila_actual = fila_inicio_datos

        for rec in recs[:20]:
            emoji = {
                "urgente": "⚠️",
                "importante": "📌",
                "tarea": "✅",
                "nota": "📝",
                "idea": "💡"
            }.get(rec.type, "•")

            texto = f"[P:{rec.prioridad}] {emoji}\n"
            texto += f"{rec.content[:40]}"
            if len(rec.content) > 40:
                texto += "..."

            if rec.hora_limite:
                texto += f"\n⏰ {rec.hora_limite.strftime('%H:%M')}"

            celda = rowcol_to_a1(fila_actual, col)
            sheet.update(celda, [[texto]])

            color = COLORES_PRIORIDAD.get(rec.prioridad, (1.0, 1.0, 1.0))
            sheet.format(celda, {
                "backgroundColor": {"red": color[0], "green": color[1], "blue": color[2]},
                "textFormat": {"fontSize": 9},
                "wrapStrategy": "WRAP",
                "verticalAlignment": "TOP"
            })

            fila_actual += 1

    logger.info(f"Recordatorios de la semana pintados en hoja '{sheet.title}'")


def _pintar_columna_con_fecha(sheet, recordatorios):
    """DEPRECATED - Usa versión batch"""
    col = COLUMNA_RECORDATORIOS_FECHA
    fila = 1
    hoy = date.today()

    sheet.update(rowcol_to_a1(fila, col), [["📅 RECORDATORIOS POR HACER"]])
    sheet.format(rowcol_to_a1(fila, col), {
        "backgroundColor": {"red": 0.2, "green": 0.3, "blue": 0.5},
        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1

    if not recordatorios:
        sheet.update(rowcol_to_a1(fila, col), [["(Sin recordatorios)"]])
        return

    for rec in recordatorios[:50]:
        emoji = {"urgente": "⚠️", "importante": "📌", "tarea": "✅", "nota": "📝", "idea": "💡"}.get(rec.type, "•")
        dias_restantes = (rec.fecha_limite - hoy).days

        if dias_restantes < 0:
            fecha_texto = f"🔴 Vencido"
        elif dias_restantes == 0:
            fecha_texto = "¡HOY!"
        elif dias_restantes == 1:
            fecha_texto = "Mañana"
        else:
            fecha_texto = f"En {dias_restantes}d"

        texto = f"[P:{rec.prioridad}] {emoji}\n{rec.content[:30]}\n📅 {fecha_texto}"
        if rec.hora_limite:
            texto += f"\n⏰ {rec.hora_limite.strftime('%H:%M')}"

        celda = rowcol_to_a1(fila, col)
        sheet.update(celda, [[texto]])

        color = COLORES_PRIORIDAD.get(rec.prioridad, (1.0, 1.0, 1.0))
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
    """DEPRECATED - Usa versión batch"""
    col = COLUMNA_PENDIENTES_GENERALES
    fila = 1

    sheet.update(rowcol_to_a1(fila, col), [["📋 PENDIENTES GENERALES"]])
    sheet.format(rowcol_to_a1(fila, col), {
        "backgroundColor": {"red": 0.3, "green": 0.3, "blue": 0.3},
        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1

    if not recordatorios:
        sheet.update(rowcol_to_a1(fila, col), [["(Sin pendientes)"]])
        return

    for rec in recordatorios[:50]:
        emoji = {"urgente": "⚠️", "importante": "📌", "tarea": "✅", "nota": "📝", "idea": "💡"}.get(rec.type, "•")
        texto = f"[ID:{rec.id}] [P:{rec.prioridad}]\n{emoji} {rec.content[:35]}"
        if len(rec.content) > 35:
            texto += "..."

        celda = rowcol_to_a1(fila, col)
        sheet.update(celda, [[texto]])

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

    rango1 = f"{rowcol_to_a1(1, col_fecha)}:{rowcol_to_a1(60, col_fecha)}"
    sheet.batch_clear([rango1])

    rango2 = f"{rowcol_to_a1(1, col_general)}:{rowcol_to_a1(60, col_general)}"
    sheet.batch_clear([rango2])

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
    rango = f"A{FILA_INICIO_RECORDATORIOS}:H60"
    sheet.batch_clear([rango])

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
    """DEPRECATED - Usar limpiar_columnas_pendientes"""
    limpiar_columnas_pendientes(sheet)


def actualizar_recordatorios_sheets():
    """
    Función principal: actualiza recordatorios en todas las hojas
    OPTIMIZADO con batch operations
    """
    return actualizar_recordatorios_todas_las_hojas()
