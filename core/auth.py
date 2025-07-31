import getpass
import logging
import sys

# Contraseña maestra (idealmente deberías cifrarla y guardarla de forma segura)
MASTER_PASSWORD = "loboseguro"
MAX_ATTEMPTS = 3

def authenticate():
    logging.info("Autenticación requerida")
    attempts = 0

    while attempts < MAX_ATTEMPTS:
        try:
            password = getpass.getpass("🔐 Ingrese la contraseña de acceso: ")
        except Exception as e:
            logging.error(f"Error al capturar la contraseña: {e}")
            sys.exit(1)

        if password == MASTER_PASSWORD:
            logging.info("Autenticación exitosa")
            return True
        else:
            attempts += 1
            logging.warning(f"Contraseña incorrecta ({attempts}/{MAX_ATTEMPTS})")

    logging.error("Demasiados intentos fallidos. Cerrando el sistema.")
    sys.exit(1)
