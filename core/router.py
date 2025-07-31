class Router:
    def __init__(self, brain):
        self.brain = brain

    def route(self, command):
        return f"Comando recibido: {command} (aún sin lógica de módulo asignada)"