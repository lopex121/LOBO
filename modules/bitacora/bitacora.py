# modules/bitacora/bitacora.py

from datetime import datetime
from core.db.sessions import SessionLocal
from core.db.schema import BitacoraRegistro
from core.security.auth import session

class Bitacora:
    def __init__(self):
        self.db = SessionLocal()
        self.session = session

    def registrar(self, modulo: str, accion: str, descripcion: str = "", usuario: str = None):

        nuevo_evento = BitacoraRegistro(
            timestamp=datetime.now(),
            modulo=modulo,
            accion=accion,
            descripcion=descripcion,
            usuario=usuario,
        )
        self.db.add(nuevo_evento)
        self.db.commit()

    def ver_entradas(self, limite: int = 10):
        entradas = self.db.query(BitacoraRegistro).order_by(BitacoraRegistro.timestamp.desc()).limit(limite).all()
        return entradas


def comando_ver_bitacora(args):
    from core.context.global_session import SESSION
    if not SESSION.user:
        print("⚠️ No hay sesión iniciada.")
        return

    SESSION.assert_admin()
    bitacora = Bitacora()
    limite = 100

    if args and args[0].isdigit():
        limite = int(args[0])

    entradas = bitacora.ver_entradas(limite)

    if not entradas:
        print("[LOBO] No hay entradas en la bitácora.")
        return

    print("\n[LOBO] Últimos registros en la bitácora:\n")
    for e in entradas:
        fecha = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{fecha}] [{e.modulo.upper()}] {e.accion} → {e.descripcion}; [{e.usuario}]")
