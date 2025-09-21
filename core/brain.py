class Brain:
    def __init__(self):
        from core.config import Config
        from core.memory import Memory
        from core.router import Router
        from core.watchdog import Watchdog

        self.config = Config()
        self.memory = Memory()
        self.router = Router(self)
        self.watchdog = Watchdog()

    def handle_command(self, command):
        return self.router.route(command)

from core.context.session_logger import SessionLogger
from core.context.global_session import SESSION

logger = SessionLogger(session_id="default")

def route_command(command):
    try:
        logger.log("INFO", f"Ejecutando comando: {command}", usuario=SESSION.user.username)
        # Aquí va la lógica real del comando
    except Exception as e:
        logger.log("ERROR", f"Error ejecutando {command}: {str(e)}", usuario=SESSION.user.username)
