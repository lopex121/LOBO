# main.py
if __name__ == "__main__":
    from core.brain import Brain
    from interface.cli import CLI
    from core.dashboard import mostrar_dashboard
    from modules.recordatorios.recordatorios import Recordatorios

    # Inicializar base de datos desde la única fuente de verdad
    from core.db.db import init_db
    init_db()

    # Autenticación
    from core.security import auth
    if not auth.authenticate():
        exit(1)

    # Cargar módulos
    from core import loader
    loader.load_modules()

    # Inicializar sistema de hojas múltiples
    try:
        from modules.agenda.sheets_manager import SHEETS_MANAGER
        from core.config import Config

        config = Config()

        if not config.data.get('hojas_inicializadas', False):
            print("🔧 Inicializando sistema de hojas múltiples...")
            resultado = SHEETS_MANAGER.inicializar_sistema()

            if resultado['hojas_creadas'] > 0:
                print(f"   ✅ {resultado['hojas_creadas']} hojas creadas")
                config.data['hojas_inicializadas'] = True
                config.save_config()

    except Exception as e:
        print(f"⚠️  Error al inicializar hojas múltiples: {e}")
        print("   Puedes ejecutar 'inicializar_hojas' manualmente después.")

    # Inicializar brain y CLI
    brain = Brain()
    cli = CLI(brain)

    # Mostrar dashboard
    dashboard = mostrar_dashboard()

    # Verificar recordatorios vencidos
    if dashboard.tiene_vencidos():
        recordatorios_obj = Recordatorios()
        recordatorios_obj.menu_vencidos()

    # Sincronizar recordatorios con Sheets
    try:
        from modules.recordatorios.recordatorios_sheets import actualizar_recordatorios_sheets

        print("🔄 Sincronizando recordatorios con Google Sheets...")
        actualizar_recordatorios_sheets()
        print("✅ Sincronización completa\n")
    except Exception as e:
        print(f"⚠️  No se pudo sincronizar con Sheets: {e}\n")

    # Ejecutar CLI
    cli.run()
