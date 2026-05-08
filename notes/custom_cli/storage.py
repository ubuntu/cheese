"""Shared JSON storage backend for notes."""

import json
import datetime
from pathlib import Path

NOTES_DIR = Path.home() / ".local" / "share" / "notes"
NOTES_FILE = NOTES_DIR / "notes.json"


def load():
    if not NOTES_FILE.exists():
        return []
    with open(NOTES_FILE, encoding="utf-8") as f:
        return json.load(f)


def save(notes):
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)


def next_id(notes):
    return max((n["id"] for n in notes), default=0) + 1


def find(notes, note_id):
    return next((n for n in notes if n["id"] == note_id), None)


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def read_docx(path):
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx is not installed. Run: pip install python-docx")
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)
