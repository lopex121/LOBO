import getpass
from utils.logger import logger

# Contraseña temporal para pruebas (esto se almacenará seguro después)
AUTHORIZED_PASSWORD = "loboseguro"

def authenticate():
    logger.info("Autenticación requerida")
    for intento in range(3):
        password = getpass.getpass("🔐 Ingrese la contraseña de acceso: ")
        if password == AUTHORIZED_PASSWORD:
            logger.info("Autenticación exitosa")
            return True
        else:
            logger.warning("Contraseña incorrecta (%d/3)", intento + 1)
    logger.error("Demasiados intentos fallidos. Cerrando el sistema.")
    return False
