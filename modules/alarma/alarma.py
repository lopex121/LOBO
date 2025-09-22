# modules/alarma/alarma.py
import threading
from datetime import datetime, timedelta
from modules.agenda.agenda_logics import get_evento_by_id
import logging

logger = logging.getLogger(__name__)

class AlarmManager:
    def __init__(self):
        self.timers = {}  # evento_id -> Timer

    def programar_alarma(self, evento_id: str, anticipacion_minutos: int = 10):
        evento = get_evento_by_id(evento_id)
        if not evento:
            raise ValueError("Evento no encontrado")

        event_dt = datetime.combine(evento.fecha_inicio, evento.hora_inicio)
        alarm_dt = event_dt - timedelta(minutes=anticipacion_minutos)
        delay = (alarm_dt - datetime.now()).total_seconds()

        if delay <= 0:
            logger.info("La alarma ya pasó o está muy cerca; no se programa.")
            return False

        timer = threading.Timer(delay, self._trigger, args=(evento_id,))
        timer.daemon = True
        timer.start()
        self.timers[evento_id] = timer
        logger.info("Alarma programada para %s (evento %s)", alarm_dt.isoformat(), evento_id)
        return True

    def cancelar_alarma(self, evento_id):
        t = self.timers.get(evento_id)
        if t:
            t.cancel()
            del self.timers[evento_id]
            return True
        return False

    def _trigger(self, evento_id):
        evento = get_evento_by_id(evento_id)
        if evento:
            # Aquí conectar con Telegram, notificación del SO, sonido, etc.
            print(f"🔔 ALARMA -> {evento.nombre} en {evento.hora_inicio.strftime('%H:%M')}")
        self.timers.pop(evento_id, None)
