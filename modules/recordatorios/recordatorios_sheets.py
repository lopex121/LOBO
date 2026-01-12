# modules/recordatorios/recordatorios_sheets.py
"""
Integración de recordatorios con Google Sheets
OPTIMIZADO MÁXIMO: Reduce requests de ~7 por hoja a ~3 por hoja
"""

from core.lobo_google.lobo_sheets import get_sheet
from core.memory import Memory
from datetime import datetime, timedelta, date
from gspread.utils import rowcol_to_a1
import logging

logger = logging.getLogger(__name__)

# Configuración
FILA_INICIO_RECORDATORIOS = 32
COLUMNA_RECORDATORIOS_FECHA = 9
COLUMNA_PENDIENTES_GENERALES = 10

# Colores según prioridad
COLORES_PRIORIDAD = {
    1: (1.0, 0.8, 0.8),
    2: (1.0, 0.9, 0.6),
    3: (1.0, 1.0, 0.8),
    4: (0.9, 1.0, 0.9),
    5: (0.85, 0.95, 1.0)
}


def actualizar_recordatorios_todas_las_hojas():
    """
    Actualiza recordatorios en TODAS las hojas semanales
    OPTIMIZADO: ~3 requests por hoja (antes: ~7)
    """
    from modules.agenda.sheets_manager import get_sheets_manager
    from core.lobo_google.rate_limiter import RATE_LIMITER

    try:
        memoria = Memory()
        todos = memoria.recall(estado="pendiente")

        con_fecha = [r for r in todos if r.fecha_limite]
        sin_fecha = [r for r in todos if not r.fecha_limite]

        con_fecha.sort(key=lambda x: (x.fecha_limite, x.hora_limite or datetime.min.time(), x.prioridad))
        sin_fecha.sort(key=lambda x: x.id)

        logger.info(f"📝 Sincronizando {len(con_fecha) + len(sin_fecha)} recordatorios...")

        manager = get_sheets_manager()
        spreadsheet = manager.spreadsheet

        RATE_LIMITER.wait_if_needed()
        todas_las_hojas = spreadsheet.worksheets()

        # ===== ORDENAR HOJAS POR FECHA (FIX PROBLEMA #1) =====
        hojas_validas = []
        hojas_excluidas = ["Hoja 1", "Sheet1", "26-2"]

        for hoja in todas_las_hojas:
            if hoja.title in hojas_excluidas:
                continue

            if "-" in hoja.title:
                meses = [
                    "ene", "feb", "mar", "abr", "may", "jun",
                    "jul", "ago", "sep", "oct", "nov", "dic",
                    "jan", "feb", "mar", "apr", "may", "jun",
                    "jul", "aug", "sep", "oct", "nov", "dec"
                ]

                if any(mes in hoja.title.lower() for mes in meses):
                    hojas_validas.append(hoja.title)

        if not hojas_validas:
            logger.warning("⚠️  No se encontraron hojas válidas")
            return 0

        # ===== ORDENAR HOJAS CRONOLÓGICAMENTE =====
        hojas_con_fechas = []
        for nombre_hoja in hojas_validas:
            fecha_lunes = _calcular_lunes_desde_nombre_hoja(nombre_hoja)
            if fecha_lunes:
                hojas_con_fechas.append((fecha_lunes, nombre_hoja))

        # Ordenar por fecha (más antigua primero)
        hojas_con_fechas.sort(key=lambda x: x[0], reverse=True)
        hojas_validas_ordenadas = [h[1] for h in hojas_con_fechas]

        logger.info(f"✅ {len(hojas_validas_ordenadas)} hojas (más reciente primero)")
        logger.info(f"Primera hoja: {hojas_validas_ordenadas[0] if hojas_validas_ordenadas else 'N/A'}")

        # ===== ACTUALIZAR CADA HOJA (OPTIMIZADO) =====
        hojas_actualizadas = 0

        for nombre_hoja in hojas_validas_ordenadas:
            try:
                RATE_LIMITER.wait_if_needed()
                sheet = spreadsheet.worksheet(nombre_hoja)

                fecha_lunes = _calcular_lunes_desde_nombre_hoja(nombre_hoja)

                if fecha_lunes:
                    # ===== OPTIMIZACIÓN: All EN UNA SOLA LLAMADA =====
                    _actualizar_hoja_completa_optimizado(
                        sheet, fecha_lunes, con_fecha, sin_fecha
                    )

                    hojas_actualizadas += 1
                    logger.info(f"✅ '{nombre_hoja}' actualizada")

            except Exception as e:
                logger.error(f"❌ Error en '{nombre_hoja}': {e}")

        logger.info(f"🎉 Completado: {hojas_actualizadas}/{len(hojas_validas_ordenadas)} hojas")

        # ===== NUEVO: REORDENAR HOJAS FÍSICAMENTE =====
        try:
            hojas_movidas = reordenar_hojas_cronologicamente()
            if hojas_movidas > 0:
                logger.info(f"📂 {hojas_movidas} hojas reordenadas en Google Sheets")
        except Exception as e:
            logger.warning(f"⚠️  No se pudieron reordenar hojas: {e}")

        RATE_LIMITER.print_stats()

        return hojas_actualizadas

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 0


def _calcular_lunes_desde_nombre_hoja(nombre_hoja):
    """
    Parsea nombres de hoja a fecha
    MEJORADO: Maneja "29 dic.-04 ene." correctamente
    """
    try:
        # Limpiar el nombre
        nombre = nombre_hoja.replace(".", "").strip()

        # Detectar si cruza meses (tiene dos abreviaciones de mes)
        meses_map = {
            "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
            "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
            "jan": 1, "aug": 8,  "dec": 12
        }

        # Contar cuántos meses aparecen
        meses_encontrados = []
        nombre_lower = nombre.lower()
        for mes_str, mes_num in meses_map.items():
            if mes_str in nombre_lower:
                meses_encontrados.append((mes_str, mes_num))

        if not meses_encontrados:
            return None

        # Caso 1: "10-16 nov" (un solo mes)
        if len(meses_encontrados) == 1:
            partes = nombre.split()
            dia_inicio = int(partes[0].split('-')[0])
            mes = meses_encontrados[0][1]

        # Caso 2: "29 dic-04 ene" (dos meses, tomar el primero)
        else:
            # Buscar el primer número antes del primer mes
            import re
            match = re.search(r'(\d+)\s*(?:' + '|'.join(meses_map.keys()) + ')', nombre_lower)
            if match:
                dia_inicio = int(match.group(1))
                mes = meses_encontrados[0][1]  # Primer mes encontrado
            else:
                return None

        # Determinar año
        ayo = date.today().year
        mes_actual = date.today().month

        # Ajustar año para meses de cambio de año
        if mes in [1, 2] and mes_actual in [11, 12]:
            ayo += 1
        elif mes in [11, 12] and mes_actual in [1, 2]:
            ayo -= 1

        try:
            return date(ayo, mes, dia_inicio)
        except ValueError:
            return date(ayo, mes, 1)

    except Exception as e:
        logger.debug(f"No se pudo parsear '{nombre_hoja}': {e}")
        return None


def _actualizar_hoja_completa_optimizado(sheet, fecha_lunes, todos_con_fecha, todos_sin_fecha):
    """
    Actualiza UNA hoja completa en el MÍNIMO de requests posible

    OPTIMIZACIÓN:
    - 1 request: batch_clear (columnas I/J + área semanal)
    - 1 request: batch_update (columnas I/J + tabla semanal)
    - 1 request: batch_format (encabezados + colores)

    Total: 3 requests por hoja (antes: 7-10 requests)
    """
    from core.lobo_google.rate_limiter import RATE_LIMITER

    memoria = Memory()
    recordatorios_semana = memoria.recall_por_semana(fecha_lunes)

    # Agrupar recordatorios de la semana por día
    recordatorios_por_dia = {i: [] for i in range(7)}
    for rec in recordatorios_semana:
        if rec.fecha_limite:
            dia_semana = rec.fecha_limite.weekday()
            recordatorios_por_dia[dia_semana].append(rec)

    # ===== 1. PREPARAR TODOS LOS VALORES =====
    hoy = date.today()

    # Columnas I/J
    valores_i = _preparar_valores_columna_i(todos_con_fecha, hoy)
    valores_j = _preparar_valores_columna_j(todos_sin_fecha)

    # Tabla semanal
    valores_tabla = _preparar_valores_tabla_semanal(recordatorios_por_dia, fecha_lunes)

    # ===== 2. LIMPIAR All EN UN SOLO REQUEST =====
    RATE_LIMITER.wait_if_needed()
    sheet.batch_clear([
        "I1:I60",  # Columna recordatorios con fecha
        "J1:J60",  # Columna pendientes generales
        f"A{FILA_INICIO_RECORDATORIOS}:H55"  # Área tabla semanal
    ])

    # ===== 3. ESCRIBIR All EN UN SOLO REQUEST =====
    RATE_LIMITER.wait_if_needed()
    updates = [
        {'range': 'I1:I60', 'values': valores_i},
        {'range': 'J1:J60', 'values': valores_j}
    ]

    # Agregar valores de tabla semanal
    if valores_tabla:
        fila = FILA_INICIO_RECORDATORIOS
        for update_tabla in valores_tabla:
            updates.append(update_tabla)

    sheet.batch_update(updates)

    # ===== 4. APLICAR FORMATO EN UN SOLO REQUEST =====
    RATE_LIMITER.wait_if_needed()
    _aplicar_formato_batch(sheet)


def _preparar_valores_columna_i(recordatorios, hoy):
    """Prepara valores de columna I (con fecha)"""
    valores = [["📅 RECORDATORIOS POR HACER"]]

    if not recordatorios:
        valores.append(["(Sin recordatorios)"])
    else:
        for rec in recordatorios[:50]:
            emoji = {"urgente": "⚠️", "importante": "📌", "tarea": "✅", "nota": "📝", "idea": "💡"}.get(rec.type, "•")
            dias = (rec.fecha_limite - hoy).days

            if dias < 0:
                fecha_texto = "🔴 Vencido"
            elif dias == 0:
                fecha_texto = "¡HOY!"
            elif dias == 1:
                fecha_texto = "Mañana"
            else:
                fecha_texto = f"En {dias}d"

            texto = f"[P:{rec.prioridad}] {emoji}\n{rec.content[:30]}\n📅 {fecha_texto}"
            if rec.hora_limite:
                texto += f"\n⏰ {rec.hora_limite.strftime('%H:%M')}"

            valores.append([texto])

    while len(valores) < 60:
        valores.append([""])

    return valores


def _preparar_valores_columna_j(recordatorios):
    """Prepara valores de columna J (sin fecha)"""
    valores = [["📋 PENDIENTES GENERALES"]]

    if not recordatorios:
        valores.append(["(Sin pendientes)"])
    else:
        for rec in recordatorios[:50]:
            emoji = {"urgente": "⚠️", "importante": "📌", "tarea": "✅", "nota": "📝", "idea": "💡"}.get(rec.type, "•")
            texto = f"[ID:{rec.id}] [P:{rec.prioridad}]\n{emoji} {rec.content[:35]}"
            if len(rec.content) > 35:
                texto += "..."
            valores.append([texto])

    while len(valores) < 60:
        valores.append([""])

    return valores


def _preparar_valores_tabla_semanal(recordatorios_por_dia, fecha_lunes=None):
    """
    Prepara valores de tabla semanal con FECHA de la semana

    Args:
        recordatorios_por_dia: dict {dia_idx: [recordatorios]}
        fecha_lunes: date - Lunes de la semana (para mostrar fechas)
    """
    if not any(recordatorios_por_dia.values()):
        return []  # No hay recordatorios, no pintar tabla

    fila = FILA_INICIO_RECORDATORIOS
    updates = []

    # ===== FILA 1: TÍTULO CON RANGO DE FECHAS =====
    if fecha_lunes:
        domingo = fecha_lunes + timedelta(days=6)

        # Formatear rango de fechas según si cruza meses
        if fecha_lunes.month == domingo.month:
            # Mismo mes: "RECORDATORIOS DEL 10 AL 16 DE NOVIEMBRE"
            rango_fechas = f"RECORDATORIOS DEL {fecha_lunes.day} AL {domingo.day} DE {fecha_lunes.strftime('%B').upper()}"
        else:
            # Meses diferentes: "RECORDATORIOS DEL 29 DE DICIEMBRE AL 4 DE ENERO"
            rango_fechas = f"RECORDATORIOS DEL {fecha_lunes.day} DE {fecha_lunes.strftime('%B').upper()} AL {domingo.day} DE {domingo.strftime('%B').upper()}"

        titulo = rango_fechas
    else:
        titulo = "RECORDATORIOS PENDIENTES DE LA SEMANA"

    updates.append({
        'range': f'A{fila}:H{fila}',
        'values': [[titulo, "", "", "", "", "", "", ""]]
    })

    fila += 1

    # ===== FILA 2: DÍAS DE LA SEMANA CON FECHAS =====
    if fecha_lunes:
        dias_con_fechas = [""]  # Columna A vacía
        dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

        for i, dia_nombre in enumerate(dias_nombres):
            fecha_dia = fecha_lunes + timedelta(days=i)
            # Formato: "Lunes 10"
            dias_con_fechas.append(f"{dia_nombre} {fecha_dia.day}")

        updates.append({
            'range': f'A{fila}:H{fila}',
            'values': [dias_con_fechas]
        })
    else:
        # Fallback sin fechas
        dias = ["", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        updates.append({
            'range': f'A{fila}:H{fila}',
            'values': [dias]
        })

    fila += 1

    # ===== FILAS 3+: DATOS DE RECORDATORIOS =====
    max_recs = max(len(recs) for recs in recordatorios_por_dia.values())
    max_recs = min(max_recs, 15)

    for fila_idx in range(max_recs):
        fila_valores = [""]  # Columna A vacía

        for dia_idx in range(7):
            recs = recordatorios_por_dia[dia_idx]
            if fila_idx < len(recs):
                rec = recs[fila_idx]
                emoji = {"urgente": "⚠️", "importante": "📌", "tarea": "✅", "nota": "📝", "idea": "💡"}.get(rec.type, "•")
                texto = f"[P:{rec.prioridad}] {emoji}\n{rec.content[:30]}"
                if rec.hora_limite:
                    texto += f"\n⏰ {rec.hora_limite.strftime('%H:%M')}"
                fila_valores.append(texto)
            else:
                fila_valores.append("")

        updates.append({
            'range': f'A{fila}:H{fila}',
            'values': [fila_valores]
        })
        fila += 1

    return updates


def _aplicar_formato_batch(sheet):
    """Aplica All el formato en una sola llamada batch_update"""
    sheet_id = sheet._properties["sheetId"]

    requests = [
        # Encabezado columna I
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 8,
                          "endColumnIndex": 9},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.2, "green": 0.3, "blue": 0.5},
                        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat"
            }
        },
        # Encabezado columna J
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 9,
                          "endColumnIndex": 10},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.3, "green": 0.3, "blue": 0.3},
                        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat"
            }
        },
        # Título tabla semanal
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": FILA_INICIO_RECORDATORIOS - 1,
                          "endRowIndex": FILA_INICIO_RECORDATORIOS, "startColumnIndex": 0, "endColumnIndex": 8},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
                        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True,
                                       "fontSize": 11},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat"
            }
        },
        # Encabezados días tabla
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": FILA_INICIO_RECORDATORIOS,
                          "endRowIndex": FILA_INICIO_RECORDATORIOS + 1, "startColumnIndex": 1, "endColumnIndex": 8},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                        "textFormat": {"bold": True, "fontSize": 9},
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat"
            }
        }
    ]

    sheet.spreadsheet.batch_update({"requests": requests})


def reordenar_hojas_cronologicamente(forzar=False):
    """
    Reordena físicamente las hojas en Google Sheets
    Orden: Template primero, luego semanas más recientes primero

    Returns:
        int: Número de hojas reordenadas
    """
    from modules.agenda.sheets_manager import get_sheets_manager
    from core.lobo_google.rate_limiter import RATE_LIMITER

    try:
        logger.info("🔄 Reordenando hojas cronológicamente...")

        manager = get_sheets_manager()
        spreadsheet = manager.spreadsheet

        RATE_LIMITER.wait_if_needed()
        todas_las_hojas = spreadsheet.worksheets()

        # Separar template y hojas semanales
        template = None
        hojas_semanales = []
        hojas_excluidas = ["Hoja 1", "Sheet1", "26-2"]

        for hoja in todas_las_hojas:
            if hoja.title in hojas_excluidas:
                template = hoja
            else:
                # Validar que sea hoja semanal
                if "-" in hoja.title:
                    meses = [
                        "ene", "feb", "mar", "abr", "may", "jun",
                        "jul", "ago", "sep", "oct", "nov", "dic"
                    ]
                    if any(mes in hoja.title.lower() for mes in meses):
                        fecha_lunes = _calcular_lunes_desde_nombre_hoja(hoja.title)
                        if fecha_lunes:
                            hojas_semanales.append((fecha_lunes, hoja))

        if not hojas_semanales:
            logger.warning("⚠️  No hay hojas semanales para reordenar")
            return 0

        # Ordenar hojas semanales (MÁS RECIENTE PRIMERO)
        hojas_semanales.sort(key=lambda x: x[0], reverse=False)

        if not forzar:
            indices_actuales = [h[1].index for h in hojas_semanales]
            indices_esperados = list(range(1 if template else 0, len(hojas_semanales) + (1 if template else 0)))

            if indices_actuales == indices_esperados:
                logger.info("✅ Hojas ya están en orden correcto")
                return 0

        logger.info(f"📋 Orden deseado: {[h[1].title for h in hojas_semanales]}")

        # ===== REORDENAR FÍSICAMENTE EN GOOGLE SHEETS =====
        sheet_id = spreadsheet.id
        requests = []

        # Posición inicial: 0 = template, 1 = primera hoja semanal, etc.
        nueva_posicion = 1 if template else 0

        for fecha, hoja in hojas_semanales:
            # Obtener índice actual de la hoja
            indice_actual = hoja.index

            # Solo mover si no está en la posición correcta
            if indice_actual != nueva_posicion:
                requests.append({
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": hoja.id,
                            "index": nueva_posicion
                        },
                        "fields": "index"
                    }
                })
                logger.debug(f"📌 Moviendo '{hoja.title}' de posición {indice_actual} → {nueva_posicion}")

            nueva_posicion += 1

        # Ejecutar reordenamiento si hay cambios
        if requests:
            RATE_LIMITER.wait_if_needed()
            spreadsheet.batch_update({"requests": requests})
            logger.info(f"✅ {len(requests)} hojas reordenadas")
            return len(requests)
        else:
            logger.info("✅ Hojas ya están en orden correcto")
            return 0

    except Exception as e:
        logger.error(f"❌ Error al reordenar hojas: {e}")
        return 0

# ===== FUNCIONES DE COMPATIBILIDAD =====

def actualizar_recordatorios_sheets():
    return actualizar_recordatorios_todas_las_hojas()


def pintar_recordatorios_semana(fecha_inicio_semana=None):
    """Sincroniza solo la hoja actual (rápido)"""
    from modules.agenda.sheets_manager import get_sheets_manager

    if fecha_inicio_semana is None:
        hoy = date.today()
        fecha_inicio_semana = hoy - timedelta(days=hoy.weekday())

    try:
        memoria = Memory()
        recordatorios = memoria.recall_por_semana(fecha_inicio_semana)
        todos = memoria.recall(estado="pendiente")
        con_fecha = [r for r in todos if r.fecha_limite]
        sin_fecha = [r for r in todos if not r.fecha_limite]

        con_fecha.sort(key=lambda x: (x.fecha_limite, x.hora_limite or datetime.min.time(), x.prioridad))
        sin_fecha.sort(key=lambda x: x.id)

        sheet = get_sheets_manager().obtener_hoja_por_fecha(fecha_inicio_semana)
        _actualizar_hoja_completa_optimizado(sheet, fecha_inicio_semana, con_fecha, sin_fecha)

        logger.info(f"✅ Hoja actual sincronizada")
    except Exception as e:
        logger.error(f"Error: {e}")

    if not recordatorios:
        logger.info("No hay recordatorios para esta semana")
        return

    # ===== APLICAR RATE LIMITING =====
    from core.lobo_google.rate_limiter import RATE_LIMITER
    RATE_LIMITER.wait_if_needed()

    limpiar_area_recordatorios(sheet)

    recordatorios_por_dia = {i: [] for i in range(7)}

    for rec in recordatorios:
        if rec.fecha_limite:
            dia_semana = rec.fecha_limite.weekday()
            recordatorios_por_dia[dia_semana].append(rec)

    fila = FILA_INICIO_RECORDATORIOS

    # ===== ENCABEZADO PRINCIPAL =====
    RATE_LIMITER.wait_if_needed()
    sheet.update(f"A{fila}", [["RECORDATORIOS PENDIENTES DE LA SEMANA"]])

    RATE_LIMITER.wait_if_needed()
    sheet.format(f"A{fila}:H{fila}", {
        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
        "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1

    # ===== ENCABEZADOS DE DÍAS =====
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    RATE_LIMITER.wait_if_needed()
    sheet.update(f"B{fila}:H{fila}", [dias])

    RATE_LIMITER.wait_if_needed()
    sheet.format(f"B{fila}:H{fila}", {
        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
        "textFormat": {"bold": True},
        "horizontalAlignment": "CENTER"
    })

    fila += 1
    fila_inicio_datos = fila

    # ===== PINTAR RECORDATORIOS POR DÍA =====
    max_recs = max(len(recs) for recs in recordatorios_por_dia.values())
    max_recs = min(max_recs, 20)  # Máximo 20 por día

    # Preparar TODOS los datos en un solo batch
    updates = []
    formatos = []

    for dia_idx in range(7):
        recs = recordatorios_por_dia[dia_idx]
        col = dia_idx + 2  # Columna B=2, C=3, ..., H=8
        fila_actual = fila_inicio_datos

        for rec in recs[:20]:
            emoji = {
                "urgente": "⚠️",
                "importante": "📌",
                "tarea": "✅",
                "nota": "📝",
                "idea": "💡"
            }.get(rec.type, "•")

            # Construir texto
            texto = f"[P:{rec.prioridad}] {emoji}\n"
            texto += f"{rec.content[:40]}"
            if len(rec.content) > 40:
                texto += "..."

            if rec.hora_limite:
                texto += f"\n⏰ {rec.hora_limite.strftime('%H:%M')}"

            # Agregar a batch de updates
            celda = rowcol_to_a1(fila_actual, col)
            updates.append((celda, [[texto]]))

            # Agregar formato
            color = COLORES_PRIORIDAD.get(rec.prioridad, (1.0, 1.0, 1.0))
            formato = {
                "backgroundColor": {"red": color[0], "green": color[1], "blue": color[2]},
                "textFormat": {"fontSize": 9},
                "wrapStrategy": "WRAP",
                "verticalAlignment": "TOP"
            }
            formatos.append((celda, formato))

            fila_actual += 1

    # ===== EJECUTAR BATCH UPDATES =====
    if updates:
        # Actualizar contenido en batches de 10
        RATE_LIMITER.wait_if_needed()

        for i in range(0, len(updates), 10):
            batch = updates[i:i + 10]

            # Preparar data para batch_update
            data = []
            for celda, valores in batch:
                data.append({
                    'range': celda,
                    'values': valores
                })

            RATE_LIMITER.wait_if_needed()
            sheet.batch_update(data, value_input_option='USER_ENTERED')
            logger.debug(f"Batch de recordatorios actualizado: {len(batch)} celdas")

    # ===== APLICAR FORMATOS EN BATCH =====
    if formatos:
        RATE_LIMITER.wait_if_needed()

        for i in range(0, len(formatos), 10):
            batch = formatos[i:i + 10]

            for celda, formato in batch:
                RATE_LIMITER.wait_if_needed()
                sheet.format(celda, formato)

    logger.info(f"Recordatorios de la semana pintados en hoja '{sheet.title}': {len(updates)} recordatorios")


def pintar_todos_pendientes(sheet=None):
    """DEPRECATED"""
    logger.warning("⚠️  Deprecated")


def limpiar_columnas_pendientes(sheet):
    """Limpia columnas I y J"""
    from core.lobo_google.rate_limiter import RATE_LIMITER
    RATE_LIMITER.wait_if_needed()
    sheet.batch_clear(["I1:I60", "J1:J60"])


def limpiar_area_recordatorios(sheet):
    """Limpia área semanal"""
    from core.lobo_google.rate_limiter import RATE_LIMITER
    RATE_LIMITER.wait_if_needed()
    sheet.batch_clear([f"A{FILA_INICIO_RECORDATORIOS}:H55"])


def limpiar_columna_todos_pendientes(sheet):
    limpiar_columnas_pendientes(sheet)
