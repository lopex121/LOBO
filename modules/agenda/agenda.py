# modules/agenda/agenda.py
from modules.agenda import agenda_logics as logics
from core.db.schema import RecurrenciaEnum
from datetime import date

class AgendaAPI:
    def __init__(self):
        pass

    # NOTA: todas las funciones reciben 'args' (lista) para ser usadas desde router
    def agregar_evento(self, args: list):
       # Uso desde LOBO (ejemplo con quotes, por eso shlex.split en router):
       # agregar_evento "Clase de Física" "Modelación" 2025-09-21 09:00 10:00 unico trabajo,estudio

        if len(args) < 4:
            return "[AGENDA] Uso: agregar_evento \"NOMBRE\" YYYY-MM-DD HH:MM HH:MM \"DESCRIPCION\" \"recurrencia\" \"etiquetas_csv\""

        nombre = args[0]
        fecha = args[1]
        hora_inicio = args[2]
        hora_fin = args[3]
        descripcion = args[4] if len(args) > 4 else ""
        recurrencia = args[5] if len(args) > 5 else "unico"
        etiquetas = args[6].split(",") if len(args) > 6 else []

        try:
            evento = logics.crear_evento_db(
                nombre=nombre,
                descripcion=descripcion,
                fecha_inicio=fecha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                recurrencia=RecurrenciaEnum(recurrencia),
                etiquetas=etiquetas
            )
        except Exception as e:
            return f"[AGENDA] Error al crear evento en DB: {e}"

        # pintar en Sheets
        try:
            logics.pintar_evento_sheets(evento)
        except Exception as e:
            # ya está en DB; si falla Sheets, informar y continuar
            return f"[AGENDA] Evento creado en DB (id={evento.id}) pero error al pintar en Sheets: {e}"

        return f"[AGENDA] Evento creado y pintado (id={evento.id})"

    def eliminar_evento(self, args: list):

       # eliminar_evento <id>

        if not args:
            return "[AGENDA] Uso: eliminar_evento <id>"

        evento_id = args[0]
        evento = logics.get_evento_by_id(evento_id)
        if not evento:
            return "[AGENDA] Evento no encontrado."

        # borrar de DB
        ok = logics.eliminar_evento_db(evento_id)
        if not ok:
            return "[AGENDA] No se pudo borrar de DB."

        # borrar de Sheets (intentar)
        try:
            logics.borrar_evento_sheets(evento)
        except Exception as e:
            return f"[AGENDA] Borrado DB correcto, pero error al borrar en Sheets: {e}"

        return "[AGENDA] Evento borrado (DB + Sheets)."

    def editar_evento(self, args: list):

        # editar_evento <id> key=value key=value ...
        # Ejemplo:
        # editar_evento <id_obtenido> (nombre="Clase Física - cambio") (hora_inicio=09:30) (hora_fin=10:30)
        # funciona tambien si se pasa un solo argumento, pero el id es escencial

        if not args:
            return "[AGENDA] Uso: editar_evento <id> key=value ..."

        evento_id = args[0]
        kvs = args[1:]
        updates = {}
        for kv in kvs:
            if "=" not in kv:
                continue
            k, v = kv.split("=", 1)
            # acepta etiquetas=tag1,tag2
            if k == "etiquetas":
                updates[k] = v.split(",")
            else:
                updates[k] = v

        old = logics.get_evento_by_id(evento_id)
        if not old:
            return "[AGENDA] Evento no encontrado."

        new = logics.editar_evento_db(evento_id, **updates)

        # actualizar en Sheets: borrar anterior y pintar nuevo
        try:
            logics.actualizar_evento_sheets(old, new)
        except Exception as e:
            return f"[AGENDA] Evento editado en DB pero error al actualizar Sheets: {e}"

        return "[AGENDA] Evento actualizado (DB + Sheets)."

    def ver_eventos(self, args: list):
        """
        ver_eventos [dia|semana|mes] [YYYY-MM-DD]
        - Si no se pasa nada: muestra eventos de HOY.
        - Si se pasa "semana YYYY-MM-DD": muestra los eventos de esa semana.
        - Si se pasa "mes YYYY-MM-DD": muestra los eventos de ese mes.
        """

        from datetime import datetime, timedelta
        import calendar

        hoy = date.today()
        modo = "dia"
        fecha_base = hoy

        if args:
            if args[0] in ["dia", "semana", "mes"]:
                modo = args[0]
                if len(args) > 1:
                    fecha_base = datetime.strptime(args[1], "%Y-%m-%d").date()
            else:
                # si solo viene una fecha, se toma como "dia"
                fecha_base = datetime.strptime(args[0], "%Y-%m-%d").date()

        # --- calcular rango de fechas según modo ---
        if modo == "dia":
            inicio = fecha_base
            fin = fecha_base
        elif modo == "semana":
            inicio = fecha_base - timedelta(days=fecha_base.weekday())  # lunes
            fin = inicio + timedelta(days=6)  # domingo
        elif modo == "mes":
            inicio = fecha_base.replace(day=1)
            ultimo_dia = calendar.monthrange(fecha_base.year, fecha_base.month)[1]
            fin = fecha_base.replace(day=ultimo_dia)
        else:
            return "[AGENDA] Uso: ver_eventos [dia|semana|mes] [YYYY-MM-DD]"

        # --- obtener eventos de DB ---
        eventos = logics.listar_eventos_por_rango(inicio.isoformat(), fin.isoformat())
        if not eventos:
            return f"[AGENDA] No hay eventos en {modo} ({inicio} → {fin})."

        # --- ordenar por hora ---
        eventos = sorted(eventos, key=lambda e: e.hora_inicio)

        # --- formatear salida ---
        lines = []
        for ev in eventos:
            lines.append(
                f"{ev.id} | {ev.fecha_inicio} {ev.hora_inicio.strftime('%H:%M')}-{ev.hora_fin.strftime('%H:%M')} "
                f"| {ev.nombre} | {','.join(ev.etiquetas or [])}"
            )
        return "\n".join(lines)

    def buscar_evento(self, args: list):
        if not args:
            return "[AGENDA] Uso: buscar_evento <texto>"
        q = " ".join(args)
        eventos = logics.buscar_eventos_db(q)
        if not eventos:
            return "[AGENDA] No se encontró nada."
        return "\n".join([f"{e.id} | {e.fecha_inicio} {e.hora_inicio} | {e.nombre}" for e in eventos])

    def clear_sheets(self, args: list):
        try:
            logics.clear_sheets()
            return "[AGENDA] Sync completo."
        except Exception as e:
            return f"[AGENDA] Error en sync: {e}"

    def importar_desde_sheets(self, args: list):
        try:
            nuevos = logics.importar_eventos_desde_sheets()
            return f"[AGENDA] Importación completada. {nuevos} eventos nuevos añadidos a la DB."
        except Exception as e:
            return f"[AGENDA] Error al importar desde Sheets: {e}"
