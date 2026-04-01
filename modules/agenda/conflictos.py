# modules/agenda/conflictos.py
"""
Sistema de detección y resolución de conflictos de horarios
"""

from datetime import datetime, date, time, timedelta
from core.db.db import SessionLocal  # migrado desde core.db.sessions
from core.db.schema import Evento
from sqlalchemy import and_


class GestorConflictos:
    def __init__(self):
        self.db = SessionLocal()

    def detectar_conflictos(self, fecha, hora_inicio, hora_fin, evento_id_excluir=None):
        if isinstance(fecha, str):
            fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
        if isinstance(hora_inicio, str):
            hora_inicio = datetime.strptime(hora_inicio, "%H:%M").time()
        if isinstance(hora_fin, str):
            hora_fin = datetime.strptime(hora_fin, "%H:%M").time()

        query = self.db.query(Evento).filter(
            and_(
                Evento.fecha_inicio == fecha,
                Evento.es_maestro == False
            )
        )

        if evento_id_excluir:
            query = query.filter(Evento.id != evento_id_excluir)

        eventos_dia = query.all()

        conflictos = []

        for evento in eventos_dia:
            if self._hay_traslape(hora_inicio, hora_fin, evento.hora_inicio, evento.hora_fin):
                conflictos.append(evento)

        return conflictos

    def _hay_traslape(self, inicio1, fin1, inicio2, fin2):
        def time_to_minutes(t):
            return t.hour * 60 + t.minute

        inicio1_min = time_to_minutes(inicio1)
        fin1_min = time_to_minutes(fin1)
        inicio2_min = time_to_minutes(inicio2)
        fin2_min = time_to_minutes(fin2)

        return inicio1_min < fin2_min and fin1_min > inicio2_min

    def encontrar_horas_libres(self, fecha, duracion_minutos=60, hora_minima="07:00", hora_maxima="22:00"):
        if isinstance(fecha, str):
            fecha = datetime.strptime(fecha, "%Y-%m-%d").date()
        if isinstance(hora_minima, str):
            hora_minima = datetime.strptime(hora_minima, "%H:%M").time()
        if isinstance(hora_maxima, str):
            hora_maxima = datetime.strptime(hora_maxima, "%H:%M").time()

        eventos = self.db.query(Evento).filter(
            and_(
                Evento.fecha_inicio == fecha,
                Evento.es_maestro == False
            )
        ).order_by(Evento.hora_inicio).all()

        bloques_libres = []
        hora_actual = hora_minima

        for evento in eventos:
            if self._time_to_minutes(hora_actual) < self._time_to_minutes(evento.hora_inicio):
                duracion = self._time_to_minutes(evento.hora_inicio) - self._time_to_minutes(hora_actual)

                if duracion >= duracion_minutos:
                    bloques_libres.append({
                        "inicio": hora_actual,
                        "fin": evento.hora_inicio,
                        "duracion_min": duracion
                    })

            hora_actual = max(hora_actual, evento.hora_fin)

        if self._time_to_minutes(hora_actual) < self._time_to_minutes(hora_maxima):
            duracion = self._time_to_minutes(hora_maxima) - self._time_to_minutes(hora_actual)

            if duracion >= duracion_minutos:
                bloques_libres.append({
                    "inicio": hora_actual,
                    "fin": hora_maxima,
                    "duracion_min": duracion
                })

        return bloques_libres

    def _time_to_minutes(self, t):
        return t.hour * 60 + t.minute

    def sugerir_horarios(self, fecha, duracion_minutos, conflictos):
        bloques_libres = self.encontrar_horas_libres(fecha, duracion_minutos)

        sugerencias = []

        for bloque in bloques_libres[:5]:
            inicio = bloque["inicio"]

            inicio_dt = datetime.combine(fecha, inicio)
            fin_dt = inicio_dt + timedelta(minutes=duracion_minutos)
            fin = fin_dt.time()

            if bloque["duracion_min"] == duracion_minutos:
                motivo = "Encaja perfectamente"
            elif bloque["duracion_min"] > duracion_minutos * 2:
                motivo = f"Bloque amplio disponible ({bloque['duracion_min']} min)"
            else:
                motivo = f"Disponible ({bloque['duracion_min']} min)"

            sugerencias.append({
                "inicio": inicio,
                "fin": fin,
                "motivo": motivo
            })

        return sugerencias

    def mostrar_conflictos_y_sugerencias(self, fecha, hora_inicio, hora_fin, conflictos):
        print("\n" + "⚠️ " * 25)
        print("   CONFLICTO DE HORARIO DETECTADO")
        print("⚠️ " * 25 + "\n")

        print(f"📅 Fecha: {fecha.strftime('%d/%m/%Y')}")
        print(f"🕐 Horario solicitado: {hora_inicio.strftime('%H:%M')} - {hora_fin.strftime('%H:%M')}\n")

        print("🔴 Eventos en conflicto:")
        for i, evento in enumerate(conflictos, 1):
            print(f"   {i}. {evento.nombre}")
            print(f"      {evento.hora_inicio.strftime('%H:%M')} - {evento.hora_fin.strftime('%H:%M')}")
            if evento.descripcion:
                print(f"      Descripción: {evento.descripcion}")

        duracion = (datetime.combine(fecha, hora_fin) - datetime.combine(fecha, hora_inicio)).seconds // 60

        sugerencias = self.sugerir_horarios(fecha, duracion, conflictos)

        print(f"\n💡 Horarios alternativos sugeridos ({duracion} min):")

        if not sugerencias:
            print("   (No hay horarios libres disponibles este día)")
        else:
            for i, sug in enumerate(sugerencias, 1):
                print(f"   {i}. {sug['inicio'].strftime('%H:%M')} - {sug['fin'].strftime('%H:%M')}  ({sug['motivo']})")

        print("\n" + "═" * 60)
        print("Opciones:")
        print("  [O] Override - Agregar de todas formas (se traslapará)")

        if sugerencias:
            print(f"  [1-{len(sugerencias)}] Usar horario sugerido")

        print("  [C] Cancelar - No agregar el evento")
        print("═" * 60)

        while True:
            opcion = input("\nTu elección > ").strip().upper()

            if opcion == "O":
                confirm = input("⚠️  ¿Confirmas agregar con traslape? [Y/N]: ").strip().upper()
                if confirm == "Y":
                    return "override"
            elif opcion == "C":
                return "cancelar"
            elif opcion.isdigit():
                idx = int(opcion) - 1
                if 0 <= idx < len(sugerencias):
                    return f"sugerencia:{idx}"
                else:
                    print("❌ Número inválido")
            else:
                print("❌ Opción inválida")


# Instancia global
CONFLICTOS = GestorConflictos()
