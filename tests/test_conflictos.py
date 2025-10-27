# test_conflictos.py
from modules.agenda.conflictos import CONFLICTOS
from datetime import date, time

print("🧪 Test 1: Detectar conflictos")
print("=" * 60)

# Simular: Ya tienes evento de 09:00 a 10:30
# Intentas agregar evento de 10:00 a 11:00 (debería detectar conflicto)

fecha_test = date(2025, 10, 28)  # Ajusta a una fecha donde tengas eventos
hora_inicio_nueva = time(10, 0)
hora_fin_nueva = time(11, 0)

conflictos = CONFLICTOS.detectar_conflictos(fecha_test, hora_inicio_nueva, hora_fin_nueva)

if conflictos:
    print(f"✅ Conflictos detectados: {len(conflictos)}")
    for conf in conflictos:
        print(f"   • {conf.nombre}: {conf.hora_inicio} - {conf.hora_fin}")
else:
    print("❌ No se detectaron conflictos (verifica que tengas eventos ese día)")

print("\n🧪 Test 2: Encontrar horas libres")
print("=" * 60)

bloques = CONFLICTOS.encontrar_horas_libres(fecha_test, duracion_minutos=60)

print(f"Bloques libres encontrados: {len(bloques)}")
for i, bloque in enumerate(bloques, 1):
    print(f"{i}. {bloque['inicio']} - {bloque['fin']} ({bloque['duracion_min']} min)")

print("\n✅ Test de conflictos completado")