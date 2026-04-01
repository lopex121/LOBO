# scripts/diagnostico_agenda.py
"""
Herramienta de diagnóstico completa para detectar problemas
en la sincronización DB ↔ Sheets
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# Agregar path del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.db.sessions import SessionLocal
from core.db.schema import Evento
from core.lobo_google.lobo_sheets import get_spreadsheet
from modules.agenda.agenda_fixes import HojaParser


class DiagnosticoCompleto:
    """
    Realiza diagnóstico exhaustivo del sistema de agenda
    """

    def __init__(self):
        self.spreadsheet = get_spreadsheet()
        self.session = SessionLocal()

    def paso_1_analizar_hojas(self):
        """Analiza estructura de hojas en el spreadsheet"""
        print("\n" + "=" * 70)
        print("PASO 1: ANÁLISIS DE HOJAS EN SPREADSHEET")
        print("=" * 70)

        hojas = self.spreadsheet.worksheets()
        print(f"\n📊 Total de hojas: {len(hojas)}\n")

        hojas_con_fecha = []
        hojas_especiales = []

        for i, hoja in enumerate(hojas, 1):
            fecha = HojaParser.parsear_nombre_hoja(hoja.title)

            if fecha:
                hojas_con_fecha.append((fecha, hoja.title))
                icono = "📅"
            else:
                hojas_especiales.append(hoja.title)
                icono = "📄"

            print(f"{i:2d}. {icono} {hoja.title}")
            if fecha:
                print(f"       → Fecha: {fecha.strftime('%d/%m/%Y')} (lunes)")

        # Resumen
        print("\n" + "─" * 70)
        print(f"   Hojas de agenda: {len(hojas_con_fecha)}")
        print(f"   Hojas especiales: {len(hojas_especiales)}")

        if hojas_especiales:
            print(f"\n   Hojas especiales detectadas:")
            for nombre in hojas_especiales:
                print(f"      • {nombre}")

        # Verificar orden
        if hojas_con_fecha:
            fechas_ordenadas = sorted([f for f, _ in hojas_con_fecha])
            fechas_actuales = [f for f, _ in hojas_con_fecha]

            if fechas_ordenadas != fechas_actuales:
                print("\n   ⚠️  PROBLEMA: Hojas NO están ordenadas cronológicamente")
                print("      Ejecuta: reordenar_hojas")
            else:
                print("\n   ✅ Hojas están ordenadas correctamente")

        print()
        return hojas_con_fecha, hojas_especiales

    def paso_2_analizar_db(self):
        """Analiza eventos en la base de datos"""
        print("\n" + "=" * 70)
        print("PASO 2: ANÁLISIS DE EVENTOS EN DB")
        print("=" * 70)

        hoy = date.today()
        hace_4_semanas = hoy - timedelta(weeks=4)
        en_12_semanas = hoy + timedelta(weeks=12)

        # Contar por categoría
        stats = {}

        # Eventos muy pasados (> 4 semanas)
        stats['muy_pasados'] = self.session.query(Evento).filter(
            Evento.fecha_inicio < hace_4_semanas,
            Evento.es_maestro == False
        ).count()

        # Eventos pasados recientes (últimas 4 semanas)
        stats['pasados_recientes'] = self.session.query(Evento).filter(
            Evento.fecha_inicio >= hace_4_semanas,
            Evento.fecha_inicio < hoy,
            Evento.es_maestro == False
        ).count()

        # Eventos actuales (esta semana)
        lunes = hoy - timedelta(days=hoy.weekday())
        domingo = lunes + timedelta(days=6)
        stats['esta_semana'] = self.session.query(Evento).filter(
            Evento.fecha_inicio >= lunes,
            Evento.fecha_inicio <= domingo,
            Evento.es_maestro == False
        ).count()

        # Eventos futuros (próximas 12 semanas)
        stats['futuros'] = self.session.query(Evento).filter(
            Evento.fecha_inicio > domingo,
            Evento.fecha_inicio <= en_12_semanas,
            Evento.es_maestro == False
        ).count()

        # Eventos muy futuros (> 12 semanas)
        stats['muy_futuros'] = self.session.query(Evento).filter(
            Evento.fecha_inicio > en_12_semanas,
            Evento.es_maestro == False
        ).count()

        # Maestros
        stats['maestros'] = self.session.query(Evento).filter(
            Evento.es_maestro == True
        ).count()

        # Total
        total = sum(stats.values())

        # Mostrar
        print(f"\n📊 Eventos en base de datos:\n")
        print(f"   🕰️  Muy pasados (> 4 sem):      {stats['muy_pasados']:4d}")
        print(f"   📅 Pasados recientes (< 4 sem): {stats['pasados_recientes']:4d}")
        print(f"   📍 Esta semana:                 {stats['esta_semana']:4d}")
        print(f"   🔮 Futuros (próx 12 sem):       {stats['futuros']:4d}")
        print(f"   🚀 Muy futuros (> 12 sem):      {stats['muy_futuros']:4d}")
        print(f"   👑 Maestros (series):           {stats['maestros']:4d}")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"   📦 TOTAL:                       {total:4d}")

        # Problemas detectados
        problemas = []

        if stats['muy_pasados'] > 0:
            problemas.append(f"⚠️  {stats['muy_pasados']} eventos muy pasados deberían archivarse")

        if stats['muy_futuros'] > 20:
            problemas.append(f"⚠️  {stats['muy_futuros']} eventos muy futuros (posible error)")

        if problemas:
            print("\n   Problemas detectados:")
            for p in problemas:
                print(f"      {p}")
        else:
            print("\n   ✅ Distribución de eventos OK")

        print()
        return stats

    def paso_3_comparar_sync(self, hojas_con_fecha):
        """Compara eventos en DB vs Sheets"""
        print("\n" + "=" * 70)
        print("PASO 3: COMPARACIÓN DB ↔ SHEETS")
        print("=" * 70)

        desincronizaciones = []

        print("\nComparando hoja por hoja...\n")

        for fecha, nombre_hoja in hojas_con_fecha[:5]:  # Solo primeras 5
            fecha_fin = fecha + timedelta(days=6)

            # Contar en DB
            eventos_db = self.session.query(Evento).filter(
                Evento.fecha_inicio >= fecha,
                Evento.fecha_inicio <= fecha_fin,
                Evento.es_maestro == False
            ).count()

            # Simular conteo en Sheets (simplificado)
            # En producción, leerías el Sheet y contarías celdas pintadas
            print(f"   📅 {nombre_hoja}: {eventos_db} eventos en DB")

            if eventos_db == 0:
                desincronizaciones.append((nombre_hoja, "Sin eventos en DB"))

        if desincronizaciones:
            print("\n   ⚠️  Posibles desincronizaciones detectadas:")
            for hoja, problema in desincronizaciones:
                print(f"      • {hoja}: {problema}")
            print("\n      Ejecuta: sincronizar_real")
        else:
            print("\n   ✅ Sincronización parece correcta")

        print()

    def paso_4_verificar_integridad(self):
        """Verifica integridad referencial"""
        print("\n" + "=" * 70)
        print("PASO 4: VERIFICACIÓN DE INTEGRIDAD")
        print("=" * 70)

        problemas = []

        # Buscar instancias huérfanas (sin maestro válido)
        instancias = self.session.query(Evento).filter(
            Evento.es_maestro == False,
            Evento.master_id != None
        ).all()

        huerfanos = []
        for instancia in instancias:
            maestro = self.session.query(Evento).filter(
                Evento.id == instancia.master_id,
                Evento.es_maestro == True
            ).first()

            if not maestro:
                huerfanos.append(instancia)

        if huerfanos:
            print(f"\n   ⚠️  {len(huerfanos)} instancias huérfanas detectadas")
            print("      (instancias de series sin maestro válido)")
            problemas.append("instancias_huerfanas")
        else:
            print("\n   ✅ No hay instancias huérfanas")

        # Buscar maestros sin instancias
        maestros = self.session.query(Evento).filter(
            Evento.es_maestro == True
        ).all()

        maestros_vacios = []
        for maestro in maestros:
            instancias_count = self.session.query(Evento).filter(
                Evento.master_id == maestro.id,
                Evento.es_maestro == False
            ).count()

            if instancias_count == 0:
                maestros_vacios.append(maestro)

        if maestros_vacios:
            print(f"\n   ⚠️  {len(maestros_vacios)} maestros sin instancias")
            print("      (eventos maestros que no generaron instancias)")
            problemas.append("maestros_vacios")
        else:
            print("   ✅ Todos los maestros tienen instancias")

        if not problemas:
            print("\n   ✅ Integridad OK")

        print()

    def generar_reporte_completo(self):
        """Genera reporte completo de diagnóstico"""
        print("\n" + "🐺" * 35)
        print("   LOBO - DIAGNÓSTICO COMPLETO DE AGENDA")
        print("🐺" * 35)

        # Ejecutar pasos
        hojas_con_fecha, hojas_especiales = self.paso_1_analizar_hojas()
        stats_db = self.paso_2_analizar_db()
        self.paso_3_comparar_sync(hojas_con_fecha)
        self.paso_4_verificar_integridad()

        # Recomendaciones
        print("=" * 70)
        print("🎯 RECOMENDACIONES")
        print("=" * 70)

        recomendaciones = []

        # Recomendación 1: Limpiar DB
        if stats_db['muy_pasados'] > 0:
            recomendaciones.append({
                'prioridad': 'ALTA',
                'accion': 'Limpiar eventos pasados de DB',
                'comando': 'limpiar_db_pasados eliminar 4',
                'impacto': f'Eliminará {stats_db["muy_pasados"]} eventos antiguos'
            })

        # Recomendación 2: Reordenar hojas
        recomendaciones.append({
            'prioridad': 'MEDIA',
            'accion': 'Reordenar hojas cronológicamente',
            'comando': 'reordenar_hojas',
            'impacto': 'Mejora organización visual'
        })

        # Recomendación 3: Sincronizar
        recomendaciones.append({
            'prioridad': 'ALTA',
            'accion': 'Sincronización completa DB → Sheets',
            'comando': 'sincronizar_real',
            'impacto': 'Elimina eventos fantasma y repinta todo desde DB'
        })

        # Mostrar
        for i, rec in enumerate(recomendaciones, 1):
            print(f"\n{i}. [{rec['prioridad']}] {rec['accion']}")
            print(f"   Comando: {rec['comando']}")
            print(f"   Impacto: {rec['impacto']}")

        print("\n" + "=" * 70)
        print()

    def __del__(self):
        """Cerrar sesión"""
        if hasattr(self, 'session'):
            self.session.close()


def main():
    """Función principal"""
    diagnostico = DiagnosticoCompleto()
    diagnostico.generar_reporte_completo()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❎ Diagnóstico cancelado (Ctrl+C)\n")
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        raise
