from core.memory import Memory
from datetime import datetime

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
            _, tipo, contenido, timestamp = nota
            fecha = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            print(f" • [{tipo.upper()}] {fecha.strftime('%d/%m %H:%M')} → {contenido}")
