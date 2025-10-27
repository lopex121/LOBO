# modules/agenda/agenda.py
"""
API de Agenda con soporte completo para:
- Eventos recurrentes (Opción C: Maestro + Instancias)
- Validación de conflictos
- Alarmas automáticas
- IDs cortos (8 caracteres)
"""

from modules.agenda import agenda_logics as logics
from modules.agenda.agenda_logics_recurrentes import (
    crear_evento_recurrente, editar_instancia, editar_serie,
    eliminar_instancia, eliminar_serie, obtener_info_serie
)
from modules.agenda.conflictos import CONFLICTOS
from core.db.schema import RecurrenciaEnum
from datetime import date, datetime, timedelta
from core.context.logs import BITACORA
from core.context.global_session import SESSION


class AgendaAPI:
    def __init__(self):
        pass

    def agregar_evento(self, args: list):
        """
        Agrega evento con validación de conflictos y soporte para recurrentes

        Uso:
            agregar_evento "NOMBRE" YYYY-MM-DD HH:MM HH:MM "DESC" "recurrencia" "tipo" "etiquetas"

        Ejemplos:
            agregar_evento "Clase de Física" 2025-10-28 09:00 10:30 "Modelación" unico clase
            agregar_evento "Gimnasio" 2025-10-28 18:00 19:00 "" semanal deporte
        """
        if len(args) < 4:
            return ("[AGENDA] Uso: agregar_evento \"NOMBRE\" YYYY-MM-DD HH:MM HH:MM "
                    "[\"DESCRIPCION\"] [recurrencia] [tipo] [etiquetas_csv]")

        nombre = args[0]
        fecha = args[1]
        hora_inicio = args[2]
        hora_fin = args[3]
        descripcion = args[4] if len(args) > 4 else ""
        recurrencia_str = args[5] if len(args) > 5 else "unico"
        tipo_evento = args[6] if len(args) > 6 else "personal"
        etiquetas = args[7].split(",") if len(args) > 7 else []

        # Validar recurrencia
        try:
            recurrencia = RecurrenciaEnum(recurrencia_str)
        except ValueError:
            return f"[AGENDA] ❌ Recurrencia inválida: {recurrencia_str}. Usa: unico, diario, semanal, mensual"

        # Validar tipo de evento
        tipos_validos = ["clase", "trabajo", "personal", "deporte", "estudio", "reunion"]
        if tipo_evento not in tipos_validos:
            return f"[AGENDA] ⚠️  Tipo '{tipo_evento}' no reconocido. Usando 'personal'. Tipos válidos: {', '.join(tipos_validos)}"
            tipo_evento = "personal"

        # Parsear fecha y horas
        try:
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            hora_inicio_obj = datetime.strptime(hora_inicio, "%H:%M").time()
            hora_fin_obj = datetime.strptime(hora_fin, "%H:%M").time()
        except ValueError as e:
            return f"[AGENDA] ❌ Formato inválido: {e}"

        # === VALIDACIÓN DE CONFLICTOS ===
        conflictos = CONFLICTOS.detectar_conflictos(fecha_obj, hora_inicio_obj, hora_fin_obj)

        if conflictos:
            # Calcular duración del evento
            duracion = (datetime.combine(fecha_obj, hora_fin_obj) -
                        datetime.combine(fecha_obj, hora_inicio_obj)).seconds // 60

            # Mostrar conflictos y pedir decisión
            decision = CONFLICTOS.mostrar_conflictos_y_sugerencias(
                fecha_obj, hora_inicio_obj, hora_fin_obj, conflictos
            )

            if decision == "cancelar":
                BITACORA.registrar("agenda", "agregar_cancelado",
                                   f"Usuario canceló por conflicto: {nombre}",
                                   SESSION.user.username)
                return "[AGENDA] ❎ Evento cancelado por el usuario."

            elif decision == "override":
                BITACORA.registrar("agenda", "agregar_override",
                                   f"Usuario forzó evento con conflicto: {nombre}",
                                   SESSION.user.username)
                print("\n⚠️  Agregando evento con traslape...\n")
                # Continuar con la creación

            elif decision.startswith("sugerencia:"):
                # Usuario eligió horario sugerido
                idx = int(decision.split(":")[1])
                sugerencias = CONFLICTOS.sugerir_horarios(fecha_obj, duracion, conflictos)

                if idx < len(sugerencias):
                    hora_inicio_obj = sugerencias[idx]['inicio']
                    hora_fin_obj = sugerencias[idx]['fin']
                    print(
                        f"\n✅ Usando horario sugerido: {hora_inicio_obj.strftime('%H:%M')} - {hora_fin_obj.strftime('%H:%M')}\n")
                    BITACORA.registrar("agenda", "agregar_horario_alternativo",
                                       f"Usuario usó sugerencia: {nombre}",
                                       SESSION.user.username)

        # === CREAR EVENTO ===
        try:
            if recurrencia == RecurrenciaEnum.unico:
                # Evento único (sin recurrencia)
                evento = logics.crear_evento_db(
                    nombre=nombre,
                    descripcion=descripcion,
                    fecha_inicio=fecha_obj,
                    hora_inicio=hora_inicio_obj,
                    hora_fin=hora_fin_obj,
                    recurrencia=recurrencia,
                    etiquetas=etiquetas,
                    tipo_evento=tipo_evento
                )

                # Pintar en Sheets
                try:
                    logics.pintar_evento_sheets(evento)
                except Exception as e:
                    BITACORA.registrar("agenda", "error_sheets",
                                       f"Error al pintar en Sheets: {e}",
                                       SESSION.user.username)
                    return f"[AGENDA] ✅ Evento creado (id={evento.id}) pero error en Sheets: {e}"

                # Programar alarma automática
                if evento.alarma_activa:
                    self._programar_alarma_automatica(evento)

                BITACORA.registrar("agenda", "agregar", f"Evento único: {nombre}",
                                   SESSION.user.username)

                return f"[AGENDA] ✅ Evento creado y pintado (id={evento.id})"

            else:
                # Evento recurrente - usar sistema Maestro + Instancias
                resultado = crear_evento_recurrente(
                    nombre=nombre,
                    descripcion=descripcion,
                    fecha_inicio=fecha_obj,
                    hora_inicio=hora_inicio_obj,
                    hora_fin=hora_fin_obj,
                    recurrencia=recurrencia,
                    etiquetas=etiquetas,
                    tipo_evento=tipo_evento,
                    alarma_minutos=5,
                    semanas_futuras=12
                )

                maestro = resultado['maestro']
                instancias = resultado['instancias']

                # Pintar todas las instancias en Sheets
                pintadas = 0
                for instancia in instancias:
                    try:
                        logics.pintar_evento_sheets(instancia)
                        pintadas += 1

                        # Programar alarma para cada instancia
                        if instancia.alarma_activa:
                            self._programar_alarma_automatica(instancia)
                    except Exception as e:
                        BITACORA.registrar("agenda", "error_sheets",
                                           f"Error al pintar instancia: {e}",
                                           SESSION.user.username)

                BITACORA.registrar("agenda", "agregar_serie",
                                   f"Serie creada: {nombre} ({len(instancias)} instancias)",
                                   SESSION.user.username)

                return (f"[AGENDA] ✅ Serie creada:\n"
                        f"   • Maestro: {maestro.id}\n"
                        f"   • {len(instancias)} instancias generadas ({pintadas} pintadas en Sheets)\n"
                        f"   • Recurrencia: {recurrencia.value}")

        except Exception as e:
            BITACORA.registrar("agenda", "error", f"Error al crear evento: {e}",
                               SESSION.user.username)
            return f"[AGENDA] ❌ Error: {e}"

    def eliminar_evento(self, args: list):
        """
        Elimina evento con soporte para series (acepta ID corto)

        Uso:
            eliminar_evento <id>      # ID completo o primeros 8 caracteres
        """
        if not args:
            return "[AGENDA] Uso: eliminar_evento <id>"

        evento_id = args[0]

        # Buscar evento por ID flexible (completo o parcial)
        evento = logics.get_evento_by_id_flexible(evento_id)

        if not evento:
            return "[AGENDA] ❌ Evento no encontrado."

        # Usar el ID completo del evento encontrado
        evento_id_completo = evento.id

        # Guardar info del evento ANTES de cualquier operación
        evento_nombre = evento.nombre
        evento_descripcion = evento.descripcion
        evento_fecha = evento.fecha_inicio
        evento_hora_inicio = evento.hora_inicio
        evento_hora_fin = evento.hora_fin

        # Obtener información del evento
        info = obtener_info_serie(evento_id_completo)

        if not info:
            # Si obtener_info_serie falla, intentar eliminar como evento único
            print("⚠️  No se pudo determinar si es parte de una serie. Tratando como evento único...")
            ok = logics.eliminar_evento_db(evento_id_completo)
            if not ok:
                return "[AGENDA] ❌ No se pudo borrar de DB."

            # Crear objeto temporal para borrar de sheets
            from core.db.schema import Evento as EventoTemp
            evento_temp = type('obj', (object,), {
                'hora_inicio': evento_hora_inicio,
                'hora_fin': evento_hora_fin,
                'fecha_inicio': evento_fecha,
                'nombre': evento_nombre
            })()

            try:
                logics.borrar_evento_sheets(evento_temp)
            except Exception as e:
                return f"[AGENDA] ⚠️  Borrado de DB OK, error en Sheets: {e}"

            BITACORA.registrar("agenda", "eliminar", f"Evento: {evento_nombre}",
                               SESSION.user.username)
            return "[AGENDA] ✅ Evento eliminado."

        if not info:
            return "[AGENDA] ❌ Evento no encontrado."

        evento = logics.get_evento_by_id(evento_id)

        if not info:
            return "[AGENDA] ❌ Error al obtener información del evento."

        if not info['es_serie']:
            # Evento único - eliminar normal
            ok = logics.eliminar_evento_db(evento_id_completo)
            if not ok:
                return "[AGENDA] ❌ No se pudo borrar de DB."

            # Crear objeto temporal para borrar de sheets (ya que evento fue eliminado de DB)
            evento_temp = type('obj', (object,), {
                'hora_inicio': evento_hora_inicio,
                'hora_fin': evento_hora_fin,
                'fecha_inicio': evento_fecha,
                'nombre': evento_nombre
            })()

            try:
                logics.borrar_evento_sheets(evento_temp)
            except Exception as e:
                return f"[AGENDA] ⚠️  Borrado de DB OK, error en Sheets: {e}"

            BITACORA.registrar("agenda", "eliminar", f"Evento único: {evento_nombre}",
                               SESSION.user.username)
            return "[AGENDA] ✅ Evento eliminado."

        # Es parte de una serie - preguntar qué eliminar
        print("\n" + "⚠️ " * 20)
        print("   Este evento es parte de una serie recurrente")
        print("⚠️ " * 20 + "\n")

        print(f"📅 Evento: {evento_nombre}")
        print(f"🔁 Recurrencia: {info['recurrencia']}")
        print(f"📊 Instancias totales: {info['instancias_totales']}")
        print(f"📅 Instancias futuras: {info['instancias_futuras']}")

        if info['es_maestro']:
            print("\n⚠️  Estás intentando eliminar el EVENTO MAESTRO")

        print("\nOpciones:")
        if not info['es_maestro']:
            print("  [1] Eliminar solo esta instancia")
            print("  [2] Eliminar esta y todas las futuras")
        print("  [3] Eliminar TODA la serie (pasadas y futuras)")
        print("  [C] Cancelar")

        opcion = input("\nTu elección > ").strip().upper()

        if opcion == "C":
            return "[AGENDA] ❎ Eliminación cancelada."

        try:
            if opcion == "1" and not info['es_maestro']:
                # Eliminar solo esta instancia
                eliminar_instancia(evento_id_completo)

                # Usar datos guardados para borrar de sheets
                evento_temp = type('obj', (object,), {
                    'hora_inicio': evento_hora_inicio,
                    'hora_fin': evento_hora_fin,
                    'fecha_inicio': evento_fecha,
                    'nombre': evento_nombre
                })()

                try:
                    logics.borrar_evento_sheets(evento_temp)
                except Exception as e:
                    pass

                BITACORA.registrar("agenda", "eliminar_instancia",
                                   f"Instancia eliminada: {evento_nombre}",
                                   SESSION.user.username)
                return "[AGENDA] ✅ Instancia eliminada."

            elif opcion == "2" and not info['es_maestro']:
                # Eliminar esta y futuras
                master_id = info['master_id']
                count = eliminar_serie(master_id, incluir_pasadas=False)

                # Limpiar Sheets (refrescar completo)
                # All: En Fase 2 implementaremos limpieza selectiva

                BITACORA.registrar("agenda", "eliminar_futuras",
                                   f"Eliminadas {count} instancias futuras",
                                   SESSION.user.username)
                return f"[AGENDA] ✅ Eliminadas {count} instancias futuras."

            elif opcion == "3":
                # Eliminar toda la serie
                master_id = info['master_id'] if not info['es_maestro'] else evento_id_completo
                count = eliminar_serie(master_id, incluir_pasadas=True)

                BITACORA.registrar("agenda", "eliminar_serie",
                                   f"Serie completa eliminada: {count} instancias",
                                   SESSION.user.username)
                return f"[AGENDA] ✅ Serie eliminada: {count} instancias."

            else:
                return "[AGENDA] ❌ Opción inválida."

        except Exception as e:
            return f"[AGENDA] ❌ Error: {e}"

    def editar_evento(self, args: list):
        """
        Edita evento con soporte para series (acepta ID corto)

        Uso:
            editar_evento <id> key=value key=value ...

        Ejemplo:
            editar_evento 5776c444 nombre="Nueva clase" hora_inicio=10:00
        """
        if not args:
            return "[AGENDA] Uso: editar_evento <id> key=value ..."

        evento_id = args[0]
        kvs = args[1:]

        if not kvs:
            return "[AGENDA] Especifica al menos un campo a editar (key=value)"

        # Buscar evento por ID flexible
        old = logics.get_evento_by_id_flexible(evento_id)

        if not old:
            return "[AGENDA] ❌ Evento no encontrado."

        # Usar ID completo
        evento_id_completo = old.id

        # Parsear actualizaciones
        updates = {}
        for kv in kvs:
            if "=" not in kv:
                continue
            k, v = kv.split("=", 1)

            # Limpiar comillas
            v = v.strip('"').strip("'")

            # Parsear según el campo
            if k in ["hora_inicio", "hora_fin"]:
                try:
                    updates[k] = datetime.strptime(v, "%H:%M").time()
                except ValueError:
                    return f"[AGENDA] ❌ Formato inválido para {k}: usa HH:MM"

            elif k == "fecha_inicio":
                try:
                    updates[k] = datetime.strptime(v, "%Y-%m-%d").date()
                except ValueError:
                    return f"[AGENDA] ❌ Formato inválido para fecha: usa YYYY-MM-DD"

            elif k == "etiquetas":
                updates[k] = v.split(",")

            elif k == "tipo_evento":
                tipos_validos = ["clase", "trabajo", "personal", "deporte", "estudio", "reunion"]
                if v not in tipos_validos:
                    return f"[AGENDA] ❌ Tipo inválido. Usa: {', '.join(tipos_validos)}"
                updates[k] = v

            elif k in ["alarma_minutos"]:
                try:
                    updates[k] = int(v)
                except ValueError:
                    return f"[AGENDA] ❌ {k} debe ser un número"

            elif k in ["alarma_activa"]:
                updates[k] = v.lower() in ["true", "1", "yes", "si"]

            else:
                updates[k] = v

        # Obtener información del evento
        info = obtener_info_serie(evento_id_completo)

        if not info:
            return "[AGENDA] ❌ Evento no encontrado."

        if not info['es_serie']:
            # Evento único - editar normal
            try:
                new = logics.editar_evento_db(evento_id_completo, **updates)

                # Actualizar en Sheets
                try:
                    logics.actualizar_evento_sheets(old, new)
                except Exception as e:
                    return f"[AGENDA] ⚠️  Evento editado en DB pero error en Sheets: {e}"

                BITACORA.registrar("agenda", "editar", f"Evento único: {new.nombre}",
                                   SESSION.user.username)
                return "[AGENDA] ✅ Evento actualizado."

            except Exception as e:
                return f"[AGENDA] ❌ Error: {e}"

        # Es parte de una serie - preguntar qué editar
        print("\n" + "⚠️ " * 20)
        print("   Este evento es parte de una serie recurrente")
        print("⚠️ " * 20 + "\n")

        print(f"📅 Evento: {old.nombre}")
        print(f"🔁 Recurrencia: {info['recurrencia']}")

        if info['modificado_manualmente']:
            print("⚠️  Esta instancia ya fue modificada manualmente")

        print("\nOpciones:")
        if not info['es_maestro']:
            print("  [1] Editar solo esta instancia")
            print("  [2] Editar TODAS las instancias futuras no modificadas")
        else:
            print("  [2] Editar TODAS las instancias futuras no modificadas")
        print("  [C] Cancelar")

        opcion = input("\nTu elección > ").strip().upper()

        if opcion == "C":
            return "[AGENDA] ❎ Edición cancelada."

        try:
            if opcion == "1" and not info['es_maestro']:
                # Editar solo esta instancia
                new = editar_instancia(evento_id_completo, **updates)

                try:
                    logics.actualizar_evento_sheets(old, new)
                except Exception as e:
                    pass

                BITACORA.registrar("agenda", "editar_instancia",
                                   f"Instancia editada: {new.nombre}",
                                   SESSION.user.username)
                return "[AGENDA] ✅ Instancia editada (desvinculada de la serie)."

            elif opcion == "2":
                # Editar todas las futuras
                master_id = info['master_id'] if not info['es_maestro'] else evento_id_completo
                resultado = editar_serie(master_id, **updates)

                # All: Actualizar Sheets (Fase 2)

                BITACORA.registrar("agenda", "editar_serie",
                                   f"Serie editada: {resultado['instancias_actualizadas']} instancias",
                                   SESSION.user.username)
                return f"[AGENDA] ✅ Serie actualizada: {resultado['instancias_actualizadas']} instancias modificadas."

            else:
                return "[AGENDA] ❌ Opción inválida."

        except Exception as e:
            return f"[AGENDA] ❌ Error: {e}"

    def ver_eventos(self, args: list):
        """
        Muestra eventos en formato lista

        Uso:
            ver_eventos [dia|semana|mes] [YYYY-MM-DD]
            ver_eventos semana +1    (próxima semana)
            ver_eventos semana -2    (hace 2 semanas)
        """
        from datetime import datetime, timedelta
        import calendar

        hoy = date.today()
        modo = "semana"  # Default: semana actual
        fecha_base = hoy

        if args:
            primer_arg = args[0].lower()

            # Detectar modo
            if primer_arg in ["dia", "semana", "mes"]:
                modo = primer_arg

                # Ver si hay navegación relativa (+1, -1, etc)
                if len(args) > 1:
                    if args[1].startswith("+") or args[1].startswith("-"):
                        offset = int(args[1])
                        if modo == "dia":
                            fecha_base = hoy + timedelta(days=offset)
                        elif modo == "semana":
                            fecha_base = hoy + timedelta(weeks=offset)
                        elif modo == "mes":
                            # Sumar/restar meses
                            mes_actual = hoy.month + offset
                            año = hoy.year
                            while mes_actual < 1:
                                mes_actual += 12
                                año -= 1
                            while mes_actual > 12:
                                mes_actual -= 12
                                año += 1
                            fecha_base = hoy.replace(year=año, month=mes_actual, day=1)
                    else:
                        # Fecha específica
                        try:
                            fecha_base = datetime.strptime(args[1], "%Y-%m-%d").date()
                        except ValueError:
                            return "[AGENDA] ❌ Formato de fecha inválido. Usa YYYY-MM-DD"
            else:
                # Solo viene fecha
                try:
                    fecha_base = datetime.strptime(primer_arg, "%Y-%m-%d").date()
                    modo = "dia"
                except ValueError:
                    return "[AGENDA] ❌ Formato inválido. Usa: ver_eventos [dia|semana|mes] [fecha o +/-N]"

        # Calcular rango según modo
        if modo == "dia":
            inicio = fecha_base
            fin = fecha_base
        elif modo == "semana":
            # Lunes de esa semana
            inicio = fecha_base - timedelta(days=fecha_base.weekday())
            fin = inicio + timedelta(days=6)
        elif modo == "mes":
            inicio = fecha_base.replace(day=1)
            ultimo_dia = calendar.monthrange(fecha_base.year, fecha_base.month)[1]
            fin = fecha_base.replace(day=ultimo_dia)

        # Obtener eventos
        eventos = logics.listar_eventos_por_rango(inicio.isoformat(), fin.isoformat())

        if not eventos:
            return f"[AGENDA] No hay eventos en {modo} ({inicio} → {fin})."

        # Ordenar por fecha y hora
        eventos = sorted(eventos, key=lambda e: (e.fecha_inicio, e.hora_inicio))

        # Formatear salida tipo lista
        lines = []
        lines.append(f"\n📅 Eventos de {modo}: {inicio.strftime('%d/%m/%Y')} - {fin.strftime('%d/%m/%Y')}")
        lines.append("─" * 70)

        fecha_actual = None
        for ev in eventos:
            # Encabezado de fecha si cambia
            if ev.fecha_inicio != fecha_actual:
                fecha_actual = ev.fecha_inicio
                try:
                    dia_nombre = fecha_actual.strftime("%A, %d de %B").capitalize()
                except:
                    dia_nombre = fecha_actual.strftime("%Y-%m-%d")
                lines.append(f"\n{dia_nombre}:")

            # Emoji según tipo
            emojis = {
                "clase": "📚",
                "trabajo": "💼",
                "personal": "🏠",
                "deporte": "🏋️",
                "estudio": "📖",
                "reunion": "👥"
            }
            emoji = emojis.get(ev.tipo_evento, "📌")

            # Indicador de serie
            info = obtener_info_serie(ev.id)
            serie_str = ""
            if info and info['es_serie']:
                if info['modificado_manualmente']:
                    serie_str = " [Serie*]"  # Modificada manualmente
                else:
                    serie_str = f" [Serie: {info['recurrencia']}]"

            # ID corto (primeros 8 caracteres)
            id_corto = ev.id[:8]

            hora_str = f"{ev.hora_inicio.strftime('%H:%M')}-{ev.hora_fin.strftime('%H:%M')}"
            lines.append(f"  {emoji} {hora_str}  {ev.nombre}{serie_str}")
            lines.append(f"      ID: {id_corto}")

            if ev.descripcion:
                lines.append(f"      └─ {ev.descripcion[:60]}")

        lines.append("\n" + "─" * 70)

        return "\n".join(lines)

    def buscar_evento(self, args: list):
        """Busca eventos por texto"""
        if not args:
            return "[AGENDA] Uso: buscar_evento <texto>"

        q = " ".join(args)
        eventos = logics.buscar_eventos_db(q)

        if not eventos:
            return "[AGENDA] No se encontró nada."

        lines = [f"\n🔍 Resultados para '{q}':"]
        for e in eventos:
            lines.append(f"  • {e.id[:8]} | {e.fecha_inicio} {e.hora_inicio.strftime('%H:%M')} | {e.nombre}")

        return "\n".join(lines)

    def clear_sheets(self, args: list):
        """Limpia y refresca completamente los Sheets"""
        try:
            logics.clear_sheets()
            return "[AGENDA] ✅ Sheets limpiado y sincronizado."
        except Exception as e:
            return f"[AGENDA] ❌ Error: {e}"

    def importar_desde_sheets(self, args: list):
        """Importa eventos desde Sheets"""
        try:
            nuevos = logics.importar_eventos_desde_sheets()
            return f"[AGENDA] ✅ Importados {nuevos} eventos nuevos."
        except Exception as e:
            return f"[AGENDA] ❌ Error: {e}"

    def _programar_alarma_automatica(self, evento):
        """Programa alarma automática para un evento (helper interno)"""
        try:
            from modules.alarma.alarma import AlarmManager
            alarmas = AlarmManager()

            # Solo programar si la fecha es futura
            from datetime import datetime, date
            hoy = date.today()

            if evento.fecha_inicio >= hoy:
                alarmas.programar_alarma(evento.id, evento.alarma_minutos)
        except Exception as e:
            # No crítico si falla la alarma
            pass