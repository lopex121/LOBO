#modules/recordatorios/recordatorios.py

from core.memory import Memory
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
            print("[LOBO] El texto de la nota no puede estar vacío.")
            return

        self.memoria.remember(texto, mem_type=etiqueta)
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
        print(f"[LOBO] Últimas notas{tipo_info}:\n")

        for nota in reversed(notas[-10:]):
            fecha = nota.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f" • [{nota.type.upper()}] {fecha} → {nota.content}")

    def eliminar(self, args):
        SESSION.assert_admin()

        if not args:
            print("[LOBO] Uso: eliminar_recuerdo <TEXTO> <ETIQUETA>")
            return

        etiquetas_validas = ["urgente", "importante", "idea", "nota"]
        posible_etiqueta = args[-1].lower()
        if posible_etiqueta not in etiquetas_validas:
            print("[LOBO] Debes especificar la etiqueta al final para eliminar con coincidencia parcial.")
            return

        etiqueta = posible_etiqueta
        texto = " ".join(args[:-1])

        if len(texto.strip().split()) < 3:
            print("[LOBO] Escribe al menos 3 palabras para poder eliminar el recordatorio.")
            return

        print(
            f"⚠️ ¿Estás seguro que quieres eliminar algún recordatorio que contenga: “{texto}” y sea de tipo '{etiqueta}'?")
        confirm = input("[Y/N]: ").strip().upper()

        if confirm != "Y":
            print("❎ Acción cancelada.")
            return

        exito = self.memoria.delete(texto.strip(), mem_type=etiqueta)
        if exito:
            print(f"🗑️ Recordatorio eliminado con coincidencia parcial: “{texto}”")
        else:
            print("⚠️ No se encontró ningún recordatorio que coincida con los criterios.")