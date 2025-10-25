if __name__ == "__main__":
    from core.brain import Brain
    from interface.cli import CLI
    from core.dashboard import mostrar_dashboard
    from modules.recordatorios.recordatorios import Recordatorios

    # 💥 Crear las tablas ANTES detodo
    from core.db.schema import Base
    from core.db.sessions import engine

    # Crea las tablas en la base de datos
    Base.metadata.create_all(bind=engine)

    # Autenticación
    from core.security import auth
    if not auth.authenticate():
        exit(1)

    # Cargar módulos
    from core import loader
    loader.load_modules()

    # Inicializar brain y CLI
    brain = Brain()
    cli = CLI(brain)

    # ===== MOSTRAR DASHBOARD =====
    dashboard = mostrar_dashboard()

    # ===== VERIFICAR RECORDATORIOS VENCIDOS =====
    if dashboard.tiene_vencidos():
        recordatorios_obj = Recordatorios()
        recordatorios_obj.menu_vencidos()

    # ===== SINCRONIZAR RECORDATORIOS CON SHEETS (opcional, comentar si es lento) =====
    try:
        from modules.recordatorios.recordatorios_sheets import actualizar_recordatorios_sheets

        print("🔄 Sincronizando recordatorios con Google Sheets...")
        actualizar_recordatorios_sheets()
        print("✅ Sincronización completa\n")
    except Exception as e:
        print(f"⚠️  No se pudo sincronizar con Sheets: {e}\n")

    # Ejecutar CLI
    cli.run()
