import json
import uuid
from pathlib import Path
from datetime import datetime
from models import Note

class NoteRepository:
    def __init__(self, path="notes.json"):
        self.path = Path(path)
        self.notes = []
        self.load()

    def load(self):
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            for item in raw:
                note = Note(
                    id=item["id"],
                    title=item["title"],
                    content=item["content"],
                    date=datetime.fromisoformat(item["date"]),
                    folder=item["folder"]
                )
                self.notes.append(note)

    def save(self):
        data = []
        for n in self.notes:
            data.append({
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "date": n.date.isoformat(),
                "folder": n.folder
            })
        self.path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")

    def add(self, note: Note):
        self.notes.append(note)
        self.save()

    def update(self, note: Note):
        for i, n in enumerate(self.notes):
            if n.id == note.id:
                self.notes[i] = note
                break
        self.save()

    def delete(self, note_id: str):
        self.notes = [n for n in self.notes if n.id != note_id]
        self.save()