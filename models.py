from dataclasses import dataclass
from datetime import datetime

@dataclass
class Note:
    id: str
    title: str
    content: str
    date: datetime
    folder: str