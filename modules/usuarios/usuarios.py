# modules/usuarios/usuarios.py
from core.db.sessions import SessionLocal
from core.db.schema import User
from core.security.auth import hash_password, verificar_clave
from core.context.global_session import SESSION
from core.services import user_service
from getpass import getpass

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

def comando_eliminar_usuario(args):
    SESSION.assert_admin()

    if len(args) < 1:
        print("[LOBO] Uso: eliminar_usuario <USERNAME>")
        return

    username = args[0]
    if username == SESSION.user.username:
        print("⚠️ No puedes eliminar tu propio usuario mientras está en sesión.")
        return

    user = user_service.get_user_by_username(username)
    if not user:
        print(f"❌ Usuario '{username}' no encontrado.")
        return

    confirm = input(f"¿Estás seguro que quieres eliminar a '{username}'? [Y/N]: ").strip().upper()
    if confirm != "Y":
        print("❎ Se canceló la acción.")
        return

    clave = getpass("🔐 Confirma tu contraseña de administrador: ")
    if not verificar_clave(clave, SESSION.user.hashed_password):
        print("❌ Contraseña incorrecta. Acción cancelada.")
        return

    if user_service.delete_user_by_username(username):
        print(f"🗑️ Usuario '{username}' eliminado con éxito.")
    else:
        print("⚠️ No se pudo eliminar el usuario.")