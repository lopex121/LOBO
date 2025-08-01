# modules/usuarios/usuarios.py
from core.db.sessions import SessionLocal
from core.db.schema import User
from core.security.auth import hash_password
from core.context.global_session import SESSION

def crear_usuario_visita(username: str, password: str):
    db = SessionLocal()
    if db.query(User).filter_by(username=username).first():
        print("⚠️ El usuario ya existe.")
        return

    nuevo = User(
        username=username,
        hashed_password=hash_password(password),
        role="visita"
    )
    db.add(nuevo)
    db.commit()
    print(f"✅ Usuario '{username}' creado como 'visita'.")

def comando_nuevo_usuario(args):
    SESSION.assert_admin()
    if len(args) < 2:
        print("[LOBO] Uso: nuevo_usuario <USERNAME> <PASSWORD>")
        return
    username, password = args[0], args[1]
    crear_usuario_visita(username, password)
