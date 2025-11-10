# tests/test_sincronizacion_completa.py
"""
LOBO - Suite de Testing para Sincronización Fase 2
Verifica recordatorios y eventos en hojas múltiples
ADAPTADO a tu estructura de código
"""

import sys
import time
from datetime import datetime, timedelta, date
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db.sessions import SessionLocal
from core.db.schema import MemoryNote, Evento
from core.lobo_google.lobo_sheets import get_sheet
from modules.recordatorios.recordatorios_sheets import actualizar_recordatorios_todas_las_hojas
from modules.agenda.sheets_manager import SHEETS_MANAGER
from modules.agenda.agenda_logics import pintar_evento_sheets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSincronizacion:
    """Suite de pruebas para sincronización DB ↔ Google Sheets"""

    def __init__(self):
        self.session = SessionLocal()
        self.errores = []
        self.warnings = []
        self.tests_pasados = 0
        self.tests_totales = 0


    def log_error(self, test_name: str, mensaje: str):
        """Registra un error de test"""
        self.errores.append(f"❌ [{test_name}] {mensaje}")


    def log_warning(self, test_name: str, mensaje: str):
        """Registra una advertencia"""
        self.warnings.append(f"⚠️ [{test_name}] {mensaje}")


    def log_success(self, test_name: str):
        """Registra un test exitoso"""
        self.tests_pasados += 1
        print(f"✅ [{test_name}] Test pasado")


    def run_test(self, test_func, test_name: str):
        """Ejecuta un test individual"""
        self.tests_totales += 1
        print(f"\n🧪 Ejecutando: {test_name}")
        print("-" * 60)

        try:
            test_func()
            self.log_success(test_name)
        except AssertionError as e:
            self.log_error(test_name, str(e))
        except Exception as e:
            self.log_error(test_name, f"Excepción: {e}")
            import traceback
            traceback.print_exc()


    # ======================================
    # TESTS DE RECORDATORIOS
    # ======================================

    def test_recordatorios_en_db(self):
        """Verifica que existan recordatorios en la DB"""
        recordatorios = self.session.query(MemoryNote).all()

        print(f"   📝 Recordatorios en DB: {len(recordatorios)}")

        if len(recordatorios) == 0:
            self.log_warning("test_recordatorios_en_db", "No hay recordatorios en DB (crear algunos para testing)")
            return

        # Verificar campos requeridos
        for rec in recordatorios[:3]:
            assert rec.contenido or rec.content, f"Recordatorio {rec.id} sin contenido"
            contenido = rec.contenido if hasattr(rec, 'contenido') else rec.content
            print(f"   • [{rec.etiqueta if hasattr(rec, 'etiqueta') else rec.type}] {contenido[:50]}...")


    def test_recordatorios_con_fecha(self):
        """Verifica recordatorios con fecha límite"""
        con_fecha = self.session.query(MemoryNote).filter(
            MemoryNote.fecha_limite.isnot(None)
        ).all()

        print(f"   📅 Recordatorios con fecha: {len(con_fecha)}")

        if len(con_fecha) == 0:
            self.log_warning(
                "test_recordatorios_con_fecha",
                "No hay recordatorios con fecha límite en DB"
            )
            return

        for rec in con_fecha[:3]:
            contenido = rec.contenido if hasattr(rec, 'contenido') else rec.content
            print(f"   • {contenido[:40]} → {rec.fecha_limite}")


    def test_sincronizar_recordatorios_hojas(self):
        """Test de sincronización de recordatorios a todas las hojas"""
        print("   🔄 Iniciando sincronización de recordatorios...")

        try:
            # Ejecutar sincronización
            hojas_actualizadas = actualizar_recordatorios_todas_las_hojas()

            assert hojas_actualizadas > 0, "No se actualizó ninguna hoja"

            print(f"   ✓ {hojas_actualizadas} hojas actualizadas exitosamente")

        except Exception as e:
            raise AssertionError(f"Error en sincronización: {e}")


    def test_verificar_recordatorios_en_sheets(self):
        """Verifica que los recordatorios aparezcan en Google Sheets"""
        print("   🔍 Verificando presencia en Google Sheets...")

        # Obtener hoja actual
        try:
            sheet = SHEETS_MANAGER.obtener_hoja_por_fecha(date.today())
        except Exception as e:
            sheet = get_sheet()

        # Leer columnas I y J (recordatorios)
        try:
            col_i = sheet.col_values(9)  # Columna I (con fecha)
            col_j = sheet.col_values(10)  # Columna J (sin fecha)

            recordatorios_sheets = [v for v in col_i + col_j if v.strip()]

            print(f"   📝 Recordatorios en Sheets: {len(recordatorios_sheets)}")

            if len(recordatorios_sheets) == 0:
                self.log_warning(
                    "test_verificar_recordatorios_en_sheets",
                    "No se encontraron recordatorios en Sheets (puede ser normal si no hay recordatorios)"
                )
                return

            # Mostrar primeros 3
            for i, rec in enumerate(recordatorios_sheets[:3], 1):
                print(f"   {i}. {rec[:60]}...")

        except Exception as e:
            raise AssertionError(f"Error al leer Sheets: {e}")


    # ======================================
    # TESTS DE EVENTOS
    # ======================================

    def test_eventos_en_db(self):
        """Verifica que existan eventos en la DB"""
        eventos = self.session.query(Evento).all()

        print(f"   📅 Eventos en DB: {len(eventos)}")

        if len(eventos) == 0:
            self.log_warning("test_eventos_en_db", "No hay eventos en DB (crear algunos para testing)")
            return

        # Verificar campos críticos
        for ev in eventos[:3]:
            assert ev.nombre, f"Evento {ev.id} sin nombre"
            assert ev.fecha_inicio, f"Evento {ev.id} sin fecha_inicio"
            assert ev.hora_inicio, f"Evento {ev.id} sin hora_inicio"
            assert ev.hora_fin, f"Evento {ev.id} sin hora_fin"

            print(f"   • {ev.nombre} → {ev.fecha_inicio} {ev.hora_inicio}-{ev.hora_fin}")


    def test_eventos_recurrentes(self):
        """Verifica sistema de recurrencia"""
        # Buscar eventos maestros (recurrentes)
        maestros = self.session.query(Evento).filter(
            Evento.evento_maestro_id.is_(None),
            Evento.recurrencia != 'único'
        ).all()

        print(f"   🔁 Eventos recurrentes en DB: {len(maestros)}")

        if len(maestros) == 0:
            self.log_warning(
                "test_eventos_recurrentes",
                "No hay eventos recurrentes maestros en DB"
            )
            return

        # Mostrar info del primer maestro
        maestro = maestros[0]
        print(f"   • Maestro: {maestro.nombre} ({maestro.recurrencia})")
        print(f"   • Fecha inicio: {maestro.fecha_inicio}")


    def test_pintar_evento_sheets(self):
        """Verifica que se puedan pintar eventos en Sheets"""
        print("   🎨 Probando pintado de evento de prueba...")

        # Buscar evento de esta semana
        hoy = date.today()
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)

        eventos_semana = self.session.query(Evento).filter(
            Evento.fecha_inicio >= inicio_semana,
            Evento.fecha_inicio <= fin_semana
        ).all()

        if len(eventos_semana) == 0:
            self.log_warning(
                "test_pintar_evento_sheets",
                "No hay eventos esta semana para probar pintado"
            )
            return

        evento = eventos_semana[0]

        print(f"   • Evento de prueba: {evento.nombre}")
        print(f"   • Fecha: {evento.fecha_inicio}")

        try:
            resultado = pintar_evento_sheets(evento)

            assert resultado is True, "pintar_evento_sheets retornó False"

            print("   ✓ Evento pintado exitosamente")

        except Exception as e:
            raise AssertionError(f"Error al pintar evento: {e}")


    # ======================================
    # TESTS DE HOJAS MÚLTIPLES
    # ======================================

    def test_hojas_semanales_existen(self):
        """Verifica que existan hojas semanales"""
        try:
            spreadsheet = SHEETS_MANAGER.spreadsheet
            hojas = spreadsheet.worksheets()

            hojas_semanales = [h.title for h in hojas if '-' in h.title and 'Copia' not in h.title]

            print(f"   📑 Hojas semanales encontradas: {len(hojas_semanales)}")

            assert len(hojas_semanales) >= 1, "No se encontraron hojas semanales"

            # Mostrar primeras 5
            for hoja in hojas_semanales[:5]:
                print(f"   • {hoja}")

        except Exception as e:
            raise AssertionError(f"Error al obtener hojas: {e}")


    def test_hoja_template_existe(self):
        """Verifica que exista la hoja template"""
        try:
            template = SHEETS_MANAGER.template_sheet

            if template is None:
                raise AssertionError("No se encontró hoja template")

            print(f"   📄 Template encontrado: {template.title}")

        except Exception as e:
            raise AssertionError(f"Error: {e}")


    def test_obtener_hoja_por_fecha(self):
        """Verifica que se pueda obtener hoja por fecha"""
        print("   📅 Probando obtener_hoja_por_fecha...")

        try:
            hoy = date.today()
            hoja = SHEETS_MANAGER.obtener_hoja_por_fecha(hoy)

            assert hoja is not None, "No se pudo obtener hoja para hoy"

            print(f"   • Hoja para hoy: {hoja.title}")

            # Probar con fecha futura
            futuro = hoy + timedelta(days=14)
            hoja_futura = SHEETS_MANAGER.obtener_hoja_por_fecha(futuro)

            print(f"   • Hoja para {futuro}: {hoja_futura.title}")

        except Exception as e:
            raise AssertionError(f"Error: {e}")


    # ======================================
    # TESTS DE OPTIMIZACIÓN
    # ======================================

    def test_batch_manager_disponible(self):
        """Verifica que el batch manager esté disponible"""
        print("   📦 Verificando batch manager...")

        try:
            from modules.agenda.sheets_batch_manager import SheetsBatchManager

            spreadsheet = SHEETS_MANAGER.spreadsheet
            manager = SheetsBatchManager(spreadsheet.client, spreadsheet.id)

            print(f"   ✓ Batch manager inicializado")
            print(f"   • Worksheets en cache: {len(manager._worksheets_cache)}")

            manager.print_stats()

        except ImportError:
            raise AssertionError("No se pudo importar SheetsBatchManager - ¿está creado el archivo?")
        except Exception as e:
            raise AssertionError(f"Error al inicializar batch manager: {e}")


    # ======================================
    # EJECUTAR TODOS LOS TESTS
    # ======================================

    def run_all(self):
        """Ejecuta toda la suite de tests"""
        print("\n" + "="*70)
        print("🧪 INICIANDO SUITE DE TESTS - LOBO FASE 2")
        print("="*70)

        inicio = time.time()

        # Tests de Recordatorios
        print("\n" + "─"*70)
        print("📝 TESTS DE RECORDATORIOS")
        print("─"*70)
        self.run_test(self.test_recordatorios_en_db, "Recordatorios en DB")
        self.run_test(self.test_recordatorios_con_fecha, "Recordatorios con fecha")
        self.run_test(self.test_sincronizar_recordatorios_hojas, "Sincronización a hojas")
        self.run_test(self.test_verificar_recordatorios_en_sheets, "Verificar en Sheets")

        # Tests de Eventos
        print("\n" + "─"*70)
        print("📅 TESTS DE AGENDA")
        print("─"*70)
        self.run_test(self.test_eventos_en_db, "Eventos en DB")
        self.run_test(self.test_eventos_recurrentes, "Sistema de recurrencia")
        self.run_test(self.test_pintar_evento_sheets, "Pintar eventos en Sheets")

        # Tests de Hojas Múltiples
        print("\n" + "─"*70)
        print("📑 TESTS DE HOJAS MÚLTIPLES")
        print("─"*70)
        self.run_test(self.test_hojas_semanales_existen, "Hojas semanales")
        self.run_test(self.test_hoja_template_existe, "Hoja template")
        self.run_test(self.test_obtener_hoja_por_fecha, "Obtener hoja por fecha")

        # Tests de Optimización
        print("\n" + "─"*70)
        print("⚡ TESTS DE OPTIMIZACIÓN")
        print("─"*70)
        self.run_test(self.test_batch_manager_disponible, "Batch manager")

        # Resumen final
        duracion = time.time() - inicio

        print("\n" + "="*70)
        print("📊 RESUMEN DE TESTS")
        print("="*70)
        print(f"✅ Tests pasados: {self.tests_pasados}/{self.tests_totales}")
        print(f"❌ Tests fallidos: {len(self.errores)}")
        print(f"⚠️ Warnings: {len(self.warnings)}")
        print(f"⏱️ Tiempo total: {duracion:.2f}s")
        print("="*70)

        # Mostrar errores
        if self.errores:
            print("\n❌ ERRORES ENCONTRADOS:")
            for error in self.errores:
                print(f"  {error}")

        # Mostrar warnings
        if self.warnings:
            print("\n⚠️ ADVERTENCIAS:")
            for warning in self.warnings:
                print(f"  {warning}")

        # Resultado final
        if len(self.errores) == 0:
            print("\n🎉 ¡TODOS LOS TESTS PASARON!")
            return True
        else:
            print("\n💥 ALGUNOS TESTS FALLARON - Revisar errores arriba")
            return False


    def __del__(self):
        """Cierra la sesión al destruir el objeto"""
        if hasattr(self, 'session'):
            self.session.close()


# ============================================
# EJECUCIÓN PRINCIPAL
# ============================================

if __name__ == "__main__":
    print("🐺 LOBO - Suite de Testing Fase 2")
    print("Verificando sincronización DB ↔ Google Sheets")
    print()

    tester = TestSincronizacion()
    exito = tester.run_all()

    sys.exit(0 if exito else 1)
