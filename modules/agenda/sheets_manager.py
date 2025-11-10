# modules/agenda/sheets_manager.py
"""
Sistema de gestión de hojas semanales en Google Sheets
- Crea hojas automáticamente
- Archiva hojas antiguas
- Maneja múltiples semanas
"""

from datetime import date, timedelta
import gspread
import logging

logger = logging.getLogger(__name__)

# Configuración
NOMBRE_TEMPLATE = "Copia de Copia de Copia de Copia de Copia de 21-27"
NOMBRE_HISTORIAL = "Horarios pasados"
SEMANAS_FUTURAS = 12


class SheetsManager:
    def __init__(self):
        self.spreadsheet = None
        self.template_sheet = None
        self._cargar_spreadsheet()

    def _cargar_spreadsheet(self):
        """Carga el spreadsheet y el template"""
        # ===== USAR FUNCIÓN QUE NO CAUSA CIRCULAR IMPORT =====
        from core.lobo_google.lobo_sheets import get_spreadsheet

        self.spreadsheet = get_spreadsheet()

        # Buscar template
        try:
            self.template_sheet = self.spreadsheet.worksheet(NOMBRE_TEMPLATE)
            logger.info(f"Template encontrado: {NOMBRE_TEMPLATE}")
        except gspread.exceptions.WorksheetNotFound:
            logger.warning(f"Template '{NOMBRE_TEMPLATE}' no encontrado")
            self.template_sheet = None

    def obtener_lunes_semana(self, fecha=None):
        """Retorna el lunes de la semana para una fecha"""
        if fecha is None:
            fecha = date.today()

        # Calcular lunes (weekday 0)
        dias_desde_lunes = fecha.weekday()
        lunes = fecha - timedelta(days=dias_desde_lunes)

        return lunes

    def nombre_hoja_para_fecha(self, fecha):
        """
        Genera nombre de hoja para una fecha
        Formato: "21-27 Oct"
        """
        lunes = self.obtener_lunes_semana(fecha)
        domingo = lunes + timedelta(days=6)

        # Formato corto
        if lunes.month == domingo.month:
            # Mismo mes: "21-27 Oct"
            nombre = f"{lunes.day:02d}-{domingo.day:02d} {lunes.strftime('%b')}"
        else:
            # Meses diferentes: "28 Oct-03 Nov"
            nombre = f"{lunes.day:02d} {lunes.strftime('%b')}-{domingo.day:02d} {domingo.strftime('%b')}"

        return nombre

    def obtener_hoja_por_fecha(self, fecha):
        """
        Obtiene la hoja correspondiente a una fecha
        Si no existe, la crea

        Returns:
            gspread.Worksheet
        """
        nombre = self.nombre_hoja_para_fecha(fecha)

        try:
            hoja = self.spreadsheet.worksheet(nombre)
            logger.info(f"Hoja encontrada: {nombre}")
            return hoja
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Hoja '{nombre}' no existe, creando...")
            return self.crear_hoja_semana(fecha)

    def crear_hoja_semana(self, fecha):
        """
        Crea una hoja nueva para una semana específica
        Copia el template
        """
        nombre = self.nombre_hoja_para_fecha(fecha)

        if self.template_sheet is None:
            raise Exception(f"Template '{NOMBRE_TEMPLATE}' no disponible")

        try:
            # Duplicar template
            nueva_hoja = self.template_sheet.duplicate(
                new_sheet_name=nombre
            )

            logger.info(f"Hoja creada: {nombre}")
            return nueva_hoja

        except Exception as e:
            logger.error(f"Error al crear hoja {nombre}: {e}")
            raise

    def renombrar_hoja_actual(self):
        """
        Renombra la hoja 2 (hoja actual) al formato de semana
        """
        try:
            # Obtener todas las hojas
            hojas = self.spreadsheet.worksheets()

            if len(hojas) < 2:
                logger.warning("No hay suficientes hojas para renombrar")
                return False

            # Hoja 2 (índice 1)
            hoja_actual = hojas[1]
            hoy = date.today()
            nuevo_nombre = self.nombre_hoja_para_fecha(hoy)

            # Verificar si ya tiene el nombre correcto
            if hoja_actual.title == nuevo_nombre:
                logger.info(f"Hoja ya tiene el nombre correcto: {nuevo_nombre}")
                return True

            # Renombrar
            hoja_actual.update_title(nuevo_nombre)
            logger.info(f"Hoja renombrada: {hoja_actual.title} → {nuevo_nombre}")

            return True

        except Exception as e:
            logger.error(f"Error al renombrar hoja actual: {e}")
            return False

    def crear_hojas_futuras(self, semanas=SEMANAS_FUTURAS):
        """
        Crea hojas para las próximas N semanas (si no existen)

        Returns:
            int: Número de hojas creadas
        """
        hoy = date.today()
        hojas_creadas = 0

        for i in range(semanas):
            fecha_futura = hoy + timedelta(weeks=i)
            nombre = self.nombre_hoja_para_fecha(fecha_futura)

            try:
                # Verificar si existe
                self.spreadsheet.worksheet(nombre)
                logger.info(f"Hoja '{nombre}' ya existe")
            except gspread.exceptions.WorksheetNotFound:
                # No existe, crear
                self.crear_hoja_semana(fecha_futura)
                hojas_creadas += 1

        logger.info(f"{hojas_creadas} hojas nuevas creadas")
        return hojas_creadas

    def archivar_hoja(self, nombre_hoja):
        """
        Mueve una hoja al spreadsheet de historial

        Args:
            nombre_hoja: str - Nombre de la hoja a archivar
        """
        try:
            # ===== USAR get_client EN LUGAR DE REIMPORTAR =====
            from core.lobo_google.lobo_sheets import get_client

            client = get_client()
            spreadsheet_historial = client.open(NOMBRE_HISTORIAL)

            # Obtener hoja a archivar
            hoja_origen = self.spreadsheet.worksheet(nombre_hoja)

            # Copiar a historial
            hoja_origen.copy_to(spreadsheet_historial.id)

            # Eliminar del spreadsheet actual
            self.spreadsheet.del_worksheet(hoja_origen)

            logger.info(f"Hoja '{nombre_hoja}' archivada en '{NOMBRE_HISTORIAL}'")

            # Limpiar historial (mantener solo últimas 8)
            self._limpiar_historial(spreadsheet_historial)

            return True

        except Exception as e:
            logger.error(f"Error al archivar hoja '{nombre_hoja}': {e}")
            return False

    def _limpiar_historial(self, spreadsheet_historial):
        """
        Mantiene solo las últimas 8 semanas en el historial
        """
        try:
            hojas = spreadsheet_historial.worksheets()

            # Si hay más de 8, eliminar las más antiguas
            if len(hojas) > 8:
                hojas_a_eliminar = hojas[:-8]  # Todas excepto últimas 8

                for hoja in hojas_a_eliminar:
                    spreadsheet_historial.del_worksheet(hoja)
                    logger.info(f"Hoja antigua eliminada del historial: {hoja.title}")

        except Exception as e:
            logger.error(f"Error al limpiar historial: {e}")

    def archivar_semanas_antiguas(self):
        """
        Archiva automáticamente hojas de semanas que ya pasaron

        Returns:
            list: Nombres de hojas archivadas
        """
        hoy = date.today()
        hojas_archivadas = []

        # Obtener todas las hojas
        hojas = self.spreadsheet.worksheets()

        for hoja in hojas:
            # Saltar template y hojas especiales
            if hoja.title in [NOMBRE_TEMPLATE, "Sheet1"]:
                continue

            # Intentar parsear el nombre como fecha
            try:
                # Extraer fecha del nombre (ej: "21-27 Oct" → 21 Oct)
                partes = hoja.title.split()
                dia_inicio = int(partes[0].split('-')[0])

                # Simplificación: si el día es menor que hoy.day - 7, archivar
                if dia_inicio < hoy.day - 7:
                    if self.archivar_hoja(hoja.title):
                        hojas_archivadas.append(hoja.title)

            except Exception as e:
                logger.warning(f"No se pudo procesar hoja '{hoja.title}': {e}")
                continue

        return hojas_archivadas

    def inicializar_sistema(self):
        """
        Inicializa el sistema completo de hojas múltiples

        Returns:
            dict: Resultado de la inicialización
        """
        resultado = {
            'hoja_renombrada': False,
            'hojas_creadas': 0,
            'errores': []
        }

        try:
            # 1. Renombrar hoja actual
            if self.renombrar_hoja_actual():
                resultado['hoja_renombrada'] = True
            else:
                resultado['errores'].append("No se pudo renombrar hoja actual")
        except Exception as e:
            resultado['errores'].append(f"Error al renombrar: {e}")

        try:
            # 2. Crear hojas futuras
            hojas_creadas = self.crear_hojas_futuras()
            resultado['hojas_creadas'] = hojas_creadas
        except Exception as e:
            resultado['errores'].append(f"Error al crear hojas futuras: {e}")

        return resultado


# ===== FUNCIÓN AUXILIAR PARA EVITAR CIRCULAR IMPORTS =====
def obtener_hoja_por_fecha_sin_manager(fecha):
    """
    Función helper que NO depende de SHEETS_MANAGER
    Usada por lobo_sheets.get_sheet() para evitar circular import

    Args:
        fecha: date

    Returns:
        gspread.Worksheet
    """
    from core.lobo_google.lobo_sheets import get_spreadsheet

    spreadsheet = get_spreadsheet()

    # Calcular nombre de hoja
    if fecha is None:
        fecha = date.today()

    dias_desde_lunes = fecha.weekday()
    lunes = fecha - timedelta(days=dias_desde_lunes)
    domingo = lunes + timedelta(days=6)

    if lunes.month == domingo.month:
        nombre = f"{lunes.day:02d}-{domingo.day:02d} {lunes.strftime('%b')}"
    else:
        nombre = f"{lunes.day:02d} {lunes.strftime('%b')}-{domingo.day:02d} {domingo.strftime('%b')}"

    try:
        return spreadsheet.worksheet(nombre)
    except gspread.exceptions.WorksheetNotFound:
        # Si no existe, usar sheet1 por defecto (fallback)
        logger.warning(f"Hoja '{nombre}' no encontrada, usando sheet1")
        return spreadsheet.sheet1


# ===== INSTANCIA GLOBAL (INICIALIZACIÓN LAZY) =====
_SHEETS_MANAGER_INSTANCE = None


def get_sheets_manager():
    """
    Obtiene la instancia global de SheetsManager (lazy initialization)

    Returns:
        SheetsManager
    """
    global _SHEETS_MANAGER_INSTANCE

    if _SHEETS_MANAGER_INSTANCE is None:
        _SHEETS_MANAGER_INSTANCE = SheetsManager()

    return _SHEETS_MANAGER_INSTANCE


# ===== ACCESO COMPATIBLE CON CÓDIGO ANTERIOR =====
# En lugar de usar SHEETS_MANAGER directamente, usa get_sheets_manager()
# Pero mantenemos la compatibilidad agregando un getter
class _SheetsManagerProxy:
    """Proxy para mantener compatibilidad con código que usa SHEETS_MANAGER directamente"""

    def __getattr__(self, name):
        return getattr(get_sheets_manager(), name)


SHEETS_MANAGER = _SheetsManagerProxy()
