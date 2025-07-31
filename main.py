if __name__ == "__main__":
    from core.brain import Brain
    from interface.cli import CLI
    from core import auth

    if not auth.verificar_clave():
        exit(1)

    from core import loader
    loader.load_modules()



    if __name__ == "__main__":
        from core.db.manager import init_db
        init_db() # Crea las tablas
        print("Base de datos inicializada correctamente.")

    brain = Brain()
    cli = CLI(brain)
    cli.run()