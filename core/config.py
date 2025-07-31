import json
import os

class Config:
    def __init__(self, path='data/config.json'):
        self.path = path
        self.data = self.load_config()

    def load_config(self):
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                return json.load(f)
        return {}

    def save_config(self):
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=4)