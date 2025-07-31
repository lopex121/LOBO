class CLI:
    def __init__(self, brain):
        self.brain = brain

    def run(self):
        print("Bienvenido a L.O.B.O. — Lex Operativa, Bellum Ordinatum")
        while True:
            try:
                command = input("LOBO > ")
                if command.lower() in ["exit", "quit"]:
                    break
                response = self.brain.handle_command(command)
                print(response)
            except KeyboardInterrupt:
                print("\nSaliendo de LOBO...")
                break