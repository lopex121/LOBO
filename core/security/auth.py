# core/security/auth.py

import bcrypt
from core.db.schema import User

from core.db.sessions import SessionLocal
session = SessionLocal()

from core.context.global_session import SESSION

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_clave(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def login():
    username = input("Nombre de usuario: ").strip()
    password = input("Contraseña: ").strip()

    user = session.query(User).filter_by(username=username).first()
    if user and verificar_clave(password, user.hashed_password):
        SESSION.login(user.username)
        print("✅ Autenticación exitosa.")
        return True
    else:
        print("❌ Usuario o contraseña incorrectos.")
        return False

def authenticate():
    print("=== Sistema de Autenticación de LOBO ===")
    option = input("¿Quieres [1] Iniciar sesión?").strip()

    if option == "1":
        return login()
    else:
        print("⚠️ Opción inválida.")
        return False
