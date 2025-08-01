# core/services/user_service.py
from core.db.schema import User
from core.db.sessions import SessionLocal

def get_user_by_username(username: str) -> User | None:
    db = SessionLocal()
    return db.query(User).filter_by(username=username).first()

def delete_user_by_username(username: str) -> bool:
    db = SessionLocal()
    user = db.query(User).filter_by(username=username).first()
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True
