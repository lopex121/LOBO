# modules/agenda/sheets_batch_manager.py
"""
LOBO - Gestor de Batch Requests para Google Sheets API
Reduce requests de N*12 hojas a operaciones agrupadas eficientes
"""

import time
from typing import List, Dict, Any, Tuple
from datetime import datetime
import gspread
from gspread_formatting import (
    CellFormat, Color, TextFormat, Borders, Border,
    format_cell_ranges
)
import logging

logger = logging.getLogger(__name__)


class SheetsBatchManager:
    """
    Gestor centralizado para operaciones batch en Google Sheets.
    Reduce el número de API calls agrupando operaciones.
    """

    def __init__(self, client: gspread.Client, spreadsheet_id: str):
        self.client = client
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet = client.open_by_key(spreadsheet_id)

        # Contadores para monitoring
        self.requests_count = 0
        self.last_request_time = time.time()
        self.requests_per_minute = []

        # Cache de worksheets para evitar re-fetch
        self._worksheets_cache = {}
        self._cache_timestamp = None
        self._cache_duration = 60  # 60 segundos

    def _refresh_cache_if_needed(self):
        """Refresca el cache de worksheets si ha expirado"""
        now = time.time()
        if (self._cache_timestamp is None or
                now - self._cache_timestamp > self._cache_duration):
            self._worksheets_cache = {
                ws.title: ws for ws in self.spreadsheet.worksheets()
            }
            self._cache_timestamp = now
            self._log_request("worksheets()")

    def get_worksheet(self, title: str) -> gspread.Worksheet:
        """Obtiene worksheet del cache o lo busca"""
        self._refresh_cache_if_needed()

        if title not in self._worksheets_cache:
            # Si no está en cache, refrescar
            self._refresh_cache_if_needed()

        return self._worksheets_cache.get(title)

    def _log_request(self, operation: str):
        """Registra un request para monitoring"""
        self.requests_count += 1
        current_time = time.time()

        # Limpiar requests antiguos (mayores a 1 minuto)
        self.requests_per_minute = [
            t for t in self.requests_per_minute
            if current_time - t < 60
        ]
        self.requests_per_minute.append(current_time)

        if len(self.requests_per_minute) >= 50:  # 50 de 60 limit
            logger.warning(f"⚠️ Rate limit cercano: {len(self.requests_per_minute)} requests/min")

    def _wait_if_needed(self):
        """Espera si estamos cerca del rate limit"""
        if len(self.requests_per_minute) >= 55:  # Margen de seguridad
            wait_time = 60 - (time.time() - self.requests_per_minute[0])
            if wait_time > 0:
                logger.info(f"⏸️ Rate limit cercano. Esperando {wait_time:.1f}s...")
                time.sleep(wait_time + 1)
                self.requests_per_minute.clear()

    def batch_update_cells(self, updates: List[Dict[str, Any]]) -> bool:
        """
        Actualiza múltiples celdas en una sola operación batch.

        updates = [
            {
                'worksheet': 'nombre_hoja',
                'range': 'A1:B2',
                'values': [['val1', 'val2'], ['val3', 'val4']]
            },
            ...
        ]
        """
        self._wait_if_needed()

        try:
            # Agrupar por worksheet
            by_worksheet = {}
            for update in updates:
                ws_title = update['worksheet']
                if ws_title not in by_worksheet:
                    by_worksheet[ws_title] = []
                by_worksheet[ws_title].append(update)

            # Ejecutar batch por worksheet
            for ws_title, ws_updates in by_worksheet.items():
                worksheet = self.get_worksheet(ws_title)
                if not worksheet:
                    logger.error(f"❌ Hoja '{ws_title}' no encontrada")
                    continue

                # Preparar batch_update
                data = []
                for upd in ws_updates:
                    data.append({
                        'range': upd['range'],
                        'values': upd['values']
                    })

                # Una sola llamada batch_update por worksheet
                worksheet.batch_update(data, value_input_option='USER_ENTERED')
                self._log_request(f"batch_update({ws_title})")

            return True

        except Exception as e:
            logger.error(f"❌ Error en batch_update_cells: {e}")
            return False

    def batch_format_cells(self, formats: List[Dict[str, Any]]) -> bool:
        """
        Aplica formato a múltiples rangos en una sola operación.

        formats = [
            {
                'worksheet': 'nombre_hoja',
                'range': 'A1:B2',
                'format': CellFormat(...)
            },
            ...
        ]
        """
        self._wait_if_needed()

        try:
            # Agrupar por worksheet
            by_worksheet = {}
            for fmt in formats:
                ws_title = fmt['worksheet']
                if ws_title not in by_worksheet:
                    by_worksheet[ws_title] = []
                by_worksheet[ws_title].append(fmt)

            # Ejecutar batch por worksheet
            for ws_title, ws_formats in by_worksheet.items():
                worksheet = self.get_worksheet(ws_title)
                if not worksheet:
                    continue

                # Preparar lista de (rango, formato)
                ranges = [(f['range'], f['format']) for f in ws_formats]

                # Una sola llamada format_cell_ranges
                format_cell_ranges(worksheet, ranges)
                self._log_request(f"format_cell_ranges({ws_title})")

            return True

        except Exception as e:
            logger.error(f"❌ Error en batch_format_cells: {e}")
            return False

    def batch_clear_ranges(self, clears: List[Dict[str, Any]]) -> bool:
        """
        Limpia múltiples rangos en operación batch.

        clears = [
            {'worksheet': 'nombre_hoja', 'range': 'A1:B10'},
            ...
        ]
        """
        self._wait_if_needed()

        try:
            by_worksheet = {}
            for clear in clears:
                ws_title = clear['worksheet']
                if ws_title not in by_worksheet:
                    by_worksheet[ws_title] = []
                by_worksheet[ws_title].append(clear['range'])

            for ws_title, ranges in by_worksheet.items():
                worksheet = self.get_worksheet(ws_title)
                if not worksheet:
                    continue

                # batch_clear en una sola llamada
                worksheet.batch_clear(ranges)
                self._log_request(f"batch_clear({ws_title})")

            return True

        except Exception as e:
            logger.error(f"❌ Error en batch_clear_ranges: {e}")
            return False

    def print_stats(self):
        """Imprime estadísticas de uso de API"""
        print("\n" + "=" * 50)
        print("📊 ESTADÍSTICAS DE API REQUESTS")
        print("=" * 50)
        print(f"Total requests esta sesión: {self.requests_count}")
        print(f"Requests último minuto: {len(self.requests_per_minute)}")
        print(f"Worksheets en cache: {len(self._worksheets_cache)}")
        print("=" * 50 + "\n")


def obtener_cliente_sheets():
    """Helper para obtener cliente de gspread"""
    from core.lobo_google.lobo_sheets import get_sheet
    sheet = get_sheet()
    return sheet.client
