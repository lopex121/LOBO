# main_db_init.py

from core.db.db import init_db

if __name__ == "__main__":
    print("[INFO] Inicializando base de datos...")
    init_db()
    print("[SUCCESS] Tablas creadas correctamente.")
