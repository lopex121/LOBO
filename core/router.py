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
    # ===== RECORDATORIOS =====
    "guardar": recordatorios.guardar,
    "recordar": recordatorios.recordar,
    "completar": recordatorios.completar,
    "eliminar_recuerdo": recordatorios.eliminar,

    # ===== USUARIOS =====
    "nuevo_usuario": comando_nuevo_usuario,
    "eliminar_usuario": comando_eliminar_usuario,

    # ===== BITÁCORA =====
    "ver_bitacora": comando_ver_bitacora,

    # ===== AGENDA =====
    "agregar_evento": agenda.agregar_evento,
    "eliminar_evento": agenda.eliminar_evento,
    "editar_evento": agenda.editar_evento,
    "ver_eventos": agenda.ver_eventos,
    "buscar_evento": agenda.buscar_evento,
    "importar_agenda": agenda.importar_desde_sheets,
    "ver_disponibilidad": lambda args: _ver_disponibilidad(args),

    # ===== ALARMAS =====
    "programar_alarma": lambda args: "[ALARMA] " + (
        str(alarmas.programar_alarma(args[0], int(args[1])) if len(args) >= 2 else alarmas.programar_alarma(args[0]))),
    "cancelar_alarma": lambda args: "[ALARMA] " + (str(alarmas.cancelar_alarma(args[0]))),

    # ===== SINCRONIZACIÓN =====
    "sync_recordatorios": lambda args: _sync_recordatorios_sheets(),
    "limpiar_agenda": agenda.clear_sheets,
}

def _sync_recordatorios_sheets():
    """Sincroniza recordatorios con Google Sheets"""
    try:
        from modules.recordatorios.recordatorios_sheets import actualizar_recordatorios_sheets
        if actualizar_recordatorios_sheets():
            return "[LOBO] ✅ Recordatorios sincronizados con Sheets"
        else:
            return "[LOBO] ⚠️  Error al sincronizar recordatorios"
    except Exception as e:
        return f"[LOBO] ❌ Error: {e}"


def _ver_disponibilidad(args):
    """Muestra disponibilidad de un día"""
    from modules.agenda.disponibilidad import DISPONIBILIDAD
    from datetime import date, datetime

    if not args:
        # Hoy por defecto
        fecha = date.today()
    else:
        try:
            fecha = datetime.strptime(args[0], "%Y-%m-%d").date()
        except ValueError:
            try:
                fecha = datetime.strptime(args[0], "%d/%m/%Y").date()
            except ValueError:
                return "[LOBO] ❌ Formato inválido. Usa: ver_disponibilidad [YYYY-MM-DD o DD/MM/YYYY]"

    try:
        DISPONIBILIDAD.mostrar_disponibilidad_dia(fecha)
        return ""  # Ya imprime all
    except Exception as e:
        return f"[LOBO] ❌ Error: {e}"

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
                return f"[LOBO] ❌ Error al ejecutar el comando '{nombre_comando}': {e}"

        # Sugerencias de comandos similares
        sugerencias = self._sugerir_comando(nombre_comando)
        if sugerencias:
            return f"[LOBO] Comando no reconocido: '{nombre_comando}'\n💡 ¿Quisiste decir: {sugerencias}?"

        return f"[LOBO] Comando no reconocido: '{nombre_comando}'\nEscribe 'ayuda' para ver comandos disponibles."


    def _sugerir_comando(self, comando_erroneo):
        """Sugiere comandos similares usando distancia de Levenshtein simple"""

        def distancia(s1, s2):
            if len(s1) > len(s2):
                s1, s2 = s2, s1
            distancias = range(len(s1) + 1)
            for i2, c2 in enumerate(s2):
                nuevas_distancias = [i2 + 1]
                for i1, c1 in enumerate(s1):
                    if c1 == c2:
                        nuevas_distancias.append(distancias[i1])
                    else:
                        nuevas_distancias.append(1 + min((distancias[i1], distancias[i1 + 1], nuevas_distancias[-1])))
                distancias = nuevas_distancias
            return distancias[-1]

        # Buscar comandos similares (distancia <= 3)
        similares = []
        for cmd in comandos.keys():
            if distancia(comando_erroneo, cmd) <= 3:
                similares.append(cmd)

        if similares:
            return ", ".join(similares[:3])  # Máximo 3 sugerencias
        return None
