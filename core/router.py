# core/router.py
from core.context.global_session import SESSION
from modules.recordatorios.recordatorios import Recordatorios
from modules.usuarios.usuarios import comando_nuevo_usuario, comando_eliminar_usuario
from modules.bitacora.bitacora import comando_ver_bitacora, Bitacora
bitacora = Bitacora()

recordatorios = Recordatorios()

comandos = {
    "guardar": recordatorios.guardar,
    "recordar": recordatorios.recordar,
    "eliminar_recuerdo": recordatorios.eliminar,
    "nuevo_usuario": comando_nuevo_usuario,
    "eliminar_usuario": comando_eliminar_usuario,
    "ver_bitacora": comando_ver_bitacora,
}

class Router:
    def __init__(self, brain):
        self.brain = brain

    def route(self, command):
        if not command.strip():
            bitacora.registrar("router", "comando vacío", "Se recibío un comando vacío",
                               SESSION.user.username)
            return "[LOBO] Comando vacío."

        partes = command.strip().split()
        nombre_comando = partes[0].lower()
        argumentos = partes[1:]

        if nombre_comando in comandos:
            funcion = comandos[nombre_comando]
            try:
                funcion(argumentos)  # Siempre mandamos lista, vacía si es necesario
                bitacora.registrar("router", "error", "Comando no reconocido",
                                   SESSION.user.username)
                return ""
            except Exception as e:
                bitacora.registrar("router", "error", "Error al ejecutar el comando",
                                   SESSION.user.username)
                return f"[LOBO] Error al ejecutar el comando '{nombre_comando}': {e}"
        return f"[LOBO] Comando no reconocido: {nombre_comando}"
