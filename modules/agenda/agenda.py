# modules/agenda/agenda.py
from core.lobo_google.lobo_sheets import get_sheet

# Días de la semana según tu hoja
DIAS = ["Hora", "Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]


def agregar_evento(hora: str, dia: str, evento: str):
    # Agrega un evento en la celda correspondiente (hora, día).
    sheet = get_sheet()

    # Buscar fila con la hora
    horas = sheet.col_values(1)
    try:
        fila = horas.index(hora) + 1
    except ValueError:
        raise Exception(f"❌ La hora {hora} no existe en la hoja.")

    # Verificar columna del día
    if dia not in DIAS:
        raise Exception(f"❌ Día {dia} no válido. Usa: {DIAS[1:]}")
    columna = DIAS.index(dia) + 1

    # Escribir en la celda
    sheet.update_cell(fila, columna, evento)
    print(f"✅ Evento agregado: {evento} en {dia} a las {hora}")


def eliminar_evento(hora: str, dia: str):
    # Elimina un evento en la celda correspondiente (hora, día).
    sheet = get_sheet()

    # Buscar fila con la hora
    horas = sheet.col_values(1)
    try:
        fila = horas.index(hora) + 1
    except ValueError:
        raise Exception(f"❌ La hora {hora} no existe en la hoja.")

    # Verificar columna del día
    if dia not in DIAS:
        raise Exception(f"❌ Día {dia} no válido. Usa: {DIAS[1:]}")
    columna = DIAS.index(dia) + 1

    # Borrar contenido
    sheet.update_cell(fila, columna, "")
    print(f"🗑️ Evento eliminado en {dia} a las {hora}")
