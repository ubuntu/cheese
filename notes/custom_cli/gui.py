"""Custom CLI — Flask web GUI for the note-taking app."""

import os
import tempfile
import webbrowser
import threading
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash
from . import storage as db

app = Flask(__name__, template_folder="templates")
app.secret_key = os.urandom(24)


@app.route("/")
def index():
    notes = db.load()
    tag_filter = request.args.get("tag")
    search_q = request.args.get("q", "").strip()
    filtered = notes
    if tag_filter:
        filtered = [n for n in filtered if tag_filter in n.get("tags", [])]
    if search_q:
        q = search_q.lower()
        filtered = [n for n in filtered
                    if q in n["title"].lower() or q in n["content"].lower()
                    or q in " ".join(n.get("tags", [])).lower()]
    from collections import Counter
    tags = Counter(t for n in notes for t in n.get("tags", []))
    return render_template("index.html", notes=filtered, tags=tags,
                           tag_filter=tag_filter, search_q=search_q, total=len(notes))


@app.route("/note/new", methods=["GET", "POST"])
def new_note():
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"]
        tags = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
        if not title:
            flash("Title is required.", "danger")
            return render_template("edit.html", note=None, tags_str="")
        notes = db.load()
        note = {"id": db.next_id(notes), "title": title, "content": content,
                "tags": tags, "created": db.now(), "updated": db.now()}
        notes.append(note); db.save(notes)
        flash(f"Note #{note['id']} created!", "success")
        return redirect(url_for("view_note", note_id=note["id"]))
    return render_template("edit.html", note=None, tags_str="")


@app.route("/note/<int:note_id>")
def view_note(note_id):
    notes = db.load()
    note = db.find(notes, note_id)
    if not note:
        flash(f"Note #{note_id} not found.", "danger")
        return redirect(url_for("index"))
    return render_template("view.html", note=note)


@app.route("/note/<int:note_id>/edit", methods=["GET", "POST"])
def edit_note(note_id):
    notes = db.load()
    note = db.find(notes, note_id)
    if not note:
        flash(f"Note #{note_id} not found.", "danger")
        return redirect(url_for("index"))
    if request.method == "POST":
        note["title"] = request.form["title"].strip()
        note["content"] = request.form["content"]
        note["tags"] = [t.strip() for t in request.form.get("tags", "").split(",") if t.strip()]
        note["updated"] = db.now()
        db.save(notes)
        flash("Note updated.", "success")
        return redirect(url_for("view_note", note_id=note_id))
    return render_template("edit.html", note=note, tags_str=", ".join(note.get("tags", [])))


@app.route("/note/<int:note_id>/delete", methods=["POST"])
def delete_note(note_id):
    db.save([n for n in db.load() if n["id"] != note_id])
    flash("Note deleted.", "info")
    return redirect(url_for("index"))


@app.route("/note/import", methods=["POST"])
def import_note():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("No file selected.", "danger")
        return redirect(url_for("index"))
    filename = file.filename
    suffix = Path(filename).suffix.lower()
    title = Path(filename).stem.replace("_", " ").title()
    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError:
            flash("python-docx not installed. Run: pip install python-docx", "danger")
            return redirect(url_for("index"))
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            file.save(f.name)
            doc = Document(f.name)
            content = "\n".join(p.text for p in doc.paragraphs)
            os.unlink(f.name)
    elif suffix in (".md", ".txt"):
        content = file.read().decode("utf-8", errors="replace")
    else:
        flash(f"Unsupported file type: {suffix}", "danger")
        return redirect(url_for("index"))
    notes = db.load()
    note = {"id": db.next_id(notes), "title": title, "content": content,
            "tags": [], "created": db.now(), "updated": db.now()}
    notes.append(note); db.save(notes)
    flash(f"Imported \"{title}\" as Note #{note['id']}.", "success")
    return redirect(url_for("edit_note", note_id=note["id"]))


def main():
    port = int(os.environ.get("NOTES_PORT", 5000))
    url = f"http://127.0.0.1:{port}"
    print(f"Starting Notes GUI at {url}  (Ctrl+C to stop)")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    app.run(debug=False, host="127.0.0.1", port=port)
