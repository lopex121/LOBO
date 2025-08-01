# core/security/auth.py

import bcrypt
from core.db.schema import User

from core.db.sessions import SessionLocal
session = SessionLocal()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verificar_clave(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def register():
    username = input("Nuevo nombre de usuario: ").strip()
    existing_user = session.query(User).filter_by(username=username).first()
    if existing_user:
        print("⚠️ El usuario ya existe.")
        return False

    password = input("Contraseña: ").strip()
    hashed_pw = hash_password(password)
    user = User(username=username, hashed_password=hashed_pw)
    session.add(user)
    session.commit()
    print("✅ Registro exitoso.")
    return True

def login():
    username = input("Nombre de usuario: ").strip()
    password = input("Contraseña: ").strip()

    user = session.query(User).filter_by(username=username).first()
    if user and verificar_clave(password, user.hashed_password):
        print("✅ Autenticación exitosa.")
        return True
    else:
        print("❌ Usuario o contraseña incorrectos.")
        return False

def authenticate():
    print("=== Sistema de Autenticación de LOBO ===")
    option = input("¿Quieres [1] Iniciar sesión o [2] Registrar? ").strip()

    if option == "1":
        return login()
    elif option == "2":
        return register()
    else:
        print("⚠️ Opción inválida.")
        return False
