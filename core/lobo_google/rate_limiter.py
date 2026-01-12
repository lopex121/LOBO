# core/lobo_google/rate_limiter.py
"""
Sistema de Rate Limiting para Google Sheets API
Limita a máximo 5 requests por minuto (versión gratuita)
"""

import time
import threading
import logging
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)


class GoogleSheetsRateLimiter:
    """
    Gestor de rate limiting para Google Sheets API

    Configuración FREE tier:
    - 60 requests/minuto (usamos 5 para margen de seguridad)
    - 500 requests/100 segundos
    """

    def __init__(self, max_requests_per_minute=5):
        self.max_requests = max_requests_per_minute
        self.window_seconds = 60
        self.requests_timestamps = deque()
        self.lock = threading.Lock()

        # Estadísticas
        self.total_requests = 0
        self.total_wait_time = 0
        self.max_wait_time = 0

    def wait_if_needed(self):
        """
        Espera si se ha alcanzado el límite de requests
        Thread-safe
        """
        with self.lock:
            now = time.time()

            # Limpiar timestamps antiguos (fuera de ventana)
            while self.requests_timestamps and \
                    now - self.requests_timestamps[0] > self.window_seconds:
                self.requests_timestamps.popleft()

            # Si alcanzamos el límite, esperar
            if len(self.requests_timestamps) >= self.max_requests:
                # Calcular tiempo de espera hasta que expire el request más antiguo
                oldest = self.requests_timestamps[0]
                wait_time = self.window_seconds - (now - oldest) + 0.5  # +0.5s de margen

                if wait_time > 0:
                    logger.info(
                        f"⏸️  Rate limit alcanzado ({len(self.requests_timestamps)}/{self.max_requests} requests). "
                        f"Esperando {wait_time:.1f}s..."
                    )

                    # Actualizar estadísticas
                    self.total_wait_time += wait_time
                    self.max_wait_time = max(self.max_wait_time, wait_time)

                    time.sleep(wait_time)

                    # Limpiar después de esperar
                    now = time.time()
                    while self.requests_timestamps and \
                            now - self.requests_timestamps[0] > self.window_seconds:
                        self.requests_timestamps.popleft()

            # Registrar nuevo request
            self.requests_timestamps.append(now)
            self.total_requests += 1

            # Log cada 10 requests
            if self.total_requests % 10 == 0:
                logger.debug(
                    f"📊 Requests: {self.total_requests} | "
                    f"En ventana: {len(self.requests_timestamps)}/{self.max_requests}"
                )

    def reset(self):
        """Resetea el contador (útil para testing)"""
        with self.lock:
            self.requests_timestamps.clear()
            self.total_requests = 0
            self.total_wait_time = 0
            self.max_wait_time = 0

    def get_stats(self):
        """Retorna estadísticas de uso"""
        with self.lock:
            return {
                'total_requests': self.total_requests,
                'requests_in_window': len(self.requests_timestamps),
                'total_wait_time': self.total_wait_time,
                'max_wait_time': self.max_wait_time,
                'avg_wait_time': self.total_wait_time / max(self.total_requests, 1)
            }

    def print_stats(self):
        """Imprime estadísticas de forma legible"""
        stats = self.get_stats()
        print("\n" + "=" * 60)
        print("📊 ESTADÍSTICAS DE RATE LIMITING - GOOGLE SHEETS API")
        print("=" * 60)
        print(f"Total de requests:         {stats['total_requests']}")
        print(f"Requests en ventana actual: {stats['requests_in_window']}/{self.max_requests}")
        print(f"Tiempo total esperado:     {stats['total_wait_time']:.1f}s")
        print(f"Espera máxima:             {stats['max_wait_time']:.1f}s")
        print(f"Espera promedio:           {stats['avg_wait_time']:.2f}s")
        print("=" * 60 + "\n")


# ===== INSTANCIA GLOBAL =====
# Plan FREE de Google Sheets API:
# - 60 requests/minuto
# - 100 requests/100 segundos (no te preocupes por este)

# Usar 55 para margen de seguridad (muy cerca del límite)
RATE_LIMITER = GoogleSheetsRateLimiter(max_requests_per_minute=55)
