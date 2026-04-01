# modules/agenda/agenda_fixes.py
"""
Correcciones críticas para el módulo de agenda:
1. Ordenamiento correcto de hojas por fecha
2. Sincronización real DB ↔ Sheets
3. Limpieza profunda de eventos fantasma
4. Guardar plantilla desde cualquier hoja
5. Limpieza de eventos pasados en DB
"""

from datetime import datetime, date, timedelta
from pathlib import Path
import json
import re
from typing import List, Dict, Optional, Tuple
from core.db.sessions import SessionLocal
from core.db.schema import Evento
from core.context.logs import BITACORA
from core.context.global_session import SESSION
import gspread


# ============================================================================
# FIX #1: Parser de nombres de hojas + Ordenamiento correcto
# ============================================================================

class HojaParser:
    """
    Parser robusto para nombres de hojas en español
    Soporta formatos: "05-11 ene.", "26 ene. - 01 feb.", "29 dic. - 04 ene."
    """

    MESES = {
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4,
        'may': 5, 'jun': 6, 'jul': 7, 'ago': 8,
        'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
    }

    @classmethod
    def parsear_nombre_hoja(cls, nombre: str) -> Optional[date]:
        """
        Extrae la fecha de inicio (lunes) de un nombre de hoja

        Returns:
            date del lunes de esa semana, o None si no puede parsear
        """
        # Normalizar nombre
        nombre = nombre.lower().strip().replace('.', '').replace(',', '')

        # Patrón 1: "05-11 ene" (mismo mes)
        pattern1 = r'(\d{1,2})-\d{1,2}\s+(\w+)'
        match = re.match(pattern1, nombre)
        if match:
            dia = int(match.group(1))
            mes_str = match.group(2)
            mes = cls.MESES.get(mes_str[:3])
            if mes:
                # Determinar año (si mes es diciembre y estamos en enero, año anterior)
                hoy = date.today()
                año = hoy.year
                if mes == 12 and hoy.month == 1:
                    año -= 1
                elif mes > hoy.month + 1:  # Hoja futura del año pasado
                    año -= 1

                try:
                    return date(año, mes, dia)
                except ValueError:
                    pass

        # Patrón 2: "26 ene - 01 feb" (cambia de mes)
        pattern2 = r'(\d{1,2})\s+(\w+)\s*-\s*\d{1,2}\s+(\w+)'
        match = re.match(pattern2, nombre)
        if match:
            dia = int(match.group(1))
            mes_str = match.group(2)
            mes = cls.MESES.get(mes_str[:3])
            if mes:
                hoy = date.today()
                año = hoy.year

                # Caso especial: "29 dic - 04 ene" (cambio de año)
                mes_fin_str = match.group(3)
                mes_fin = cls.MESES.get(mes_fin_str[:3])
                if mes == 12 and mes_fin == 1:
                    # Si estamos en enero, la hoja es del diciembre pasado
                    if hoy.month == 1:
                        año -= 1

                try:
                    return date(año, mes, dia)
                except ValueError:
                    pass

        return None

    @classmethod
    def ordenar_hojas(cls, hojas: List[gspread.Worksheet]) -> List[gspread.Worksheet]:
        """
        Ordena hojas cronológicamente por su fecha
        Mantiene hojas especiales (Sheet1, Hoja 1, templates) al final
        """
        hojas_con_fecha = []
        hojas_especiales = []

        for hoja in hojas:
            nombre = hoja.title

            # Identificar hojas especiales
            if any(x in nombre.lower() for x in ['sheet', 'hoja', 'copia', 'template', 'plantilla']):
                hojas_especiales.append((None, hoja))
                continue

            # Parsear fecha
            fecha = cls.parsear_nombre_hoja(nombre)
            if fecha:
                hojas_con_fecha.append((fecha, hoja))
            else:
                hojas_especiales.append((None, hoja))

        # Ordenar por fecha
        hojas_con_fecha.sort(key=lambda x: x[0])

        # Retornar: hojas con fecha + especiales
        return [h for _, h in hojas_con_fecha] + [h for _, h in hojas_especiales]


# ============================================================================
# FIX #2: Sincronización REAL DB ↔ Sheets
# ============================================================================

class SincronizadorReal:
    """
    Sincronización bidireccional real entre DB y Sheets
    Elimina eventos fantasma y mantiene consistencia
    """

    def __init__(self):
        from core.lobo_google.lobo_sheets import get_spreadsheet
        self.spreadsheet = get_spreadsheet()
        self.session = SessionLocal()

    def obtener_eventos_db(self, fecha_inicio: date, fecha_fin: date) -> Dict[str, Evento]:
        """
        Obtiene eventos de DB en un rango de fechas
        Returns: Dict[id_evento -> Evento]
        """
        eventos = self.session.query(Evento).filter(
            Evento.fecha_inicio >= fecha_inicio,
            Evento.fecha_inicio <= fecha_fin,
            Evento.es_maestro == False
        ).all()

        return {ev.id: ev for ev in eventos}

    def limpiar_hoja_completa(self, hoja: gspread.Worksheet):
        """
        Limpia TODA la hoja (excepto headers y columna de horas)
        """
        from modules.agenda.agenda_optimizer import SAFE_SHEETS

        print(f"   🧹 Limpiando hoja '{hoja.title}'...")

        # Limpiar área de eventos (B2:H31)
        try:
            SAFE_SHEETS.safe_batch_clear(hoja, ["B2:H31"])
        except Exception as e:
            print(f"      ⚠️  Error limpiando eventos: {e}")

        # Limpiar columnas de recordatorios (I1:J60)
        try:
            SAFE_SHEETS.safe_batch_clear(hoja, ["I1:J60"])
        except Exception as e:
            print(f"      ⚠️  Error limpiando recordatorios: {e}")

        # Limpiar formatos
        sheet_id = hoja._properties["sheetId"]
        requests = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,  # Fila 2
                        "endRowIndex": 31,  # Fila 31
                        "startColumnIndex": 1,  # Columna B
                        "endColumnIndex": 8  # Columna H
                    },
                    "cell": {"userEnteredFormat": {}},
                    "fields": "userEnteredFormat"
                }
            }
        ]

        try:
            SAFE_SHEETS.safe_batch_update(hoja, requests)
        except Exception as e:
            print(f"      ⚠️  Error limpiando formatos: {e}")

    def sincronizar_hoja(self, hoja: gspread.Worksheet) -> Tuple[int, int]:
        """
        Sincroniza una hoja específica con la DB

        Returns:
            (eventos_pintados, errores)
        """
        # Parsear fecha de la hoja
        fecha_inicio = HojaParser.parsear_nombre_hoja(hoja.title)

        if not fecha_inicio:
            print(f"   ⚠️  No se pudo parsear fecha de '{hoja.title}'")
            return (0, 1)

        fecha_fin = fecha_inicio + timedelta(days=6)

        # Obtener eventos de DB para esta semana
        eventos_db = self.obtener_eventos_db(fecha_inicio, fecha_fin)

        if not eventos_db:
            print(f"   📭 '{hoja.title}': Sin eventos en DB")
            return (0, 0)

        print(f"   📅 '{hoja.title}': {len(eventos_db)} eventos en DB")

        # Pintar cada evento
        eventos_pintados = 0
        errores = 0

        for evento in eventos_db.values():
            try:
                from modules.agenda.agenda_logics import pintar_evento_sheets
                pintar_evento_sheets(evento)
                eventos_pintados += 1
            except Exception as e:
                print(f"      ❌ Error pintando '{evento.nombre}': {e}")
                errores += 1

        return (eventos_pintados, errores)

    def sincronizar_todas_las_hojas(self) -> Dict[str, any]:
        """
        Sincronización completa: limpia y repinta TODAS las hojas
        """
        print("\n" + "=" * 70)
        print("SINCRONIZACIÓN REAL DB ↔ SHEETS")
        print("=" * 70)

        # Obtener todas las hojas
        hojas = self.spreadsheet.worksheets()

        # Ordenar cronológicamente
        hojas_ordenadas = HojaParser.ordenar_hojas(hojas)

        # Filtrar hojas de agenda (excluir especiales)
        hojas_agenda = []
        for hoja in hojas_ordenadas:
            if HojaParser.parsear_nombre_hoja(hoja.title):
                hojas_agenda.append(hoja)

        print(f"\n📋 Hojas de agenda encontradas: {len(hojas_agenda)}")
        print(f"   (Hojas especiales ignoradas: {len(hojas) - len(hojas_agenda)})\n")

        # Sincronizar cada hoja
        total_pintados = 0
        total_errores = 0

        for i, hoja in enumerate(hojas_agenda, 1):
            print(f"\n[{i}/{len(hojas_agenda)}] Procesando '{hoja.title}'...")

            # Limpiar completamente
            self.limpiar_hoja_completa(hoja)

            # Repintar desde DB
            pintados, errores = self.sincronizar_hoja(hoja)
            total_pintados += pintados
            total_errores += errores

            print(f"      ✅ {pintados} eventos pintados")
            if errores > 0:
                print(f"      ⚠️  {errores} errores")

        # Resumen
        print("\n" + "=" * 70)
        print("📊 RESUMEN")
        print("=" * 70)
        print(f"   Hojas procesadas: {len(hojas_agenda)}")
        print(f"   Eventos pintados: {total_pintados}")
        print(f"   Errores: {total_errores}")
        print("=" * 70 + "\n")

        BITACORA.registrar("agenda", "sincronizacion_real",
                           f"{len(hojas_agenda)} hojas, {total_pintados} eventos",
                           SESSION.user.username if SESSION.user else "system")

        return {
            'hojas_procesadas': len(hojas_agenda),
            'eventos_pintados': total_pintados,
            'errores': total_errores
        }

    def __del__(self):
        """Cerrar sesión al destruir objeto"""
        if hasattr(self, 'session'):
            self.session.close()


# ============================================================================
# FIX #3: Limpieza de eventos pasados en DB
# ============================================================================

class LimpiadorDB:
    """
    Limpia eventos pasados de la base de datos
    """

    @staticmethod
    def listar_eventos_pasados(semanas_atras: int = 4) -> List[Evento]:
        """
        Lista eventos pasados más allá de N semanas
        """
        session = SessionLocal()

        fecha_limite = date.today() - timedelta(weeks=semanas_atras)

        eventos = session.query(Evento).filter(
            Evento.fecha_inicio < fecha_limite,
            Evento.es_maestro == False
        ).order_by(Evento.fecha_inicio).all()

        session.close()
        return eventos

    @staticmethod
    def eliminar_eventos_pasados(semanas_atras: int = 4,
                                 preservar_maestros: bool = True) -> int:
        """
        Elimina eventos pasados de la DB

        Args:
            semanas_atras: Cuántas semanas hacia atrás preservar
            preservar_maestros: Si True, no elimina eventos maestros

        Returns:
            Número de eventos eliminados
        """
        session = SessionLocal()

        fecha_limite = date.today() - timedelta(weeks=semanas_atras)

        query = session.query(Evento).filter(
            Evento.fecha_inicio < fecha_limite
        )

        if preservar_maestros:
            query = query.filter(Evento.es_maestro == False)

        eventos = query.all()
        count = len(eventos)

        # Eliminar
        for evento in eventos:
            session.delete(evento)

        session.commit()
        session.close()

        return count


# ============================================================================
# FIX #4: Guardar plantilla desde cualquier hoja
# ============================================================================

class PlantillaFlexible:
    """
    Sistema de plantillas mejorado que permite seleccionar hoja específica
    """

    def __init__(self):
        self.plantillas_dir = Path("data/plantillas_semanas")
        self.plantillas_dir.mkdir(parents=True, exist_ok=True)
        from core.lobo_google.lobo_sheets import get_spreadsheet
        self.spreadsheet = get_spreadsheet()

    def listar_hojas_disponibles(self) -> List[Tuple[str, Optional[date]]]:
        """
        Lista todas las hojas con sus fechas parseadas

        Returns:
            List[(nombre_hoja, fecha_inicio)]
        """
        hojas = self.spreadsheet.worksheets()
        resultado = []

        for hoja in hojas:
            fecha = HojaParser.parsear_nombre_hoja(hoja.title)
            resultado.append((hoja.title, fecha))

        # Ordenar por fecha (None al final)
        resultado.sort(key=lambda x: x[1] if x[1] else date.max)

        return resultado

    def guardar_plantilla_desde_hoja(self, nombre_hoja: str,
                                     nombre_plantilla: str) -> bool:
        """
        Guarda una plantilla desde una hoja específica del spreadsheet

        Args:
            nombre_hoja: Nombre exacto de la hoja en el spreadsheet
            nombre_plantilla: Nombre personalizado para la plantilla
        """
        # Buscar hoja
        try:
            hoja = self.spreadsheet.worksheet(nombre_hoja)
        except gspread.exceptions.WorksheetNotFound:
            print(f"❌ Hoja '{nombre_hoja}' no encontrada")
            return False

        # Parsear fecha de la hoja
        fecha_inicio = HojaParser.parsear_nombre_hoja(nombre_hoja)

        if not fecha_inicio:
            print(f"⚠️  No se pudo parsear fecha de '{nombre_hoja}'")
            print("   Intentando guardar eventos de la hoja de todas formas...")

        # Obtener eventos de DB para esta semana
        session = SessionLocal()

        if fecha_inicio:
            fecha_fin = fecha_inicio + timedelta(days=6)
            eventos = session.query(Evento).filter(
                Evento.fecha_inicio >= fecha_inicio,
                Evento.fecha_inicio <= fecha_fin,
                Evento.es_maestro == False
            ).all()
        else:
            # Si no hay fecha, intentar obtener eventos recientes
            print("   Guardando eventos de las últimas 2 semanas...")
            hace_2_semanas = date.today() - timedelta(weeks=2)
            eventos = session.query(Evento).filter(
                Evento.fecha_inicio >= hace_2_semanas,
                Evento.es_maestro == False
            ).all()

        session.close()

        if not eventos:
            print(f"❌ No hay eventos en la hoja '{nombre_hoja}'")
            return False

        # Crear estructura de plantilla
        plantilla_data = {
            'nombre': nombre_plantilla,
            'nombre_hoja_origen': nombre_hoja,
            'fecha_origen': fecha_inicio.isoformat() if fecha_inicio else None,
            'descripcion': f"Plantilla creada desde hoja '{nombre_hoja}'",
            'creada': datetime.now().isoformat(),
            'eventos': []
        }

        # Convertir eventos a formato de plantilla
        for evento in eventos:
            plantilla_data['eventos'].append({
                'nombre': evento.nombre,
                'descripcion': evento.descripcion or '',
                'dia_semana': evento.fecha_inicio.weekday(),
                'hora_inicio': evento.hora_inicio.strftime('%H:%M'),
                'hora_fin': evento.hora_fin.strftime('%H:%M'),
                'tipo_evento': evento.tipo_evento,
                'etiquetas': evento.etiquetas,
                'alarma_minutos': evento.alarma_minutos,
                'alarma_activa': evento.alarma_activa
            })

        # Guardar JSON
        filename = f"{nombre_plantilla.lower().replace(' ', '_')}.json"
        filepath = self.plantillas_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(plantilla_data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Plantilla '{nombre_plantilla}' guardada")
        print(f"   📋 Origen: Hoja '{nombre_hoja}'")
        print(f"   📊 Eventos: {len(eventos)}")
        print(f"   📁 Archivo: {filepath}\n")

        BITACORA.registrar("agenda", "plantilla_desde_hoja",
                           f"'{nombre_plantilla}' desde '{nombre_hoja}' con {len(eventos)} eventos",
                           SESSION.user.username if SESSION.user else "system")

        return True


# ============================================================================
# FIX #5: Reordenar hojas en el spreadsheet
# ============================================================================

class ReordenadorHojas:
    """
    Reordena físicamente las hojas en el spreadsheet
    """

    @staticmethod
    def reordenar_hojas():
        """
        Reordena todas las hojas cronológicamente
        Mantiene hojas especiales al final
        """
        from core.lobo_google.lobo_sheets import get_spreadsheet
        from modules.agenda.agenda_optimizer import SAFE_SHEETS

        print("\n" + "=" * 70)
        print("REORDENAMIENTO DE HOJAS")
        print("=" * 70)

        spreadsheet = get_spreadsheet()
        hojas = spreadsheet.worksheets()

        print(f"\n📋 Hojas actuales: {len(hojas)}")
        print("\nOrden actual:")
        for i, h in enumerate(hojas, 1):
            print(f"   {i}. {h.title}")

        # Ordenar
        hojas_ordenadas = HojaParser.ordenar_hojas(hojas)

        print("\n✨ Nuevo orden propuesto:")
        for i, h in enumerate(hojas_ordenadas, 1):
            print(f"   {i}. {h.title}")

        # Confirmar
        print("\n" + "=" * 70)
        confirm = input("¿Aplicar este orden? [Y/N]: ").strip().upper()

        if confirm != "Y":
            print("\n❎ Cancelado")
            return False

        # Aplicar reordenamiento
        print("\n🔄 Reordenando...")

        for i, hoja in enumerate(hojas_ordenadas):
            try:
                # gspread usa índice 0-based para update_index
                hoja.update_index(i)
                print(f"   ✅ '{hoja.title}' → posición {i + 1}")
            except Exception as e:
                print(f"   ❌ Error con '{hoja.title}': {e}")

        print("\n✅ Reordenamiento completado")
        print("=" * 70 + "\n")

        return True


# ============================================================================
# COMANDOS DE USUARIO
# ============================================================================

def comando_sincronizar_real(args):
    """Sincronización REAL DB → Sheets (limpia y repinta todo)"""
    sync = SincronizadorReal()
    resultado = sync.sincronizar_todas_las_hojas()
    return f"[LOBO] ✅ Sincronización completada: {resultado['eventos_pintados']} eventos"


def comando_limpiar_db_pasados(args):
    """Limpia eventos pasados de la DB"""
    # Listar primero
    if not args or args[0] == "ver":
        semanas = 4
        eventos = LimpiadorDB.listar_eventos_pasados(semanas)

        if not eventos:
            return f"[LOBO] No hay eventos pasados (>{semanas} semanas)"

        print(f"\n📋 Eventos pasados encontrados (>{semanas} semanas): {len(eventos)}\n")

        # Agrupar por mes
        por_mes = {}
        for ev in eventos:
            mes_key = ev.fecha_inicio.strftime("%Y-%m")
            if mes_key not in por_mes:
                por_mes[mes_key] = []
            por_mes[mes_key].append(ev)

        for mes, evs in sorted(por_mes.items()):
            print(f"   {mes}: {len(evs)} eventos")

        print(f"\nUsa: limpiar_db_pasados eliminar [semanas]")
        return ""

    # Eliminar
    if args[0] == "eliminar":
        semanas = int(args[1]) if len(args) > 1 else 4

        eventos = LimpiadorDB.listar_eventos_pasados(semanas)

        if not eventos:
            return f"[LOBO] No hay eventos para eliminar"

        print(f"\n⚠️  Se eliminarán {len(eventos)} eventos (>{semanas} semanas)")
        confirm = input("¿Continuar? [Y/N]: ").strip().upper()

        if confirm != "Y":
            return "[LOBO] ❎ Cancelado"

        count = LimpiadorDB.eliminar_eventos_pasados(semanas)

        BITACORA.registrar("agenda", "limpiar_db_pasados",
                           f"{count} eventos eliminados (>{semanas} semanas)",
                           SESSION.user.username if SESSION.user else "system")

        return f"[LOBO] ✅ {count} eventos eliminados"


def comando_guardar_plantilla_desde(args):
    """Guarda plantilla desde hoja específica"""
    if len(args) < 2:
        # Mostrar hojas disponibles
        plantilla = PlantillaFlexible()
        hojas = plantilla.listar_hojas_disponibles()

        print("\n📋 Hojas disponibles:\n")
        for nombre, fecha in hojas:
            if fecha:
                print(f"   • {nombre} ({fecha.strftime('%d/%m/%Y')})")
            else:
                print(f"   • {nombre} (hoja especial)")

        print("\nUso: guardar_plantilla_desde \"<nombre_hoja>\" \"<nombre_plantilla>\"")
        print("Ejemplo: guardar_plantilla_desde \"12-18 ene.\" \"Universidad Típica\"")
        return ""

    nombre_hoja = args[0]
    nombre_plantilla = " ".join(args[1:])

    plantilla = PlantillaFlexible()

    if plantilla.guardar_plantilla_desde_hoja(nombre_hoja, nombre_plantilla):
        return "[LOBO] ✅ Plantilla guardada"
    else:
        return "[LOBO] ❌ Error al guardar plantilla"


def comando_reordenar_hojas(args):
    """Reordena hojas cronológicamente"""
    if ReordenadorHojas.reordenar_hojas():
        return "[LOBO] ✅ Hojas reordenadas"
    else:
        return "[LOBO] ❎ Operación cancelada"


# ============================================================================
# EXPORTAR
# ============================================================================

COMANDOS_FIXES = {
    "sincronizar_real": comando_sincronizar_real,
    "limpiar_db_pasados": comando_limpiar_db_pasados,
    "guardar_plantilla_desde": comando_guardar_plantilla_desde,
    "reordenar_hojas": comando_reordenar_hojas,
}
