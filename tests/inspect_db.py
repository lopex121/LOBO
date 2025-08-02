import sqlite3

conn = sqlite3.connect("lobo.db")  # o cambia al nombre real de tu base de datos
cursor = conn.cursor()

# Mostrar todas las tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tablas = cursor.fetchall()
print("\nTablas encontradas:")
for t in tablas:
    print(f"- {t[0]}")

# Mostrar columnas de cada tabla
print("\nColumnas por tabla:")
for t in tablas:
    cursor.execute(f"PRAGMA table_info({t[0]});")
    columnas = cursor.fetchall()
    print(f"\nTabla: {t[0]}")
    for col in columnas:
        print(f"  - {col[1]} ({col[2]})")

conn.close()
