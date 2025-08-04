#modules/recordatorios/recordatorios.py

from core.memory import Memory
from modules.bitacora.bitacora import Bitacora
bitacora = Bitacora()
from core.context.global_session import SESSION

class Recordatorios:
    def __init__(self):
        self.memoria = Memory()

    def guardar(self, args):
        if not args:
            print("[LOBO] Especifica qué deseas guardar.")
            return

        etiquetas_validas = ["urgente", "importante", "idea", "nota"]
        posible_etiqueta = args[-1].lower()

        if posible_etiqueta in etiquetas_validas:
            etiqueta = posible_etiqueta
            texto = " ".join(args[:-1])
        else:
            etiqueta = "nota"
            texto = " ".join(args)

        if not texto.strip():
            bitacora.registrar("recordatorios", "guardar", "Se intento guardar un texto vacío"
                               , SESSION.user.username)
            print("[LOBO] El texto de la nota no puede estar vacío.")
            return

        self.memoria.remember(texto, mem_type=etiqueta)
        bitacora.registrar("recordatorios", "guardar", "Texto guardado", SESSION.user.username)
        print(f"[LOBO] Nota guardada como '{etiqueta}': “{texto}”")

    def recordar(self, args):  # <= quitamos el valor por defecto
        SESSION.assert_admin()
        tipo = None
        if args and args[0].lower() in ["urgente", "importante", "idea", "nota"]:
            tipo = args[0].lower()

        notas = self.memoria.recall(mem_type=tipo)

        if not notas:
            print("[LOBO] No hay notas registradas.")
            return

        tipo_info = f" de tipo '{tipo}'" if tipo else ""
        bitacora.registrar("recordatorios", "recordar", "Recordatorios mostrados",
                           SESSION.user.username)
        print(f"[LOBO] Últimas notas{tipo_info}:\n")

        for nota in reversed(notas[-10:]):
            fecha = nota.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f" • [{nota.type.upper()}] {fecha} → {nota.content}")

    def eliminar(self, args):
        SESSION.assert_admin()

        if not args:
            print("[LOBO] Uso: eliminar_recuerdo <TEXTO_PARCIAL> <ETIQUETA>")
            return

        etiquetas_validas = ["urgente", "importante", "idea", "nota"]
        posible_etiqueta = args[-1].lower()
        if posible_etiqueta not in etiquetas_validas:
            bitacora.registrar("recordatorios", "eliminar", "Se intento eliminar un "
                                                            "recordatorio sin especificar su etiqueta",
                               SESSION.user.username)
            print("[LOBO] Debes especificar una etiqueta válida al final.")
            return

        etiqueta = posible_etiqueta
        texto = " ".join(args[:-1]).strip()

        if len(texto.split()) < 1:
            bitacora.registrar("recordatorios", "buscar", "Se intentó eliminar un"
                                                            "recordatorio sin escribir las suficientes palabras para "
                                                            "buscarlo", SESSION.user.username)
            print("[LOBO] Escribe al menos 1 palabras para buscar coincidencias.")
            return

        # Buscar coincidencias usando LIKE
        coincidencias = self.memoria.buscar_por_contenido(texto, etiqueta)

        if not coincidencias:
            bitacora.registrar("recordatorios", "buscar fallido", "No se encontraron "
                                                                  "recordatorios con la descprición y/o etiqueta "
                                                                  "escrita", SESSION.user.username)
            print("⚠️ No se encontraron recordatorios con esa descripción y etiqueta.")
            return

        # Si solo hay una coincidencia, confirmar directamente
        if len(coincidencias) == 1:
            seleccionado = coincidencias[0]
            print(f"⚠️ ¿Estás seguro que deseas eliminar: “{seleccionado.content}”?")
            confirm = input("[Y/N]: ").strip().upper()
            if confirm != "Y":
                bitacora.registrar("recordatorios", "cancelar", "Se cancelo la eliminación de "
                                                                "un recordatorio", SESSION.user.username)
                print("❎ Acción cancelada.")
                return

            if self.memoria.eliminar_por_id(seleccionado.id):
                bitacora.registrar("recordatorios", "eliminar", "Recordatorio eliminado por ID"
                                   , SESSION.user.username)
                print(f"🗑️ Recordatorio eliminado con éxito.")
            else:
                bitacora.registrar("recordatorios", "error", "Error al intentar "
                                                             "eliminar un recordatorio", SESSION.user.username)
                print("❌ Ocurrió un error al eliminar el recordatorio.")
            return

        # Si hay más de una coincidencia, mostrar todas y pedir ID
        print("🔍 Se encontraron varios recordatorios:")
        for nota in coincidencias:
            fecha = nota.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[ID: {nota.id}] [{nota.type.upper()}] {fecha} → {nota.content}")

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

        # Confirmación final
        print(f"⚠️ ¿Estás seguro que deseas eliminar: “{seleccionado.content}”?")
        confirm = input("[Y/N]: ").strip().upper()
        if confirm != "Y":
            print("❎ Acción cancelada.")
            return

        if self.memoria.eliminar_por_id(id_elegido):
            print(f"🗑️ Recordatorio eliminado con éxito.")
        else:
            print("❌ Ocurrió un error al eliminar el recordatorio.")