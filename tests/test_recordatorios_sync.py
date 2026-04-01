# test_recordatorios_sync.py
from modules.recordatorios.recordatorios_sheets import actualizar_recordatorios_todas_las_hojas

print("=" * 70)
print("  PRUEBA DE SINCRONIZACIÓN DE RECORDATORIOS")
print("=" * 70)
print()

hojas = actualizar_recordatorios_todas_las_hojas()

print()
print("=" * 70)
print(f"Resultado: {hojas} hojas actualizadas")
print("=" * 70)
