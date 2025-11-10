# test_fase2.py
"""
Verificación de Fase 2 - Hojas Múltiples
"""

print("🔍 Verificación FASE 2 - Hojas Múltiples")
print("=" * 70)

# Test 1: Importar SheetsManager
print("\n1️⃣ Verificando SheetsManager...")
try:
    from modules.agenda.sheets_manager import SHEETS_MANAGER

    print("   ✅ SheetsManager importado")

    # Test template
    if SHEETS_MANAGER.template_sheet:
        print(f"   ✅ Template encontrado: {SHEETS_MANAGER.template_sheet.title}")
    else:
        print("   ⚠️  Template no encontrado")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Verificar funciones actualizadas
print("\n2️⃣ Verificando funciones actualizadas...")
try:
    from modules.agenda import agenda_logics
    import inspect

    # Verificar que pintar_evento_sheets use SHEETS_MANAGER
    source = inspect.getsource(agenda_logics.pintar_evento_sheets)

    if 'SHEETS_MANAGER' in source:
        print("   ✅ pintar_evento_sheets actualizado")
    else:
        print("   ❌ pintar_evento_sheets NO actualizado")

    if 'obtener_hoja_por_fecha' in source:
        print("   ✅ Usa obtener_hoja_por_fecha")
    else:
        print("   ⚠️  No usa obtener_hoja_por_fecha")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Verificar comandos en router
print("\n3️⃣ Verificando comandos nuevos...")
try:
    from core.router import comandos

    comandos_fase2 = [
        'inicializar_hojas',
        'crear_hojas_futuras',
        'archivar_semana',
        'sync_recordatorios_todas'
    ]

    for cmd in comandos_fase2:
        if cmd in comandos:
            print(f"   ✅ Comando '{cmd}' disponible")
        else:
            print(f"   ❌ Comando '{cmd}' NO encontrado")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Probar generación de nombres
print("\n4️⃣ Probando generación de nombres de hojas...")
try:
    from datetime import date

    # Test 1: Semana en mismo mes
    fecha1 = date(2025, 10, 23)  # Jueves
    nombre1 = SHEETS_MANAGER.nombre_hoja_para_fecha(fecha1)
    print(f"   {fecha1} → '{nombre1}'")

    # Test 2: Semana que cruza meses
    fecha2 = date(2025, 10, 30)  # Jueves
    nombre2 = SHEETS_MANAGER.nombre_hoja_para_fecha(fecha2)
    print(f"   {fecha2} → '{nombre2}'")

    print("   ✅ Generación de nombres funcional")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Verificar acceso a historial
print("\n5️⃣ Verificando acceso a spreadsheet de historial...")
try:
    from core.lobo_google.lobo_sheets import Credentials, gspread
    import os

    SERVICE_ACCOUNT_FILE = "core/lobo_google/LOBO-credenciales.json"
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)

    historial = client.open("Horarios pasados")
    print(f"   ✅ Spreadsheet de historial accesible")
    print(f"   Hojas actuales en historial: {len(historial.worksheets())}")

except gspread.exceptions.SpreadsheetNotFound:
    print("   ❌ Spreadsheet 'Horarios pasados' no encontrado")
    print("      Crea el spreadsheet y compártelo con el service account")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Resumen
print("\n" + "=" * 70)
print("VERIFICACIÓN COMPLETADA")
print("=" * 70)
print("\nSi todos los tests pasaron, ejecuta:")
print("  python auto_inicializar_hojas.py")
print()
