# core/db/migration_recordatorios.py
"""
Script de migración para agregar nuevos campos a la tabla MemoryNote
SIN PERDER DATOS EXISTENTES

Ejecutar UNA SOLA VEZ: python -m core.db.migration_recordatorios
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../database/lobo.db'))


def migrar_recordatorios():
    print("🔄 Iniciando migración de tabla MemoryNote...")

    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró la base de datos en: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(memory)")
        columnas = [col[1] for col in cursor.fetchall()]

        campos_nuevos = {
            'fecha_limite': 'DATE',
            'hora_limite': 'TIME',
            'prioridad': 'INTEGER DEFAULT 5',
            'estado': 'TEXT DEFAULT "pendiente"',
            'creado_por': 'TEXT DEFAULT "system"'
        }

        for campo, tipo in campos_nuevos.items():
            if campo not in columnas:
                print(f"   ➕ Agregando campo '{campo}'...")
                cursor.execute(f"ALTER TABLE memory ADD COLUMN {campo} {tipo}")
                conn.commit()
            else:
                print(f"   ✅ Campo '{campo}' ya existe")

        # Actualizar registros existentes según su tipo
        print("\n🔧 Actualizando registros existentes...")

        # Urgentes → prioridad 1
        cursor.execute("UPDATE memory SET prioridad = 1 WHERE type = 'urgente' AND prioridad IS NULL")

        # Importantes → prioridad 2
        cursor.execute("UPDATE memory SET prioridad = 2 WHERE type = 'importante' AND prioridad IS NULL")

        # Tareas → prioridad 3
        cursor.execute("UPDATE memory SET prioridad = 3 WHERE type = 'tarea' AND prioridad IS NULL")

        # Notas e ideas → prioridad 5
        cursor.execute("UPDATE memory SET prioridad = 5 WHERE type IN ('nota', 'idea') AND prioridad IS NULL")

        # Establecer estado pendiente para todos los existentes
        cursor.execute("UPDATE memory SET estado = 'pendiente' WHERE estado IS NULL")

        conn.commit()

        print("\n✅ Migración completada exitosamente")
        print(f"   Total de registros actualizados: {cursor.rowcount}")

        return True

    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    print("═" * 60)
    print("  MIGRACIÓN DE BASE DE DATOS - MÓDULO RECORDATORIOS")
    print("═" * 60)
    print()

    respuesta = input("⚠️  Esta operación modificará la base de datos.\n¿Deseas continuar? [Y/N]: ").strip().upper()

    if respuesta == "Y":
        if migrar_recordatorios():
            print("\n🎉 ¡Migración exitosa! Puedes ejecutar LOBO normalmente.")
        else:
            print("\n❌ La migración falló. Revisa los errores arriba.")
    else:
        print("\n❎ Migración cancelada.")