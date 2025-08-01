# core/services/user_service.py

from core.db.schema import User
from core.db.sessions import SessionLocal
from core.security.auth import hash_password, verificar_clave
from sqlalchemy.exc import IntegrityError

def create_user(username: str, password: str):
    db = SessionLocal()
    try:
        hashed = hash_password(password)
        new_user = User(username=username, hashed_password=hashed)
        db.add(new_user)
        db.commit()
        return {"success": True, "message": f"Usuario '{username}' creado correctamente."}
    except IntegrityError:
        db.rollback()
        return {"success": False, "message": f"Usuario '{username}' ya existe."}
    finally:
        db.close()

def authenticate_user(username: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and verificar_clave(password, user.hashed_password):
            return {"success": True, "user": user}
        return {"success": False, "message": "Credenciales inválidas"}
    finally:
        db.close()
