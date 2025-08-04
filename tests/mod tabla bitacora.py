from sqlalchemy import create_engine
engine = create_engine("sqlite:///core/database/lobo.db")  # pon la ruta real

with engine.connect() as conn:
    conn.execute("ALTER TABLE bitacora ADD COLUMN usuario TEXT")
