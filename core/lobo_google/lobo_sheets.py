# core/lobo_google/lobo_sheets.py
import gspread
from google.oauth2.service_account import Credentials
import os

# --- CONFIGURACIÓN ---
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "LOBO-credenciales.json")
# tu JSON ^
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", # acceso a spreadsheets
          "https://www.googleapis.com/auth/drive" # acceso a drive
          ]

def get_sheet():
    # Autenticación con Google
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)

    # ABRIR TU HOJA
    # Usa el nombre EXACTO de tu Sheet (ejemplo: "horarios semanales")
    sheet = client.open("Horarios semanales").sheet1
    return sheet

# --- PRUEBAS ---
# Leer la primera fila
# fila1 = sheet.row_values(1)
# print("Primera fila:", fila1)

# Agregar un evento de prueba
# sheet.append_row(["Lunes", "08:00", "Reunión con equipo", "Pendiente"])
# print("✅ Evento agregado correctamente")
