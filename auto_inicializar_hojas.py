# auto_inicializar_hojas.py
"""
Script para inicializar el sistema de hojas múltiples
EJECUTAR UNA SOLA VEZ después de instalar Fase 2

Este script:
1. Renombra la hoja 2 (actual) al formato de semana
2. Crea 12 hojas futuras
3. Sincroniza todos los eventos en sus hojas correspondientes
4. Actualiza recordatorios en todas las hojas
"""

print("=" * 70)
print("  INICIALIZACIÓN DE SISTEMA DE HOJAS MÚLTIPLES - FASE 2")
print("=" * 70)
print()

input("⚠️  Este script modificará tu Google Sheet. Presiona ENTER para continuar...")

print("\n1️⃣ Inicializando sistema de hojas...")
from modules.agenda.sheets_manager import SHEETS_MANAGER

try:
    resultado = SHEETS_MANAGER.inicializar_sistema()

    if resultado['hoja_renombrada']:
        print("   ✅ Hoja actual renombrada")
    else:
        print("   ⚠️  No se pudo renombrar hoja actual")

    if resultado['hojas_creadas'] > 0:
        print(f"   ✅ {resultado['hojas_creadas']} hojas futuras creadas")
    else:
        print("   ℹ️  No se crearon hojas nuevas (probablemente ya existen)")

    if resultado['errores']:
        print("\n   ⚠️  Errores encontrados:")
        for error in resultado['errores']:
            print(f"      • {error}")

except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

print("\n2️⃣ Sincronizando eventos en hojas correspondientes...")
from modules.agenda import agenda_logics

try:
    agenda_logics.clear_sheets()
    print("   ✅ Eventos sincronizados en todas las hojas")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n3️⃣ Sincronizando recordatorios en todas las hojas...")
from modules.recordatorios.recordatorios_sheets import actualizar_recordatorios_todas_las_hojas

try:
    hojas = actualizar_recordatorios_todas_las_hojas()
    print(f"   ✅ Recordatorios actualizados en {hojas} hojas")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("✅ INICIALIZACIÓN COMPLETADA")
print("=" * 70)
print("\nAhora puedes usar LOBO normalmente.")
print("Los eventos se pintarán automáticamente en la hoja correcta de su semana.")
print()
print("Comandos nuevos:")
print("  • inicializar_hojas      - Re-ejecutar inicialización")
print("  • crear_hojas_futuras    - Crear más hojas futuras")
print("  • archivar_semana        - Archivar hojas antiguas")
print("  • sync_recordatorios_todas - Sincronizar recordatorios en todas las hojas")
print()
