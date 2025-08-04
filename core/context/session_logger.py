# core/context/session_logger.py
from core.db.schema import User as DBUser
from core.db.sessions import SessionLocal
from modules.bitacora.bitacora import Bitacora
bitacora = Bitacora()

class SessionContext:
    def __init__(self):
        self.db = SessionLocal()
        self.user: DBUser | None = None

    def login(self, username: str):
        user = self.db.query(DBUser).filter_by(username=username).first()
        if not user:
            bitacora.registrar("session_logger", "Login fallido",
                               "Se intento  acceder con un nombre de usuario inexistente",
                               self.user.username)
            raise ValueError("❌ Usuario no encontrado.")
        self.user = user
        bitacora.registrar("session_logger", "Login exitoso",
                           "Se inicializó el programa",
                           self.user.username)
        print(f"🔑 Sesión iniciada como '{self.user.username}' ({self.user.role})")

    def logout(self):
        print(f"🔒 Sesión cerrada para '{self.user.username}'") if self.user else None
        self.user = None

    def is_admin(self):
        return self.user and self.user.role == "admin"

    def assert_admin(self):
        if not self.is_admin():
            print("⚠️ Solo el administrador puede acceder a esta interfaz.")
            bitacora.registrar("session_logger", "Only Admin",
                               "Se intento realizar una acción permitida solamente a administrador.",
                               self.user.username)
            exit(1)
