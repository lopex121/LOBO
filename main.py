if __name__ == "__main__":
    from core.brain import Brain
    from interface.cli import CLI
    from core import auth

    if not auth.authenticate():
        exit(1)

    from core import loader
    loader.load_modules()
    brain = Brain()
    cli = CLI(brain)
    cli.run()