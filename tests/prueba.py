# prueba.py

from core.services.user_service import create_user, authenticate_user

print(create_user("admin", "secreta123"))
print(authenticate_user("admin", "secreta123"))
print(authenticate_user("admin", "incorrecta"))
