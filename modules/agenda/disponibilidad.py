# modules/agenda/disponibilidad.py
"""
Sistema de visualización de disponibilidad y horas libres
"""

from datetime import datetime, date, time, timedelta
from modules.agenda.conflictos import CONFLICTOS
from modules.agenda.agenda_logics import listar_eventos_por_fecha


class VistaDisponibilidad:
    def __init__(self):
        self.gestor = CONFLICTOS

    def mostrar_disponibilidad_dia(self, fecha, hora_inicio="07:00", hora_fin="22:00"):
        """
        Muestra la disponibilidad de un día completo

        Args:
            fecha: date o str (YYYY-MM-DD o DD/MM/YYYY)
            hora_inicio: str - Hora mínima a considerar
            hora_fin: str - Hora máxima a considerar
        """
        # Parsear fecha
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
            except ValueError:
                fecha = datetime.strptime(fecha, "%d/%m/%Y").date()

        # Obtener eventos del día
        try:
            eventos = listar_eventos_por_fecha(fecha.isoformat())
        except:
            eventos = []

        # Obtener bloques libres
        bloques_libres = self.gestor.encontrar_horas_libres(
            fecha,
            duracion_minutos=30,
            hora_minima=hora_inicio,
            hora_maxima=hora_fin
        )

        # Calcular estadísticas
        total_minutos_libres = sum(b['duracion_min'] for b in bloques_libres)
        total_horas_libres = total_minutos_libres / 60

        total_minutos_ocupados = 0
        for evento in eventos:
            inicio = datetime.combine(fecha, evento.hora_inicio)
            fin = datetime.combine(fecha, evento.hora_fin)
            total_minutos_ocupados += (fin - inicio).seconds // 60

        total_horas_ocupadas = total_minutos_ocupados / 60

        # Encabezado
        print("\n" + "═" * 70)
        try:
            fecha_str = fecha.strftime("%A, %d de %B de %Y").capitalize()
        except:
            fecha_str = fecha.strftime("%Y-%m-%d")

        print(f"📅  DISPONIBILIDAD - {fecha_str}")
        print("═" * 70)

        # Resumen
        print(f"\n📊 Resumen del día:")
        print(f"   ⏰ Horas ocupadas: {total_horas_ocupadas:.1f}h ({len(eventos)} eventos)")
        print(f"   ✅ Horas libres: {total_horas_libres:.1f}h ({len(bloques_libres)} bloques)")

        if bloques_libres:
            mayor_bloque = max(bloques_libres, key=lambda b: b['duracion_min'])
            print(
                f"   🎯 Mayor bloque libre: {mayor_bloque['duracion_min'] // 60}h {mayor_bloque['duracion_min'] % 60}min")

        # Línea de tiempo
        print(f"\n🕐 Línea de tiempo ({hora_inicio} - {hora_fin}):")
        print("─" * 70)

        # Parsear horas
        hora_min = datetime.strptime(hora_inicio, "%H:%M").time()
        hora_max = datetime.strptime(hora_fin, "%H:%M").time()

        # Crear timeline combinando eventos y bloques libres
        timeline = []

        # Agregar eventos
        for evento in sorted(eventos, key=lambda e: e.hora_inicio):
            timeline.append({
                'tipo': 'ocupado',
                'inicio': evento.hora_inicio,
                'fin': evento.hora_fin,
                'evento': evento
            })

        # Agregar bloques libres
        for bloque in bloques_libres:
            timeline.append({
                'tipo': 'libre',
                'inicio': bloque['inicio'],
                'fin': bloque['fin'],
                'duracion_min': bloque['duracion_min']
            })

        # Ordenar por hora de inicio
        timeline.sort(key=lambda x: x['inicio'])

        # Mostrar timeline
        for item in timeline:
            inicio_str = item['inicio'].strftime("%H:%M")
            fin_str = item['fin'].strftime("%H:%M")

            if item['tipo'] == 'ocupado':
                evento = item['evento']
                duracion = (datetime.combine(fecha, evento.hora_fin) -
                            datetime.combine(fecha, evento.hora_inicio)).seconds // 60

                emoji = self._get_emoji_tipo(evento.tipo_evento)

                print(f"❌ {inicio_str} - {fin_str}  {emoji} {evento.nombre}")
                if evento.descripcion:
                    print(f"   └─ {evento.descripcion[:60]}")
            else:
                duracion = item['duracion_min']
                horas = duracion // 60
                minutos = duracion % 60

                if duracion >= 60:
                    duracion_str = f"{horas}h {minutos}min" if minutos else f"{horas}h"
                else:
                    duracion_str = f"{minutos}min"

                print(f"✅ {inicio_str} - {fin_str}  Libre ({duracion_str})")

        print("─" * 70)

        # Recomendaciones
        if bloques_libres:
            print("\n💡 Mejores horarios para agendar:")
            for i, bloque in enumerate(bloques_libres[:3], 1):
                inicio_str = bloque['inicio'].strftime("%H:%M")
                fin_str = bloque['fin'].strftime("%H:%M")
                duracion = bloque['duracion_min']

                if duracion >= 120:
                    desc = "Ideal para proyectos largos"
                elif duracion >= 60:
                    desc = "Bueno para reuniones o clases"
                else:
                    desc = "Suficiente para tareas cortas"

                print(f"   {i}. {inicio_str} - {fin_str} ({duracion}min) - {desc}")

        print("\n" + "═" * 70 + "\n")

    def _get_emoji_tipo(self, tipo_evento):
        """Retorna emoji según tipo de evento"""
        emojis = {
            "clase": "📚",
            "trabajo": "💼",
            "personal": "🏠",
            "deporte": "🏋️",
            "estudio": "📖",
            "reunion": "👥"
        }
        return emojis.get(tipo_evento, "📌")

    def disponibilidad_resumen(self, fecha):
        """
        Retorna resumen compacto de disponibilidad (para dashboard)

        Returns:
            dict: {'horas_libres': float, 'mayor_bloque_min': int, 'bloques_count': int}
        """
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
            except ValueError:
                fecha = datetime.strptime(fecha, "%d/%m/%Y").date()

        bloques_libres = self.gestor.encontrar_horas_libres(fecha, duracion_minutos=30)

        if not bloques_libres:
            return {
                'horas_libres': 0,
                'mayor_bloque_min': 0,
                'bloques_count': 0
            }

        total_minutos = sum(b['duracion_min'] for b in bloques_libres)
        mayor_bloque = max(bloques_libres, key=lambda b: b['duracion_min'])

        return {
            'horas_libres': total_minutos / 60,
            'mayor_bloque_min': mayor_bloque['duracion_min'],
            'bloques_count': len(bloques_libres),
            'mayor_bloque_inicio': mayor_bloque['inicio'],
            'mayor_bloque_fin': mayor_bloque['fin']
        }


# Instancia global
DISPONIBILIDAD = VistaDisponibilidad()