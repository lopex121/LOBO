# debug_info_serie.py
"""
Script para debuggear obtener_info_serie
"""

from modules.agenda.agenda_logics_recurrentes import obtener_info_serie
from core.db.sessions import SessionLocal
from core.db.schema import Evento

# IDs de prueba (ajusta con IDs reales de tu DB)
ids_prueba = [
    "3d18e4fa",  # Serie que falla
    "c8a42e34",  # Serie que falla
]

print("🔍 DEBUG obtener_info_serie")
print("=" * 70)

session = SessionLocal()

for id_prueba in ids_prueba:
    print(f"\n📝 Probando ID: {id_prueba}")

    # Buscar por ID parcial
    eventos = session.query(Evento).filter(
        Evento.id.like(f"{id_prueba}%")
    ).all()

    if not eventos:
        print("   ❌ No se encontró evento en DB")
        continue

    if len(eventos) > 1:
        print(f"   ⚠️  Múltiples eventos ({len(eventos)})")
        for ev in eventos:
            print(f"      • {ev.id}")

    evento = eventos[0]
    print(f"   ✅ Evento encontrado: {evento.nombre}")
    print(f"   📊 Campos:")
    print(f"      • es_maestro: {evento.es_maestro}")
    print(f"      • master_id: {evento.master_id}")
    print(f"      • modificado_manualmente: {evento.modificado_manualmente}")
    print(f"      • recurrencia: {evento.recurrencia}")

    # Probar obtener_info_serie
    print(f"\n   🔄 Llamando obtener_info_serie...")
    try:
        info = obtener_info_serie(evento.id)

        if info is None:
            print("      ❌ Retornó None!")
        else:
            print("      ✅ Retornó:")
            for key, value in info.items():
                print(f"         • {key}: {value}")
    except Exception as e:
        print(f"      ❌ Excepción: {e}")
        import traceback

        traceback.print_exc()

session.close()

print("\n" + "=" * 70)
print("DEBUG completado")