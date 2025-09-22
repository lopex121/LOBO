# core/router.py
from core.context.global_session import SESSION
from modules.recordatorios.recordatorios import Recordatorios
from modules.usuarios.usuarios import comando_nuevo_usuario, comando_eliminar_usuario
from modules.bitacora.bitacora import comando_ver_bitacora, Bitacora
import shlex
from modules.agenda.agenda import AgendaAPI
from modules.alarma.alarma import AlarmManager

bitacora = Bitacora()

recordatorios = Recordatorios()

agenda = AgendaAPI()
alarmas = AlarmManager()

comandos = {
    # recordatorios
    "guardar": recordatorios.guardar,
    "recordar": recordatorios.recordar,
    "eliminar_recuerdo": recordatorios.eliminar,
    # usuarios
    "nuevo_usuario": comando_nuevo_usuario,
    "eliminar_usuario": comando_eliminar_usuario,
    # bitácora
    "ver_bitacora": comando_ver_bitacora,
    # agenda
    "agregar_evento": agenda.agregar_evento,
    "eliminar_evento": agenda.eliminar_evento,
    "editar_evento": agenda.editar_evento,
    "ver_eventos": agenda.ver_eventos,
    "buscar_evento": agenda.buscar_evento,
    "limpiar_agenda": agenda.clear_sheets,
    "importar_agenda": agenda.importar_desde_sheets,
    # alarmas
    "programar_alarma": lambda args: "[ALARMA] " + (
        str(alarmas.programar_alarma(args[0], int(args[1])) if len(args) >= 2 else alarmas.programar_alarma(args[0]))),
    "cancelar_alarma": lambda args: "[ALARMA] " + (str(alarmas.cancelar_alarma(args[0]))),
}

class Router:
    def __init__(self, brain):
        self.brain = brain

    def route(self, command):
        if not command.strip():
            bitacora.registrar("router", "comando vacío", "Se recibío un comando vacío",
                               SESSION.user.username)
            return "[LOBO] Comando vacío."

        partes = shlex.split(command.strip())
        if not partes:
            return "[LOBO] Comando vacío."

        nombre_comando = partes[0].lower()
        argumentos = partes[1:]

        if nombre_comando in comandos:
            funcion = comandos[nombre_comando]
            try:
                resultado = funcion(argumentos)  # capturamos el return
                return resultado if resultado is not None else "[LOBO] ✅ Comando ejecutado."
            except Exception as e:
                bitacora.registrar("router", "error", "Error al ejecutar el comando",
                                   SESSION.user.username)
                return f"[LOBO] Error al ejecutar el comando '{nombre_comando}': {e}"
        return f"[LOBO] Comando no reconocido: {nombre_comando}"
