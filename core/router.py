# core/router.py
from core.context.global_session import SESSION
from modules.recordatorios.recordatorios import Recordatorios
from modules.usuarios.usuarios import comando_nuevo_usuario, comando_eliminar_usuario
from modules.bitacora.bitacora import comando_ver_bitacora, Bitacora
import shlex
from modules.agenda.agenda import AgendaAPI
from modules.alarma.alarma import AlarmManager
from modules.agenda.agenda_optimizer import NUEVOS_COMANDOS
from modules.agenda.agenda_fixes import COMANDOS_FIXES


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
    "limpiar_agenda": agenda.clear_sheets,
    "importar_agenda": agenda.importar_desde_sheets,
    "ver_disponibilidad": lambda args: _ver_disponibilidad(args),
    **NUEVOS_COMANDOS,  # Esto agrega: guardar_plantilla, listar_plantillas, aplicar_plantilla, sincronizar_todo

    **COMANDOS_FIXES, # Agrega: sincronizar_real, limpiar_db_pasados, guardar_plantilla_desde, reordenar_hojas

    # ===== GESTIÓN DE HOJAS =====
    "inicializar_hojas": lambda args: _inicializar_hojas(),
    "crear_hojas_futuras": lambda args: _crear_hojas_futuras(),
    "archivar_semana": lambda args: _archivar_semana(args),
    "reordenar_hoja": lambda args: _reordenar_hojas(),

    # ===== ALARMAS =====
    "programar_alarma": lambda args: "[ALARMA] " + (
        str(alarmas.programar_alarma(args[0], int(args[1])) if len(args) >= 2 else alarmas.programar_alarma(args[0]))),
    "cancelar_alarma": lambda args: "[ALARMA] " + (str(alarmas.cancelar_alarma(args[0]))),

    # ===== SINCRONIZACIÓN =====
    "sync_recordatorios": lambda args: _sync_recordatorios_sheets(),
    "sync_recordatorios_todas": lambda args: _sync_recordatorios_todas_hojas(),

    # ===== AYUDA =====
    "ayuda": lambda args: _mostrar_ayuda(args),
    "help": lambda args: _mostrar_ayuda(args),
}


def _sync_recordatorios_sheets():
    """Sincroniza recordatorios con Google Sheets (solo hoja actual)"""
    try:
        from modules.recordatorios.recordatorios_sheets import actualizar_recordatorios_sheets
        if actualizar_recordatorios_sheets():
            return "[LOBO] ✅ Recordatorios sincronizados con Sheets (hoja actual)"
        else:
            return "[LOBO] ⚠️  Error al sincronizar recordatorios"
    except Exception as e:
        return f"[LOBO] ❌ Error: {e}"

def _sync_recordatorios_todas_hojas():
    """Sincroniza recordatorios en TODAS las hojas semanales"""
    try:
        from modules.recordatorios.recordatorios_sheets import actualizar_recordatorios_todas_las_hojas

        print("\n🔄 Sincronizando recordatorios en todas las hojas...")
        hojas = actualizar_recordatorios_todas_las_hojas()

        if hojas > 0:
            return f"[LOBO] ✅ Recordatorios sincronizados en {hojas} hojas"
        else:
            return "[LOBO] ⚠️  No se pudieron sincronizar recordatorios"

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


def _inicializar_hojas():
    """Inicializa el sistema de hojas múltiples"""
    from modules.agenda.sheets_manager import SHEETS_MANAGER

    try:
        resultado = SHEETS_MANAGER.inicializar_sistema()

        msg = "[LOBO] ✅ Sistema de hojas inicializado:\n"

        if resultado['hoja_renombrada']:
            msg += "   ✅ Hoja actual renombrada\n"

        if resultado['hojas_creadas'] > 0:
            msg += f"   ✅ {resultado['hojas_creadas']} hojas futuras creadas\n"

        if resultado['errores']:
            msg += "\n⚠️  Errores:\n"
            for error in resultado['errores']:
                msg += f"   • {error}\n"

        return msg

    except Exception as e:
        return f"[LOBO] ❌ Error: {e}"


def _crear_hojas_futuras():
    """Crea hojas para las próximas 12 semanas"""
    from modules.agenda.sheets_manager import SHEETS_MANAGER

    try:
        hojas_creadas = SHEETS_MANAGER.crear_hojas_futuras()
        return f"[LOBO] ✅ {hojas_creadas} hojas futuras creadas"
    except Exception as e:
        return f"[LOBO] ❌ Error: {e}"


def _archivar_semana(args):
    """Archiva una semana específica"""
    from modules.agenda.sheets_manager import SHEETS_MANAGER

    if not args:
        # Archivar automáticamente hojas antiguas
        try:
            hojas = SHEETS_MANAGER.archivar_semanas_antiguas()
            if hojas:
                return f"[LOBO] ✅ Archivadas: {', '.join(hojas)}"
            else:
                return "[LOBO] ℹ️  No hay hojas antiguas para archivar"
        except Exception as e:
            return f"[LOBO] ❌ Error: {e}"
    else:
        # Archivar hoja específica
        nombre_hoja = " ".join(args)
        try:
            if SHEETS_MANAGER.archivar_hoja(nombre_hoja):
                return f"[LOBO] ✅ Hoja '{nombre_hoja}' archivada"
            else:
                return f"[LOBO] ❌ No se pudo archivar '{nombre_hoja}'"
        except Exception as e:
            return f"[LOBO] ❌ Error: {e}"


def _reordenar_hojas():
    """Reordena hojas cronológicamente en Google Sheets"""
    try:
        from modules.recordatorios.recordatorios_sheets import reordenar_hojas_cronologicamente

        print("\n🔄 Reordenando hojas en Google Sheets...")
        hojas_movidas = reordenar_hojas_cronologicamente()

        if hojas_movidas > 0:
            return f"[LOBO] ✅ {hojas_movidas} hojas reordenadas correctamente"
        else:
            return "[LOBO] ✅ Hojas ya están en orden correcto"

    except Exception as e:
        return f"[LOBO] ❌ Error: {e}"


def _mostrar_ayuda(args):
    """Muestra ayuda de comandos"""
    if not args:
        # Ayuda general
        return """
🐺 LOBO - Comandos Disponibles

═══════════════════════════════════════════════════════════
RECORDATORIOS
  guardar "texto" etiqueta [fecha] [hora] [prioridad=N]
  recordar [filtro]
  completar <id>
  eliminar_recuerdo <id>

AGENDA
  agregar_evento "nombre" YYYY-MM-DD HH:MM HH:MM
  ver_eventos [dia|semana|mes]
  editar_evento <id> campo=valor
  eliminar_evento <id>
  buscar_evento "texto"
  ver_disponibilidad [fecha]

SINCRONIZACIÓN
  sync_recordatorios
  sync_recordatorios_todas
  limpiar_agenda
  importar_agenda
  listar_plantillas
  sincronizar_todo
  guardar_plantilla <nombre>
  aplicar_plantilla <nombre> [semanas]

HOJAS MÚLTIPLES
  inicializar_hojas
  crear_hojas_futuras
  archivar_semana

SISTEMA
  ayuda <comando>        # Ayuda específica
  ver_bitacora [limite]  # Solo admin
  salir / exit

═══════════════════════════════════════════════════════════
Usa 'ayuda <comando>' para más detalles
Ejemplo: ayuda agregar_evento
"""

class Router:
    def __init__(self, brain):
        self.brain = brain

    def route(self, command):
        if not command.strip():
            bitacora.registrar("router", "comando vacío", "Se recibió un comando vacío",
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
                resultado = funcion(argumentos)
                return resultado if resultado is not None else "[LOBO] ✅ Comando ejecutado."
            except Exception as e:
                bitacora.registrar("router", "error", f"Error al ejecutar {nombre_comando}: {str(e)}",
                                   SESSION.user.username)
                return f"[LOBO] ❌ Error al ejecutar '{nombre_comando}': {e}"

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
