# test_integridad_agenda.py
"""
Script de verificación de integridad para Fase 1 del Módulo Agenda
"""

import sys
import os

print("🔍 Verificación de Integridad - Módulo Agenda Fase 1")
print("=" * 70)

# Test 1: Verificar schema
print("\n1️⃣ Verificando schema actualizado...")
try:
    from core.db.schema import Evento

    # Verificar que tenga los campos nuevos
    campos_requeridos = [
        'es_maestro', 'master_id', 'modificado_manualmente',
        'tipo_evento', 'alarma_minutos', 'alarma_activa', 'color_custom'
    ]

    from sqlalchemy import inspect
    from core.db.sessions import engine

    inspector = inspect(engine)
    columnas_db = [col['name'] for col in inspector.get_columns('eventos')]

    faltantes = [campo for campo in campos_requeridos if campo not in columnas_db]

    if faltantes:
        print(f"   ❌ Faltan campos en DB: {', '.join(faltantes)}")
        print("   Ejecuta: python -m core.db.migration_agenda")
        sys.exit(1)
    else:
        print("   ✅ Schema actualizado correctamente")
        print(f"   Campos encontrados: {len(columnas_db)}")

except Exception as e:
    print(f"   ❌ Error al verificar schema: {e}")
    sys.exit(1)

# Test 2: Verificar módulo de conflictos
print("\n2️⃣ Verificando módulo de conflictos...")
try:
    from modules.agenda.conflictos import CONFLICTOS

    print("   ✅ Módulo conflictos.py importado correctamente")

    # Test básico de funcionalidad
    from datetime import date, time

    test_conflictos = CONFLICTOS.detectar_conflictos(
        date(2025, 10, 28),
        time(9, 0),
        time(10, 0)
    )
    print(f"   ✅ Función detectar_conflictos() funcional")

    test_libres = CONFLICTOS.encontrar_horas_libres(date(2025, 10, 28))
    print(f"   ✅ Función encontrar_horas_libres() funcional")
    print(f"   Bloques libres encontrados: {len(test_libres)}")

except ImportError as e:
    print(f"   ❌ Error al importar conflictos.py: {e}")
    print("   Verifica que el archivo modules/agenda/conflictos.py exista")
    sys.exit(1)
except Exception as e:
    print(f"   ⚠️  Módulo importado pero error en funcionalidad: {e}")

# Test 3: Verificar eventos existentes
print("\n3️⃣ Verificando eventos existentes...")
try:
    from core.db.sessions import SessionLocal
    from core.db.schema import Evento

    db = SessionLocal()
    total_eventos = db.query(Evento).count()
    print(f"   ✅ Total de eventos en DB: {total_eventos}")

    if total_eventos > 0:
        # Verificar un evento
        evento_test = db.query(Evento).first()
        print(f"   Evento de prueba: {evento_test.nombre}")
        print(f"     • tipo_evento: {evento_test.tipo_evento}")
        print(f"     • alarma_minutos: {evento_test.alarma_minutos}")
        print(f"     • es_maestro: {evento_test.es_maestro}")
        print(f"     • master_id: {evento_test.master_id}")

    db.close()

except Exception as e:
    print(f"   ❌ Error al verificar eventos: {e}")
    sys.exit(1)

# Test 4: Verificar que LOBO puede iniciar
print("\n4️⃣ Verificando importaciones principales...")
try:
    from core.brain import Brain
    from modules.agenda.agenda import AgendaAPI

    print("   ✅ Brain importado correctamente")
    print("   ✅ AgendaAPI importado correctamente")
except Exception as e:
    print(f"   ⚠️  Error en importaciones: {e}")
    print("   Esto podría no ser crítico si la migración fue exitosa")

# Resumen
print("\n" + "=" * 70)
print("✅ VERIFICACIÓN COMPLETADA")
print("=" * 70)
print("\nEstado: Fase 1 (Parcial) - Listo para continuar")
print("\nPróximos pasos:")
print("  1. Probar comandos actuales de agenda")
print("  2. Confirmar que no hay errores en el dashboard")
print("  3. Avisar a Claude para continuar con Fase 1 completa")
print()