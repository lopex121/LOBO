# core/dashboard.py
"""
Sistema de dashboard para LOBO
Muestra resumen al iniciar: eventos, alarmas, recordatorios, errores
"""

from datetime import date, datetime, timedelta
from core.memory import Memory
from modules.agenda.agenda_logics import listar_eventos_por_fecha
from core.context.logs import BITACORA
from core.db.sessions import SessionLocal
from core.db.schema import BitacoraRegistro
import locale

# Configurar locale para español
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_MX.UTF-8')
    except:
        pass  # Si falla, usar locale por defecto


class Dashboard:
    def __init__(self):
        self.memoria = Memory()
        self.hoy = date.today()

    def mostrar(self):
        """Muestra el dashboard completo"""
        self._imprimir_encabezado()
        self._mostrar_agenda_hoy()
        self._mostrar_alarmas()
        self._mostrar_recordatorios_urgentes()
        self._mostrar_errores_recientes()
        self._imprimir_pie()

    def _imprimir_encabezado(self):
        """Encabezado del dashboard"""
        # Fecha formateada
        try:
            fecha_str = self.hoy.strftime("%A, %d de %B de %Y").capitalize()
        except:
            fecha_str = self.hoy.strftime("%Y-%m-%d")

        print("\n" + "═" * 65)
        print("           🐺 L O B O - Dashboard Diario".center(65))
        print(f"           {fecha_str}".center(65))
        print("═" * 65 + "\n")

    def _mostrar_agenda_hoy(self):
        """Muestra eventos de hoy"""
        try:
            eventos = listar_eventos_por_fecha(self.hoy.isoformat())
        except:
            eventos = []

        print("📅 AGENDA HOY:")

        if not eventos:
            print("   • Sin eventos programados")
        else:
            eventos_ordenados = sorted(eventos, key=lambda e: e.hora_inicio)

            for evento in eventos_ordenados:
                hora_inicio = evento.hora_inicio.strftime("%H:%M")
                hora_fin = evento.hora_fin.strftime("%H:%M")

                # Emoji según tipo
                emoji_map = {
                    "clase": "📚",
                    "trabajo": "💼",
                    "personal": "🏠",
                    "deporte": "🏋️",
                    "estudio": "📖",
                    "reunion": "👥"
                }
                emoji = emoji_map.get(evento.tipo_evento, "📌")

                print(f"   {emoji} {hora_inicio} - {hora_fin}  {evento.nombre}")

        # Agregar disponibilidad
        try:
            from modules.agenda.disponibilidad import DISPONIBILIDAD
            resumen = DISPONIBILIDAD.disponibilidad_resumen(self.hoy)

            if resumen['horas_libres'] > 0:
                mayor_bloque_h = resumen['mayor_bloque_min'] // 60
                mayor_bloque_m = resumen['mayor_bloque_min'] % 60

                if mayor_bloque_h > 0:
                    bloque_str = f"{mayor_bloque_h}h {mayor_bloque_m}min" if mayor_bloque_m else f"{mayor_bloque_h}h"
                else:
                    bloque_str = f"{mayor_bloque_m}min"

                inicio_str = resumen['mayor_bloque_inicio'].strftime("%H:%M")
                fin_str = resumen['mayor_bloque_fin'].strftime("%H:%M")

                print(f"\n   🕐 Horas libres hoy: {resumen['horas_libres']:.1f}h")
                print(f"   🎯 Mayor bloque: {inicio_str}-{fin_str} ({bloque_str})")
        except Exception as e:
            pass  # Si falla disponibilidad, continuar sin ella

        print()

    def _mostrar_alarmas(self):
        """Muestra alarmas programadas para hoy"""
        print("🔔 ALARMAS PROGRAMADAS:")

        # All: Integrar con el módulo de alarmas cuando esté completo
        # Por ahora, mostrar eventos con anticipación de 5 min

        try:
            eventos = listar_eventos_por_fecha(self.hoy.isoformat())

            if not eventos:
                print("   • Sin alarmas programadas\n")
                return

            for evento in sorted(eventos, key=lambda e: e.hora_inicio):
                # Calcular hora de alarma (5 min antes)
                hora_evento = datetime.combine(self.hoy, evento.hora_inicio)
                hora_alarma = hora_evento - timedelta(minutes=5)

                print(f"   🔔 {hora_alarma.strftime('%H:%M')} - {evento.nombre} (5 min antes)")
        except:
            print("   • Sin alarmas programadas")

        print()

    def _mostrar_recordatorios_urgentes(self):
        """Muestra recordatorios urgentes y próximos a vencer"""
        print("📝 RECORDATORIOS URGENTES:")

        # Vencidos
        vencidos = self.memoria.recall_vencidos()

        # Próximos 3 días
        proximos = self.memoria.recall_proximos(dias=3)

        # Urgentes sin fecha
        urgentes = self.memoria.recall(mem_type="urgente", estado="pendiente")
        urgentes_sin_fecha = [u for u in urgentes if not u.fecha_limite]

        # Prioridad 1 (sin importar tipo)
        prioridad_1 = self.memoria.recall_por_prioridad(1, 1)

        if not vencidos and not proximos and not urgentes_sin_fecha and not prioridad_1:
            print("   ✅ Sin recordatorios urgentes\n")
            return

        # Mostrar vencidos
        if vencidos:
            for rec in vencidos[:3]:  # Solo primeros 3
                dias_vencido = (self.hoy - rec.fecha_limite).days
                emoji = "⚠️" if rec.type == "urgente" else "✅"
                print(f"   🔴 [P:{rec.prioridad}] {emoji} {rec.content[:40]}")
                print(f"      VENCIDO hace {dias_vencido} día(s)")

        # Mostrar próximos
        if proximos:
            for rec in proximos[:3]:  # Solo primeros 3
                dias_restantes = (rec.fecha_limite - self.hoy).days
                emoji = "⚠️" if rec.type == "urgente" else "📌" if rec.type == "importante" else "✅"

                if dias_restantes == 0:
                    when = "¡HOY!"
                elif dias_restantes == 1:
                    when = "Mañana"
                else:
                    when = f"En {dias_restantes} días"

                print(f"   ⚠️  [P:{rec.prioridad}] {emoji} {rec.content[:40]}")
                print(f"      {when}")
                if rec.hora_limite:
                    print(f"      a las {rec.hora_limite.strftime('%H:%M')}")

        # Mostrar urgentes sin fecha
        if urgentes_sin_fecha:
            for rec in urgentes_sin_fecha[:2]:
                print(f"   ⚠️  [P:{rec.prioridad}] {rec.content[:40]} (sin fecha)")

        print()

    def _mostrar_errores_recientes(self):
        """Muestra errores recientes de la bitácora"""
        print("⚠️  ERRORES RECIENTES:")

        try:
            db = SessionLocal()

            # Buscar errores de las últimas 24 horas
            hace_24h = datetime.now() - timedelta(hours=24)

            errores = db.query(BitacoraRegistro).filter(
                BitacoraRegistro.accion.like('%error%')
            ).filter(
                BitacoraRegistro.timestamp >= hace_24h
            ).order_by(BitacoraRegistro.timestamp.desc()).limit(3).all()

            db.close()

            if not errores:
                print("   ✅ Ninguno\n")
                return

            for error in errores:
                tiempo = error.timestamp.strftime("%H:%M")
                print(f"   🔴 [{tiempo}] {error.modulo.upper()}: {error.descripcion[:50]}")
        except:
            print("   ⚠️  No se pudo consultar la bitácora\n")

        print()

    def _imprimir_pie(self):
        """Pie del dashboard"""
        print("═" * 65)
        print("Escribe 'ayuda' para ver comandos | 'salir' para cerrar".center(65))
        print("═" * 65 + "\n")

    def tiene_vencidos(self):
        """Retorna True si hay recordatorios vencidos"""
        vencidos = self.memoria.recall_vencidos()
        return len(vencidos) > 0


def mostrar_dashboard():
    """Función rápida para mostrar el dashboard"""
    dashboard = Dashboard()
    dashboard.mostrar()
    return dashboard