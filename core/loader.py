import os
import importlib
from utils.logger import logger

def load_modules(modules_dir="modules"):
    logger.info("Buscando módulos en '%s'...", modules_dir)
    if not os.path.isdir(modules_dir):
        logger.warning("Directorio de módulos '%s' no encontrado.", modules_dir)
        return

    for filename in os.listdir(modules_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            full_module_path = f"{modules_dir}.{module_name}"
            try:
                module = importlib.import_module(full_module_path)
                if hasattr(module, "initialize"):
                    logger.info("Inicializando módulo: %s", module_name)
                    module.initialize()
                else:
                    logger.info("Módulo %s cargado sin función 'initialize'", module_name)
            except Exception as e:
                logger.error("Error al cargar módulo '%s': %s", module_name, str(e))
