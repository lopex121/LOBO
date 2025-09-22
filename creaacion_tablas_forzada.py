# force_create_tables.py
from core.db.schema import Base, Evento  # importa todos tus modelos aquí
from core.db.db import engine

if __name__ == "__main__":
    print("[INFO] Forzando creación de tablas nuevas si no existen...")
    Base.metadata.create_all(bind=engine)  # crea SOLO las que falten
    print("[SUCCESS] Tablas listas.")
