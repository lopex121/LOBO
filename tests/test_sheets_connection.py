# test_sheets_connection.py
"""
Script para diagnosticar problemas de conexión con Google Sheets
Ejecutar: python test_sheets_connection.py
"""

import sys
import os

print("🔍 Diagnóstico de Conexión con Google Sheets")
print("=" * 60)

# Test 1: Verificar archivo de credenciales
print("\n1️⃣ Verificando archivo de credenciales...")
credential_path = os.path.join("core", "lobo_google", "LOBO-credenciales.json")

if os.path.exists(credential_path):
    print(f"   ✅ Archivo encontrado: {credential_path}")

    # Verificar que sea JSON válido
    try:
        import json

        with open(credential_path, 'r') as f:
            creds_data = json.load(f)

        print(f"   ✅ JSON válido")
        print(f"   📧 Service account email: {creds_data.get('client_email', 'N/A')}")
    except json.JSONDecodeError as e:
        print(f"   ❌ ERROR: JSON inválido - {e}")
        sys.exit(1)
else:
    print(f"   ❌ ERROR: Archivo no encontrado en {credential_path}")
    sys.exit(1)

# Test 2: Verificar importaciones
print("\n2️⃣ Verificando librerías...")
try:
    import gspread

    print(f"   ✅ gspread instalado (versión: {gspread.__version__})")
except ImportError:
    print("   ❌ ERROR: gspread no instalado")
    print("   Instalar con: pip install gspread")
    sys.exit(1)

try:
    from google.oauth2.service_account import Credentials

    print("   ✅ google-auth instalado")
except ImportError:
    print("   ❌ ERROR: google-auth no instalado")
    print("   Instalar con: pip install google-auth")
    sys.exit(1)

# Test 3: Intentar conexión
print("\n3️⃣ Intentando conectar con Google Sheets...")
try:
    from core.lobo_google.lobo_sheets import get_sheet

    print("   🔄 Autenticando...")
    sheet = get_sheet()

    print(f"   ✅ Conexión exitosa!")
    print(f"   📊 Hoja: {sheet.title}")
    print(f"   🔗 URL: {sheet.spreadsheet.url}")

    # Test 4: Leer primera fila
    print("\n4️⃣ Leyendo datos de prueba...")
    primera_fila = sheet.row_values(1)
    print(f"   ✅ Primera fila: {primera_fila}")

    print("\n✅ ¡TODO FUNCIONA CORRECTAMENTE!")

except FileNotFoundError as e:
    print(f"   ❌ ERROR: Archivo de credenciales no encontrado")
    print(f"   Detalle: {e}")

except gspread.exceptions.SpreadsheetNotFound:
    print(f"   ❌ ERROR: Hoja 'Horarios semanales' no encontrada")
    print(f"\n   Posibles causas:")
    print(f"   1. El nombre de la hoja no es exactamente 'Horarios semanales'")
    print(f"   2. La hoja no está compartida con: {creds_data.get('client_email', 'N/A')}")
    print(f"\n   Soluciones:")
    print(f"   • Verifica el nombre exacto de tu hoja en Google Sheets")
    print(f"   • Comparte la hoja con el email de arriba (permisos de Editor)")

except gspread.exceptions.APIError as e:
    print(f"   ❌ ERROR: API de Google Sheets")
    print(f"   Detalle: {e}")
    print(f"\n   Posibles causas:")
    print(f"   1. La API de Google Sheets no está habilitada en tu proyecto")
    print(f"   2. El service account no tiene permisos")

except Exception as e:
    print(f"   ❌ ERROR INESPERADO: {type(e).__name__}")
    print(f"   Detalle: {e}")
    import traceback

    print("\n   Stack trace completo:")
    traceback.print_exc()

print("\n" + "=" * 60)