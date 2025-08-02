# core/memory.py

from core.db.sessions import SessionLocal
from core.db.schema import MemoryNote

class Memory:
    def __init__(self):
        self.db = SessionLocal()

    def remember(self, content, mem_type="note"):
        nota = MemoryNote(content=content, type=mem_type)
        self.db.add(nota)
        self.db.commit()

    def recall(self, mem_type=None):
        if mem_type:
            return self.db.query(MemoryNote).filter_by(type=mem_type).all()
        return self.db.query(MemoryNote).all()

    def delete(self, contenido: str, mem_type=None) -> bool:
        query = self.db.query(MemoryNote).filter(MemoryNote.content == contenido)
        if mem_type:
            query = query.filter(MemoryNote.type == mem_type)
        resultado = query.first()
        if resultado:
            self.db.delete(resultado)
            self.db.commit()
            return True
        return False
