# test_fase1_completa.py
"""
Verificación completa de FASE 1 - Módulo Agenda
"""

import sys

print("🔍 Verificación FASE 1 COMPLETA - Módulo Agenda")
print("=" * 70)

errores = []

# Test 1: Imports básicos
print("\n1️⃣ Verificando imports...")
try:
    from modules.agenda.conflictos import CONFLICTOS

    print("   ✅ conflictos.py")
except Exception as e:
    errores.append(f"conflictos.py: {e}")
    print(f"   ❌ conflictos.py: {e}")

try:
    from modules.agenda.disponibilidad import DISPONIBILIDAD

    print("   ✅ disponibilidad.py")
except Exception as e:
    errores.append(f"disponibilidad.py: {e}")
    print(f"   ❌ disponibilidad.py: {e}")

try:
    from modules.agenda.agenda_logics_recurrentes import (
        crear_evento_recurrente, editar_instancia, editar_serie
    )

    print("   ✅ agenda_logics_recurrentes.py")
except Exception as e:
    errores.append(f"agenda_logics_recurrentes.py: {e}")
    print(f"   ❌ agenda_logics_recurrentes.py: {e}")

try:
    from modules.agenda.agenda import AgendaAPI

    print("   ✅ agenda.py (refactorizado)")
except Exception as e:
    errores.append(f"agenda.py: {e}")
    print(f"   ❌ agenda.py: {e}")

# Test 2: Verificar función actualizada
print("\n2️⃣ Verificando agenda_logics.py actualizado...")
try:
    from modules.agenda import agenda_logics
    import inspect

    sig = inspect.signature(agenda_logics.crear_evento_db)
    params = list(sig.parameters.keys())

    if 'tipo_evento' in params and 'alarma_minutos' in params:
        print("   ✅ crear_evento_db actualizado con nuevos parámetros")
    else:
        errores.append("crear_evento_db no tiene los parámetros nuevos")
        print("   ❌ crear_evento_db NO actualizado")
        print("      Falta agregar: tipo_evento, alarma_minutos, alarma_activa")
except Exception as e:
    errores.append(f"agenda_logics: {e}")
    print(f"   ❌ Error: {e}")

# Test 3: Dashboard actualizado
print("\n3️⃣ Verificando dashboard actualizado...")
try:
    from core.dashboard import Dashboard
    import inspect

    source = inspect.getsource(Dashboard._mostrar_agenda_hoy)

    if 'DISPONIBILIDAD' in source:
        print("   ✅ Dashboard integra disponibilidad")
    else:
        print("   ⚠️  Dashboard no muestra disponibilidad (no crítico)")
except Exception as e:
    print(f"   ⚠️  Error al verificar dashboard: {e}")

# Test 4: Router actualizado
print("\n4️⃣ Verificando router actualizado...")
try:
    from core.router import comandos

    if 'ver_disponibilidad' in comandos:
        print("   ✅ Comando ver_disponibilidad agregado")
    else:
        errores.append("Falta comando ver_disponibilidad en router")
        print("   ❌ Comando ver_disponibilidad NO encontrado")
except Exception as e:
    errores.append(f"router: {e}")
    print(f"   ❌ Error: {e}")

# Test 5: Prueba funcional de conflictos
print("\n5️⃣ Probando detección de conflictos...")
try:
    from datetime import date, time

    conflictos = CONFLICTOS.detectar_conflictos(
        date(2025, 10, 28),
        time(9, 0),
        time(10, 0)
    )
    print(f"   ✅ Detección funcional ({len(conflictos)} conflictos encontrados)")

    bloques = CONFLICTOS.encontrar_horas_libres(date(2025, 10, 28))
    print(f"   ✅ Búsqueda de horas libres funcional ({len(bloques)} bloques)")
except Exception as e:
    errores.append(f"conflictos funcional: {e}")
    print(f"   ❌ Error: {e}")

# Test 6: Prueba funcional de disponibilidad
print("\n6️⃣ Probando vista de disponibilidad...")
try:
    from datetime import date

    resumen = DISPONIBILIDAD.disponibilidad_resumen(date(2025, 10, 28))
    print(f"   ✅ Vista disponibilidad funcional")
    print(f"      Horas libres: {resumen['horas_libres']:.1f}h")
    print(f"      Bloques: {resumen['bloques_count']}")
except Exception as e:
    errores.append(f"disponibilidad funcional: {e}")
    print(f"   ❌ Error: {e}")

# Resumen final
print("\n" + "=" * 70)

if not errores:
    print("✅ FASE 1 COMPLETADA EXITOSAMENTE")
    print("=" * 70)
    print("\n🎉 ¡Todo listo para probar LOBO!")
    print("\nPrueba estos comandos:")
    print("  • ver_disponibilidad")
    print("  • agregar_evento \"Test\" 2025-10-28 18:00 19:00 \"\" unico deporte")
    print("  • agregar_evento \"Serie\" 2025-10-28 09:00 10:00 \"\" semanal clase")
    print("  • ver_eventos semana +1")
    print()
else:
    print("❌ ERRORES ENCONTRADOS:")
    print("=" * 70)
    for i, error in enumerate(errores, 1):
        print(f"{i}. {error}")
    print("\n⚠️  Revisa los errores antes de usar LOBO")
    print()
    sys.exit(1)