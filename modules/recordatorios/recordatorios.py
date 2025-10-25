#modules/recordatorios/recordatorios.py

from core.memory import Memory
from core.context.logs import BITACORA
from core.context.global_session import SESSION
from datetime import datetime

class Recordatorios:
    def __init__(self):
        self.memoria = Memory()
        self.etiquetas_validas = ["urgente", "importante", "idea", "nota", "tarea"]

    def guardar(self, args):
        """
        Guarda un recordatorio con opciones extendidas

        Ejemplos:
            guardar "Comprar leche" nota
            guardar "Entregar proyecto" tarea 30/10/2025
            guardar "Llamar a Juan" importante 28/10/2025 14:30 prioridad=2
            guardar "Revisar código" nota prioridad=3
        """
        if not args:
            print("[LOBO] Especifica qué deseas guardar.")
            print("Uso: guardar <TEXTO> <etiqueta> [fecha] [hora] [prioridad=N]")
            return

        # Parsear argumentos
        texto_parts = []
        etiqueta = "nota"
        fecha = None
        hora = None
        prioridad = None

        i = 0
        while i < len(args):
            arg = args[i]

            # Detectar prioridad=N
            if arg.lower().startswith("prioridad="):
                try:
                    prioridad = int(arg.split("=")[1])
                    if not 1 <= prioridad <= 5:
                        print("⚠️  Prioridad debe estar entre 1 (urgente) y 5 (normal)")
                        prioridad = None
                except ValueError:
                    print(f"⚠️  Prioridad inválida: {arg}")
                i += 1
                continue

            # Detectar etiqueta
            if arg.lower() in self.etiquetas_validas:
                etiqueta = arg.lower()
                i += 1
                continue

            # Detectar fecha DD/MM/YYYY
            if "/" in arg and len(arg.split("/")) == 3:
                try:
                    datetime.strptime(arg, "%d/%m/%Y")
                    fecha = arg
                    i += 1
                    continue
                except ValueError:
                    pass

            # Detectar hora HH:MM
            if ":" in arg and len(arg.split(":")) == 2:
                try:
                    datetime.strptime(arg, "%H:%M")
                    hora = arg
                    i += 1
                    continue
                except ValueError:
                    pass

            # Si no es ninguno de los anteriores, es parte del texto
            texto_parts.append(arg)
            i += 1

        texto = " ".join(texto_parts).strip()

        if not texto:
            BITACORA.registrar("recordatorios", "guardar", "Intento de guardar texto vacío",
                               SESSION.user.username)
            print("[LOBO] El texto del recordatorio no puede estar vacío.")
            return

        # Validar: tareas DEBEN tener fecha
        if etiqueta == "tarea" and not fecha:
            print("⚠️  Las tareas requieren una fecha límite.")
            print("Ejemplo: guardar \"Entregar proyecto\" tarea 30/10/2025")
            return

        # Guardar en memoria
        nota = self.memoria.remember(
            content=texto,
            mem_type=etiqueta,
            fecha_limite=fecha,
            hora_limite=hora,
            prioridad=prioridad,
            usuario=SESSION.user.username if SESSION.user else None
        )

        # Mensaje de confirmación
        msg = f"[LOBO] ✅ Recordatorio guardado como '{etiqueta}': \"{texto}\""
        if fecha:
            msg += f"\n   📅 Vence: {fecha}"
            if hora:
                msg += f" a las {hora}"
        if prioridad:
            msg += f"\n   🎯 Prioridad: {prioridad}"

        print(msg)

        BITACORA.registrar("recordatorios", "guardar", f"Guardado ID {nota.id}",
                           SESSION.user.username)

    def recordar(self, args):
        """
        Muestra recordatorios con filtros

        Ejemplos:
            recordar                    # Todos los pendientes
            recordar urgente            # Solo urgentes pendientes
            recordar vencidos           # Solo vencidos
            recordar proximos 7         # Que vencen en próximos 7 días
            recordar completadas        # Historial de completadas
            recordar prioridad 1 2      # Prioridad 1 y 2
        """
        SESSION.assert_admin()

        # Sin argumentos: mostrar todos los pendientes
        if not args:
            notas = self.memoria.recall(estado="pendiente")
            self._mostrar_recordatorios(notas, "Recordatorios pendientes")
            return

        comando = args[0].lower()

        # Filtrar por etiqueta
        if comando in self.etiquetas_validas:
            notas = self.memoria.recall(mem_type=comando, estado="pendiente")
            self._mostrar_recordatorios(notas, f"Recordatorios '{comando}' pendientes")

        # Vencidos
        elif comando == "vencidos":
            notas = self.memoria.recall_vencidos()
            self._mostrar_recordatorios(notas, "⚠️  Recordatorios VENCIDOS", destacar_vencidos=True)

        # Próximos N días
        elif comando == "proximos":
            dias = int(args[1]) if len(args) > 1 else 3
            notas = self.memoria.recall_proximos(dias)
            self._mostrar_recordatorios(notas, f"Recordatorios próximos {dias} días")

        # Completadas
        elif comando in ["completadas", "completados"]:
            notas = self.memoria.recall(estado="completada", incluir_completadas=True)
            self._mostrar_recordatorios(notas, "✅ Historial de completadas")

        # Por prioridad
        elif comando == "prioridad":
            if len(args) < 3:
                print("[LOBO] Uso: recordar prioridad <MIN> <MAX>")
                print("Ejemplo: recordar prioridad 1 2")
                return
            prioridad_min = int(args[1])
            prioridad_max = int(args[2])
            notas = self.memoria.recall_por_prioridad(prioridad_min, prioridad_max)
            self._mostrar_recordatorios(notas, f"Recordatorios prioridad {prioridad_min}-{prioridad_max}")

        # Todas (incluir completadas y canceladas)
        elif comando == "todas" or comando == "todos":
            notas = self.memoria.recall(incluir_completadas=True)
            self._mostrar_recordatorios(notas, "Todos los recordatorios")

        else:
            print(f"❌ Comando no reconocido: {comando}")
            print("\nOpciones válidas:")
            print("  recordar [etiqueta]       - urgente, importante, tarea, nota, idea")
            print("  recordar vencidos         - Recordatorios vencidos")
            print("  recordar proximos [dias]  - Próximos N días (default: 3)")
            print("  recordar completadas      - Historial de completadas")
            print("  recordar prioridad MIN MAX - Por rango de prioridad")
            print("  recordar todas            - Todos sin filtro")

        BITACORA.registrar("recordatorios", "recordar", f"Consulta: {' '.join(args)}",
                           SESSION.user.username)

    def _mostrar_recordatorios(self, notas, titulo, destacar_vencidos=False):
        """Función auxiliar para mostrar recordatorios formateados"""
        if not notas:
            print(f"[LOBO] {titulo}: No hay registros.")
            return

        print(f"\n🐺 [LOBO] {titulo}:\n")

        from datetime import date
        hoy = date.today()

        for nota in reversed(notas[-20:]):  # Últimos 20
            # Emoji según tipo
            emoji_map = {
                "urgente": "⚠️ ",
                "importante": "📌",
                "tarea": "✅",
                "nota": "📝",
                "idea": "💡"
            }
            emoji = emoji_map.get(nota.type, "•")

            # Color según estado
            estado_str = ""
            if nota.estado == "completada":
                estado_str = "[✓]"
            elif nota.estado == "cancelada":
                estado_str = "[✗]"

            # Información de prioridad
            prioridad_str = f"[P:{nota.prioridad}]" if nota.prioridad else ""

            # Fecha y hora
            fecha_str = ""
            if nota.fecha_limite:
                dias_restantes = (nota.fecha_limite - hoy).days

                if destacar_vencidos and dias_restantes < 0:
                    fecha_str = f"🔴 VENCIDO hace {abs(dias_restantes)} días"
                elif dias_restantes < 0:
                    fecha_str = f"(Vencido)"
                elif dias_restantes == 0:
                    fecha_str = f"📅 ¡HOY!"
                elif dias_restantes == 1:
                    fecha_str = f"📅 Mañana"
                elif dias_restantes <= 3:
                    fecha_str = f"📅 En {dias_restantes} días"
                else:
                    fecha_str = f"📅 {nota.fecha_limite.strftime('%d/%m/%Y')}"

                if nota.hora_limite:
                    fecha_str += f" a las {nota.hora_limite.strftime('%H:%M')}"

            # Línea completa
            print(f" {emoji} {estado_str}{prioridad_str} [ID:{nota.id}] {nota.content}")
            if fecha_str:
                print(f"    {fecha_str}")
            if nota.creado_por and nota.creado_por != "system":
                print(f"    👤 Por: {nota.creado_por}")
            print()

    def completar(self, args):
        """
        Marca recordatorios como completados

        Ejemplos:
            completar 123               # Por ID
            completar "proyecto" tarea  # Por búsqueda
        """
        SESSION.assert_admin()

        if not args:
            print("[LOBO] Uso: completar <ID> | completar <TEXTO> <etiqueta>")
            return

        # Intentar por ID primero
        if len(args) == 1 and args[0].isdigit():
            note_id = int(args[0])
            nota = self.memoria.obtener_por_id(note_id)

            if not nota:
                print(f"❌ No se encontró recordatorio con ID {note_id}")
                return

            if nota.estado == "completada":
                print(f"⚠️  El recordatorio ya está completado.")
                return

            print(f"📝 Recordatorio: \"{nota.content}\"")
            confirm = input("¿Marcar como completado? [Y/N]: ").strip().upper()

            if confirm == "Y":
                if self.memoria.completar(note_id):
                    print(f"✅ Recordatorio marcado como completado.")
                    BITACORA.registrar("recordatorios", "completar", f"ID {note_id}",
                                       SESSION.user.username)
                else:
                    print("❌ Error al completar recordatorio.")
            else:
                print("❎ Acción cancelada.")
            return

        # Búsqueda por texto + etiqueta
        if len(args) < 2:
            print("[LOBO] Para búsqueda por texto usa: completar <TEXTO> <etiqueta>")
            return

        etiqueta = args[-1].lower()
        if etiqueta not in self.etiquetas_validas:
            print(f"❌ Etiqueta inválida. Usa: {', '.join(self.etiquetas_validas)}")
            return

        texto = " ".join(args[:-1]).strip()
        coincidencias = self.memoria.buscar_por_contenido(texto, etiqueta, estado="pendiente")

        if not coincidencias:
            print("⚠️  No se encontraron recordatorios pendientes con esa descripción.")
            return

        if len(coincidencias) == 1:
            nota = coincidencias[0]
            print(f"📝 Recordatorio: \"{nota.content}\"")
            confirm = input("¿Marcar como completado? [Y/N]: ").strip().upper()

            if confirm == "Y":
                if self.memoria.completar(nota.id):
                    print(f"✅ Recordatorio completado.")
                else:
                    print("❌ Error al completar.")
            else:
                print("❎ Cancelado.")
        else:
            print("🔍 Se encontraron varios recordatorios:")
            for nota in coincidencias:
                fecha_str = f" - Vence: {nota.fecha_limite.strftime('%d/%m/%Y')}" if nota.fecha_limite else ""
                print(f"  [ID: {nota.id}] {nota.content}{fecha_str}")

            try:
                id_elegido = int(input("\nID a completar: ").strip())
                if self.memoria.completar(id_elegido):
                    print(f"✅ Recordatorio completado.")
                else:
                    print("❌ Error al completar.")
            except ValueError:
                print("❌ ID inválido.")

    def eliminar(self, args):
        """
        Elimina recordatorios (permanente)

        Ejemplos:
            eliminar_recuerdo 123               # Por ID
            eliminar_recuerdo "proyecto" tarea  # Por búsqueda
        """
        SESSION.assert_admin()

        if not args:
            print("[LOBO] Uso: eliminar_recuerdo <ID> | eliminar_recuerdo <TEXTO> <ETIQUETA>")
            return

        # Intentar por ID primero
        if len(args) == 1 and args[0].isdigit():
            note_id = int(args[0])
            nota = self.memoria.obtener_por_id(note_id)

            if not nota:
                print(f"❌ No se encontró recordatorio con ID {note_id}")
                return

            print(f"⚠️  ¿Estás seguro que deseas ELIMINAR: \"{nota.content}\"?")
            confirm = input("[Y/N]: ").strip().upper()

            if confirm == "Y":
                if self.memoria.eliminar_por_id(note_id):
                    print(f"🗑️  Recordatorio eliminado.")
                else:
                    print("❌ Error al eliminar.")
            else:
                print("❎ Cancelado.")
            return

        # Búsqueda por texto + etiqueta
        etiqueta = args[-1].lower()
        if etiqueta not in self.etiquetas_validas:
            BITACORA.registrar("recordatorios", "eliminar", "Etiqueta inválida",
                               SESSION.user.username)
            print("[LOBO] Debes especificar una etiqueta válida al final.")
            return

        texto = " ".join(args[:-1]).strip()

        if len(texto.split()) < 1:
            BITACORA.registrar("recordatorios", "buscar", "Texto insuficiente",
                               SESSION.user.username)
            print("[LOBO] Escribe al menos 1 palabra para buscar.")
            return

        coincidencias = self.memoria.buscar_por_contenido(texto, etiqueta)

        if not coincidencias:
            BITACORA.registrar("recordatorios", "buscar fallido",
                               "Sin resultados", SESSION.user.username)
            print("⚠️  No se encontraron recordatorios con esa descripción y etiqueta.")
            return

        # Una sola coincidencia
        if len(coincidencias) == 1:
            seleccionado = coincidencias[0]
            print(f"⚠️  ¿Estás seguro que deseas eliminar: \"{seleccionado.content}\"?")
            confirm = input("[Y/N]: ").strip().upper()

            if confirm != "Y":
                BITACORA.registrar("recordatorios", "cancelar",
                                   "Eliminación cancelada", SESSION.user.username)
                print("❎ Acción cancelada.")
                return

            if self.memoria.eliminar_por_id(seleccionado.id):
                BITACORA.registrar("recordatorios", "eliminar",
                                   f"ID {seleccionado.id}", SESSION.user.username)
                print(f"🗑️  Recordatorio eliminado con éxito.")
            else:
                BITACORA.registrar("recordatorios", "error",
                                   "Error al eliminar", SESSION.user.username)
                print("❌ Ocurrió un error al eliminar el recordatorio.")
            return

        # Múltiples coincidencias
        print("🔍 Se encontraron varios recordatorios:")
        for nota in coincidencias:
            fecha = nota.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            fecha_lim = f" - Vence: {nota.fecha_limite.strftime('%d/%m/%Y')}" if nota.fecha_limite else ""
            print(f"[ID: {nota.id}] [{nota.type.upper()}] {fecha} → {nota.content}{fecha_lim}")

        print("\nEscribe el ID del recordatorio que deseas eliminar.")
        try:
            id_elegido = int(input("ID a eliminar: ").strip())
        except ValueError:
            print("❌ ID inválido.")
            return

        seleccionado = next((n for n in coincidencias if n.id == id_elegido), None)

        if not seleccionado:
            print("❌ No se encontró un recordatorio con ese ID en los resultados.")
            return

        print(f"⚠️  ¿Estás seguro que deseas eliminar: \"{seleccionado.content}\"?")
        confirm = input("[Y/N]: ").strip().upper()

        if confirm != "Y":
            print("❎ Acción cancelada.")
            return

        if self.memoria.eliminar_por_id(id_elegido):
            print(f"🗑️  Recordatorio eliminado con éxito.")
            BITACORA.registrar("recordatorios", "eliminar",
                               f"ID {id_elegido}", SESSION.user.username)
        else:
            print("❌ Ocurrió un error al eliminar el recordatorio.")

    def menu_vencidos(self):
        """
        Menú interactivo para manejar recordatorios vencidos
        """
        vencidos = self.memoria.recall_vencidos()

        if not vencidos:
            return  # No hay vencidos, salir silenciosamente

        print("\n" + "⚠️ " * 20)
        print(f"   ¡ATENCIÓN! Tienes {len(vencidos)} recordatorio(s) vencido(s)")
        print("⚠️ " * 20 + "\n")

        from datetime import date
        hoy = date.today()

        for i, nota in enumerate(vencidos, 1):
            dias_vencido = (hoy - nota.fecha_limite).days
            emoji = "⚠️ " if nota.type == "urgente" else "📌" if nota.type == "importante" else "✅"

            print(f"{i}. [P:{nota.prioridad}] {emoji} {nota.content}")
            print(f"   🔴 Vencido hace {dias_vencido} día(s) - {nota.fecha_limite.strftime('%d/%m/%Y')}")
            if nota.hora_limite:
                print(f"   ⏰ Hora: {nota.hora_limite.strftime('%H:%M')}")
            print()

        print("Opciones:")
        print("  [C] Completar todas")
        print("  [V] Ver detalles (abrir recordar vencidos)")
        print("  [I] Ignorar por ahora")
        print("  [R] Reprogramar (seleccionar por ID)")
        print()

        opcion = input("Tu elección > ").strip().upper()

        if opcion == "C":
            confirm = input(f"¿Marcar las {len(vencidos)} tareas como completadas? [Y/N]: ").strip().upper()
            if confirm == "Y":
                for nota in vencidos:
                    self.memoria.completar(nota.id)
                print(f"✅ {len(vencidos)} recordatorios marcados como completados.")
                BITACORA.registrar("recordatorios", "completar_multiple",
                                   f"{len(vencidos)} vencidos", SESSION.user.username)

        elif opcion == "V":
            self.recordar(["vencidos"])

        elif opcion == "I":
            print("❎ Recordatorios vencidos ignorados por ahora.")

        elif opcion == "R":
            print("\n🔍 Recordatorios vencidos:")
            for nota in vencidos:
                print(f"  [ID: {nota.id}] {nota.content}")

            try:
                id_elegido = int(input("\nID a reprogramar: ").strip())
                nota = self.memoria.obtener_por_id(id_elegido)

                if nota and nota in vencidos:
                    nueva_fecha = input("Nueva fecha (DD/MM/YYYY): ").strip()
                    nueva_hora = input("Nueva hora (HH:MM) [opcional]: ").strip() or None

                    # Actualizar (necesitarías agregar métdo update en Memory)
                    print(f"⚠️  Función de reprogramación pendiente de implementar.")
                    print(f"   Por ahora, elimina el recordatorio y créalo de nuevo.")
                else:
                    print("❌ ID inválido o no está en la lista de vencidos.")
            except ValueError:
                print("❌ ID inválido.")

        else:
            print("❌ Opción no válida.")
