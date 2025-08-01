# core/context/session_logger.py
from core.db.schema import User as DBUser
from core.db.sessions import SessionLocal

class SessionContext:
    def __init__(self):
        self.db = SessionLocal()
        self.user: DBUser | None = None

    def login(self, username: str):
        user = self.db.query(DBUser).filter_by(username=username).first()
        if not user:
            raise ValueError("❌ Usuario no encontrado.")
        self.user = user
        print(f"🔑 Sesión iniciada como '{self.user.username}' ({self.user.role})")

    def logout(self):
        print(f"🔒 Sesión cerrada para '{self.user.username}'") if self.user else None
        self.user = None

    def is_admin(self):
        return self.user and self.user.role == "admin"

    def assert_admin(self):
        if not self.is_admin():
            print("⚠️ Solo el administrador puede acceder a esta interfaz.")
            exit(1)
