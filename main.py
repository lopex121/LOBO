if __name__ == "__main__":
    from core.brain import Brain
    from interface.cli import CLI
    from core import auth

    if not auth.verificar_clave():
        exit(1)

    from core import loader
    loader.load_modules()

    from core.db.schema import Base
    from core.db.sessions import engine

    # Crea las tablas en la base de datos
    Base.metadata.create_all(bind=engine)

    brain = Brain()
    cli = CLI(brain)
    cli.run()