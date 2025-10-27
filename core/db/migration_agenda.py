# core/db/migration_agenda.py
"""
Script de migración para agregar campos de recurrencia a tabla Evento
SIN PERDER DATOS EXISTENTES

Ejecutar UNA SOLA VEZ: python -m core.db.migration_agenda
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../database/lobo.db'))


def migrar_agenda():
    print("🔄 Iniciando migración de tabla Evento...")

    if not os.path.exists(DB_PATH):
        print(f"❌ No se encontró la base de datos en: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(eventos)")
        columnas = [col[1] for col in cursor.fetchall()]

        campos_nuevos = {
            'es_maestro': 'INTEGER DEFAULT 0',  # SQLite usa 0/1 para boolean
            'master_id': 'TEXT',
            'modificado_manualmente': 'INTEGER DEFAULT 0',
            'tipo_evento': 'TEXT DEFAULT "personal"',
            'alarma_minutos': 'INTEGER DEFAULT 5',
            'alarma_activa': 'INTEGER DEFAULT 1',
            'color_custom': 'TEXT'
        }

        for campo, tipo in campos_nuevos.items():
            if campo not in columnas:
                print(f"   ➕ Agregando campo '{campo}'...")
                cursor.execute(f"ALTER TABLE eventos ADD COLUMN {campo} {tipo}")
                conn.commit()
            else:
                print(f"   ✅ Campo '{campo}' ya existe")

        # Actualizar eventos existentes
        print("\n🔧 Actualizando registros existentes...")

        # Detectar tipo de evento por etiquetas
        cursor.execute("SELECT id, etiquetas FROM eventos")
        eventos = cursor.fetchall()

        for evento_id, etiquetas_json in eventos:
            if etiquetas_json:
                import json
                try:
                    etiquetas = json.loads(etiquetas_json)

                    # Determinar tipo según etiquetas
                    tipo = "personal"
                    if any(tag in ["clase", "escuela", "universidad"] for tag in etiquetas):
                        tipo = "clase"
                    elif any(tag in ["trabajo", "oficina", "junta"] for tag in etiquetas):
                        tipo = "trabajo"
                    elif any(tag in ["deporte", "gym", "ejercicio"] for tag in etiquetas):
                        tipo = "deporte"
                    elif any(tag in ["estudio", "tarea", "examen"] for tag in etiquetas):
                        tipo = "estudio"
                    elif any(tag in ["reunion", "meeting"] for tag in etiquetas):
                        tipo = "reunion"

                    cursor.execute("UPDATE eventos SET tipo_evento = ? WHERE id = ?", (tipo, evento_id))
                except:
                    pass

        conn.commit()

        print("\n✅ Migración completada exitosamente")
        print(f"   Total de eventos actualizados: {len(eventos)}")

        return True

    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    print("═" * 60)
    print("  MIGRACIÓN DE BASE DE DATOS - MÓDULO AGENDA")
    print("═" * 60)
    print()

    respuesta = input("⚠️  Esta operación modificará la base de datos.\n¿Deseas continuar? [Y/N]: ").strip().upper()

    if respuesta == "Y":
        if migrar_agenda():
            print("\n🎉 ¡Migración exitosa! Puedes ejecutar LOBO normalmente.")
        else:
            print("\n❌ La migración falló. Revisa los errores arriba.")
    else:
        print("\n❎ Migración cancelada.")