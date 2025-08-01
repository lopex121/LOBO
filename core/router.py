from modules.recordatorios.recordatorios import Recordatorios
from modules.usuarios.usuarios import comando_nuevo_usuario, comando_eliminar_usuario

recordatorios = Recordatorios()

comandos = {
    "guardar": recordatorios.guardar,
    "recordar": recordatorios.recordar,
    "nuevo_usuario": comando_nuevo_usuario,
    "eliminar_usuario": comando_eliminar_usuario
}

class Router:
    def __init__(self, brain):
        self.brain = brain

    def route(self, command):
        if not command.strip():
            return "[LOBO] Comando vacío."

        partes = command.strip().split()
        nombre_comando = partes[0].lower()
        argumentos = partes[1:]

        if nombre_comando in comandos:
            funcion = comandos[nombre_comando]
            try:
                funcion(argumentos)  # Siempre mandamos lista, vacía si es necesario
                return ""
            except Exception as e:
                return f"[LOBO] Error al ejecutar el comando '{nombre_comando}': {e}"

        return f"[LOBO] Comando no reconocido: {nombre_comando}"
