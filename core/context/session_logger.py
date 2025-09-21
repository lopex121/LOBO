# core/context/session_logger.py
from core.context.logs import BITACORA
import logging
import inspect

class SessionLogger:
    def __init__(self, session_id="system"):
        self.session_id = session_id

    logging.basicConfig(
        filename="lobo.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    def log(self, nivel, mensaje, usuario="system"):

        # 🔹 Detectar automáticamente el origen
        stack = inspect.stack()
        # El frame 1 es quien llamó al logger (ej: brain, router, auth, etc.)
        caller_module = inspect.getmodule(stack[1][0])
        if caller_module and hasattr(caller_module, "__name__"):
            origen = caller_module.__name__.upper()
        else:
            # Si no lo detecta, tratamos de deducir del stack
            origen = stack[1].function.upper() if stack and len(stack) > 1 else "ROUTER"

        # Guardar en archivo local
        if nivel.upper() == "INFO":
            logging.info(mensaje)
        elif nivel.upper() == "WARNING":
            logging.warning(mensaje)
        elif nivel.upper() == "ERROR":
            logging.error(mensaje)
        else:
            logging.debug(mensaje)

        # Guardar en la base de datos (bitácora global)
        BITACORA.registrar(origen, nivel, mensaje, usuario)