# core/lobo_google/lobo_sheets.py
import gspread
from google.oauth2.service_account import Credentials
import os

# --- CONFIGURACIÓN ---
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "LOBO-credenciales.json")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ===== CACHE GLOBAL =====
_client_cache = None
_spreadsheet_cache = None


def get_client():
    """
    Obtiene el cliente de gspread (cacheado)

    Returns:
        gspread.Client
    """
    global _client_cache

    if _client_cache is None:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        _client_cache = gspread.authorize(creds)

    return _client_cache


def get_spreadsheet():
    """
    Obtiene el spreadsheet completo (cacheado)

    Returns:
        gspread.Spreadsheet
    """
    global _spreadsheet_cache

    if _spreadsheet_cache is None:
        # ===== APLICAR RATE LIMITING =====
        from core.lobo_google.rate_limiter import RATE_LIMITER
        RATE_LIMITER.wait_if_needed()

        client = get_client()
        _spreadsheet_cache = client.open("Horarios semanales")

    return _spreadsheet_cache


def get_sheet(fecha=None):
    """
    Obtiene una hoja específica del spreadsheet

    Args:
        fecha: date opcional. Si None, retorna hoja actual (esta semana)

    Returns:
        gspread.Worksheet
    """
    if fecha is None:
        from datetime import date
        fecha = date.today()

    # ===== EVITAR IMPORT CIRCULAR =====
    # En lugar de importar SHEETS_MANAGER aquí, llamamos la función directamente
    from modules.agenda.sheets_manager import obtener_hoja_por_fecha_sin_manager

    return obtener_hoja_por_fecha_sin_manager(fecha)


def get_sheet_simple():
    """
    FUNCIÓN LEGACY: Obtiene sheet1 directamente
    Usada solo durante inicialización para evitar circular imports

    Returns:
        gspread.Worksheet
    """
    spreadsheet = get_spreadsheet()
    return spreadsheet.sheet1
