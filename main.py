if __name__ == "__main__":
    from core.brain import Brain
    from interface.cli import CLI

    # 💥 Crear las tablas ANTES detodo
    from core.db.schema import Base
    from core.db.sessions import engine

    # Crea las tablas en la base de datos
    Base.metadata.create_all(bind=engine)

    from core.security import auth
    if not auth.authenticate():
        exit(1)

    from core import loader
    loader.load_modules()

    from core.db.schema import Base
    from core.db.sessions import engine

    brain = Brain()
    cli = CLI(brain)
    cli.run()