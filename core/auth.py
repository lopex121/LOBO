import os
import sys
import getpass
from utils.logger import get_logger

logger = get_logger(__name__)

SECRET_PATH = os.path.join(os.path.dirname(__file__), 'secrets')
KEY_FILE = os.path.join(SECRET_PATH, 'auth_key.txt')


def generar_clave_si_no_existe():
    if not os.path.exists(SECRET_PATH):
        os.makedirs(SECRET_PATH)

    if not os.path.exists(KEY_FILE):
        logger.info("No se encontró clave de acceso. Generando nueva clave.")
        nueva_clave = input("🔐 Ingrese la nueva clave maestra: ").strip()

        with open(KEY_FILE, 'w') as f:
            f.write(nueva_clave)
        logger.info("Clave generada y almacenada correctamente.")


def verificar_clave():
    generar_clave_si_no_existe()

    with open(KEY_FILE, 'r') as f:
        clave_correcta = f.read().strip()

    intentos = 3

    for intento in range(intentos):
        try:
            clave_ingresada = getpass.getpass("🔐 Ingrese la clave de acceso: ").strip()
        except Exception:
            clave_ingresada = input("🔐 Ingrese la clave de acceso: ").strip()

        if clave_ingresada == clave_correcta:
            logger.info("Autenticación exitosa.")
            return True
        else:
            logger.warning(f"Clave incorrecta. Intentos restantes: {intentos - intento - 1}")

    logger.critical("Demasiados intentos fallidos. Cerrando sistema.")
    sys.exit(1)
