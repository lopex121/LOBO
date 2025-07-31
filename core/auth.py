# core/auth.py

import getpass
from utils.logger import logger

# Contraseña maestra por ahora (en producción usar hash)
MASTER_PASSWORD = "loboseguro"

def authenticate():
    logger.info("Autenticación requerida")

    try:
        password = getpass.getpass("🔐 Ingrese la contraseña de acceso: ")
    except getpass.GetPassWarning:
        print("⚠️ Advertencia: Su terminal no soporta ocultar la entrada. La contraseña puede ser visible.")
        password = input("🔐 Ingrese la contraseña de acceso (visible): ")

    if password == MASTER_PASSWORD:
        logger.info("Autenticación exitosa")
        return True
    else:
        logger.info("Fallo en la autenticación")
        print("❌ Contraseña incorrecta. Acceso denegado.")
        return False
