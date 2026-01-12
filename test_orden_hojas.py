# test_orden_hojas.py
from modules.recordatorios.recordatorios_sheets import actualizar_recordatorios_todas_las_hojas

print("Ejecutando sincronización...")
actualizar_recordatorios_todas_las_hojas()
print("\nVerifica en Google Sheets:")
print("1. La hoja más reciente debe estar hasta adelante")
print("2. La hoja más antigua debe estar hasta atrás")
