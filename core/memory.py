# core/memory.py

from core.db.sessions import SessionLocal
from core.db.schema import MemoryNote
from sqlalchemy import and_, func
from sqlalchemy.orm.exc import NoResultFound

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
        if mem_type is None:
            print("[LOBO] Debes especificar la etiqueta para usar búsqueda parcial.")
            return False

        if len(contenido.split()) < 3:
            print("[LOBO] Escribe al menos 3 palabras para eliminar con coincidencia parcial.")
            return False

        pattern = f"%{contenido.strip()}%"
        query = self.db.query(MemoryNote).filter(
            and_(
                MemoryNote.type == mem_type,
                func.lower(MemoryNote.content).like(pattern.lower())
            )
        )
        resultado = query.first()

        if resultado:
            self.db.delete(resultado)
            self.db.commit()
            return True
        return False

    def buscar_por_contenido(self, texto: str, mem_type: str):
        patron = f"%{texto}%"
        return self.db.query(MemoryNote).filter(
            and_(
                MemoryNote.type == mem_type,
                func.lower(MemoryNote.content).like(func.lower(patron))
            )
        ).all()

    def eliminar_por_id(self, note_id: int) -> bool:
        try:
            nota = self.db.query(MemoryNote).filter(MemoryNote.id == note_id).one()
            self.db.delete(nota)
            self.db.commit()
            return True
        except NoResultFound:
            return False