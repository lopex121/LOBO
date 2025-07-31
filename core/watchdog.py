class Watchdog:
    def __init__(self):
        self.status = "OK"

    def heartbeat(self):
        return self.status