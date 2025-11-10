# auto_archivar.py
"""
Script para ejecutar automáticamente el archivado de hojas antiguas
Se debe ejecutar los domingos a las 23:59

Opciones de automatización:
1. Cron job (Linux/Mac)
2. Task Scheduler (Windows)
3. Integrar en LOBO como tarea en background
"""

from datetime import datetime, date
from modules.agenda.sheets_manager import SHEETS_MANAGER
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)


def ejecutar_archivado():
    """Ejecuta el archivado de hojas antiguas"""

    hoy = date.today()

    # Verificar que sea domingo
    if hoy.weekday() != 6:  # 6 = Domingo
        logger.warning(f"Hoy no es domingo (día {hoy.weekday()}). No se archivará.")
        return False

    # Verificar que sea cerca de las 23:59
    ahora = datetime.now()
    if ahora.hour != 23:
        logger.warning(f"No es la hora correcta (hora actual: {ahora.hour}:00)")
        return False

    logger.info("Iniciando archivado automático de hojas antiguas...")

    try:
        hojas_archivadas = SHEETS_MANAGER.archivar_semanas_antiguas()

        if hojas_archivadas:
            logger.info(f"✅ Archivadas: {', '.join(hojas_archivadas)}")
        else:
            logger.info("ℹ️  No hay hojas antiguas para archivar")

        return True

    except Exception as e:
        logger.error(f"❌ Error durante archivado: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("  ARCHIVADO AUTOMÁTICO DE HOJAS ANTIGUAS")
    print("=" * 70)
    print()

    ejecutar_archivado()

    print("\n" + "=" * 70)
    print("Proceso completado")

# ===== CONFIGURACIÓN DE CRON (Linux/Mac) =====
# Ejecutar este script todos los domingos a las 23:59
#
# Editar crontab:
#   crontab -e
#
# Agregar línea:
#   59 23 * * 0 cd /ruta/a/LOBO && python auto_archivar.py >> logs/archivado.log 2>&1
#
# Esto ejecutará el script todos los domingos a las 23:59


# ===== CONFIGURACIÓN DE TASK SCHEDULER (Windows) =====
# 1. Abrir Task Scheduler
# 2. Create Basic Task
# 3. Name: "LOBO Archivar Hojas"
# 4. Trigger: Weekly, Domingos, 23:59
# 5. Action: Start a program
#    Program: C:\ruta\a\python.exe
#    Arguments: C:\ruta\a\LOBO\auto_archivar.py
#    Start in: C:\ruta\a\LOBO
