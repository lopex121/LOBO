# modules/usuarios/usuarios.py
from core.db.sessions import SessionLocal
from core.db.schema import User
from core.security.auth import hash_password, verificar_clave
from core.services import user_service
from getpass import getpass
from modules.bitacora.bitacora import Bitacora
bitacora = Bitacora()
from core.context.global_session import SESSION

def crear_usuario_visita(username: str, password: str):
    db = SessionLocal()
    if db.query(User).filter_by(username=username).first():
        bitacora.registrar("usuarios", "error", "Se intento crear un usuario con nombre "
                                                "existente",
                           SESSION.user.username)
        print("⚠️ El usuario ya existe.")
        return

    nuevo = User(
        username=username,
        hashed_password=hash_password(password),
        role="visita"
    )
    db.add(nuevo)
    db.commit()
    bitacora.registrar("usuarios", "crear", "Se asigno el rol de visita a" f"{username}"
                       ,SESSION.user.username)
    print(f"✅ Usuario '{username}' creado como 'visita'.")

def comando_nuevo_usuario(args):
    SESSION.assert_admin()
    if len(args) < 2:
        print("[LOBO] Uso: nuevo_usuario <USERNAME> <PASSWORD>")
        return
    username, password = args[0], args[1]
    crear_usuario_visita(username, password)
    bitacora.registrar("usuarios", "crear", "Se creo un usuario con nombre" f"{username}"
                       ,SESSION.user.username)

def comando_eliminar_usuario(args):
    SESSION.assert_admin()
    if len(args) < 1:
        print("[LOBO] Uso: eliminar_usuario <USERNAME>")
        return

    username = args[0]
    if username == SESSION.user.username:
        bitacora.registrar("usuarios", "eliminar", "Se intento eliminar el usuario actual"
                           , SESSION.user.username)
        print("⚠️ No puedes eliminar tu propio usuario mientras está en sesión.")
        return

    user = user_service.get_user_by_username(username)
    if not user:
        bitacora.registrar("usuarios", "error", "Se intento eliminar un usuario inexistente"
                           , SESSION.user.username)
        print(f"❌ Usuario '{username}' no encontrado.")
        return

    confirm = input(f"¿Estás seguro que quieres eliminar a '{username}'? [Y/N]: ").strip().upper()
    if confirm != "Y":
        bitacora.registrar("usuarios", "cancelar eliminación", "Se canceló la acción de eliminar el usuario" 
                                                               f"{username}", SESSION.user.username)
        print("❎ Se canceló la acción.")
        return

    clave = getpass("🔐 Confirma tu contraseña de administrador: ")
    if not verificar_clave(clave, SESSION.user.hashed_password):
        print("❌ Contraseña incorrecta. Acción cancelada.")
        bitacora.registrar("usuarios", "fallido", "Se intento eliminar un usuario, pero la "
                                                  "clave fue erronea", SESSION.user.username)
        return

    if user_service.delete_user_by_username(username):
        print(f"🗑️ Usuario '{username}' eliminado con éxito.")
        bitacora.registrar("usuarios", "eliminar", "Se elimino el usuario" f"{username}",
                           SESSION.user.username)
    else:
        print("⚠️ No se pudo eliminar el usuario.")