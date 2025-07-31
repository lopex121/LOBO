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