import os
import sys
import getpass
import hashlib
import shutil
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

SECRET_PATH = os.path.join(os.path.dirname(__file__), 'secrets')
KEY_FILE = os.path.join(SECRET_PATH, 'auth_key.txt')

def hash_clave(clave: str) -> str:
    return hashlib.sha256(clave.encode('utf-8')).hexdigest()


def hacer_backup_clave():
    if os.path.exists(KEY_FILE):
        backup_dir = os.path.join(SECRET_PATH, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'auth_key_backup_{timestamp}.txt')
        shutil.copy2(KEY_FILE, backup_file)
        logger.info(f"Backup de clave creado en: {backup_file}")


def generar_clave_si_no_existe():
    if not os.path.exists(SECRET_PATH):
        os.makedirs(SECRET_PATH)

    if not os.path.exists(KEY_FILE):
        logger.info("No se encontró clave de acceso. Generando nueva clave.")
        nueva_clave = input("🔐 Ingrese la nueva clave maestra: ").strip()
        hash_nueva_clave = hash_clave(nueva_clave)

        with open(KEY_FILE, 'w') as f:
            f.write(hash_nueva_clave)
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

        if hash_clave(clave_ingresada) == clave_correcta:
            logger.info("Autenticación exitosa.")
            return True
        else:
            logger.warning(f"Clave incorrecta. Intentos restantes: {intentos - intento - 1}")

    logger.critical("Demasiados intentos fallidos. Cerrando sistema.")
    sys.exit(1)
