#core/memory.py


import sqlite3

class Memory:
    def __init__(self, db_path='data/memory.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.setup()

    def setup(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        self.conn.commit()

    def remember(self, content, mem_type="note"):
        self.cursor.execute('INSERT INTO memory (type, content) VALUES (?, ?)', (mem_type, content))
        self.conn.commit()

    def recall(self, mem_type=None):
        if mem_type:
            self.cursor.execute("SELECT * FROM memory WHERE type=?", (mem_type,))
        else:
            self.cursor.execute('SELECT * FROM memory')
        return self.cursor.fetchall()

    def delete(self, contenido: str, mem_type=None) -> bool:
        cursor = self.conn.cursor()
        if mem_type:
            cursor.execute(
                "DELETE FROM memory WHERE content = ? AND type = ?",
                (contenido, mem_type),
            )
        else:
            cursor.execute(
                "DELETE FROM memory WHERE content = ?",
                (contenido,),
            )
        self.conn.commit()
        return cursor.rowcount > 0  # True si se eliminó algo