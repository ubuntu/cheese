#!/usr/bin/env python3
"""Custom CLI — terminal interface for the note-taking app."""

import os
import sys
import argparse
import subprocess
import tempfile
from . import storage as db

RESET  = "\033[0m";  BOLD   = "\033[1m";  GREEN  = "\033[92m"
CYAN   = "\033[96m"; YELLOW = "\033[93m"; RED    = "\033[91m"; DIM = "\033[2m"

def c(text, col): return f"{col}{text}{RESET}"
def header(t):
    print(c("─" * 60, CYAN))
    print(c(f"  {t}", BOLD + CYAN))
    print(c("─" * 60, CYAN))
def rule(): print(c("─" * 60, DIM))


def render_markdown(text):
    import re
    out = []
    in_fence = False
    for line in text.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence; out.append(c(line, DIM)); continue
        if in_fence: out.append(c(line, DIM)); continue
        if   line.startswith("# "):   out.append(c(line[2:], BOLD + CYAN))
        elif line.startswith("## "):  out.append(c(line[3:], BOLD + GREEN))
        elif line.startswith("### "): out.append(c(line[4:], BOLD + YELLOW))
        elif line.startswith(("- ", "* ", "+ ")):
            out.append(c("  •", GREEN) + " " + line[2:])
        else:
            line = re.sub(r"\*\*(.+?)\*\*", lambda m: c(m.group(1), BOLD), line)
            line = re.sub(r"`(.+?)`",       lambda m: c(m.group(1), DIM),  line)
            out.append(line)
    return "\n".join(out)


def open_editor(initial=""):
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(initial); tmp = f.name
    subprocess.call([editor, tmp])
    with open(tmp, encoding="utf-8") as f:
        content = f.read()
    os.unlink(tmp)
    return content


def cmd_new(args):
    title = args.title
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    if args.docx:
        try:
            content = db.read_docx(args.docx)
        except ImportError as e:
            print(c(str(e), RED)); sys.exit(1)
        print(c(f"Imported from {args.docx}", GREEN))
    elif args.content:
        content = args.content
    else:
        content = open_editor(f"# {title}\n\n")

    notes = db.load()
    note = {"id": db.next_id(notes), "title": title, "content": content,
            "tags": tags, "created": db.now(), "updated": db.now()}
    notes.append(note); db.save(notes)
    print(c(f"✔ Note #{note['id']} created: {title}", GREEN))


def cmd_list(args):
    notes = db.load()
    tag_filter = getattr(args, "tag", None)
    header("All Notes" if not tag_filter else f"Notes tagged: {tag_filter}")
    shown = 0
    for n in notes:
        if tag_filter and tag_filter not in n["tags"]: continue
        tags_str = (" [" + ", ".join(n["tags"]) + "]") if n["tags"] else ""
        print(f"  {c(str(n['id']).rjust(4), YELLOW)}  {c(n['title'], BOLD)}{c(tags_str, CYAN)}  {c(n['created'][:10], DIM)}")
        shown += 1
    rule(); print(c(f"  {shown} note(s)", DIM))


def cmd_view(args):
    notes = db.load()
    note = db.find(notes, args.id)
    if not note: print(c(f"Note #{args.id} not found.", RED)); sys.exit(1)
    tags_str = ", ".join(note["tags"]) if note["tags"] else "none"
    header(f"Note #{note['id']}: {note['title']}")
    print(f"  {c('Tags:', DIM)} {c(tags_str, CYAN)}")
    print(f"  {c('Created:', DIM)} {note['created']}   {c('Updated:', DIM)} {note['updated']}")
    rule()
    print(render_markdown(note["content"]))
    rule()


def cmd_edit(args):
    notes = db.load()
    note = db.find(notes, args.id)
    if not note: print(c(f"Note #{args.id} not found.", RED)); sys.exit(1)
    if args.title: note["title"] = args.title
    if args.tags is not None: note["tags"] = [t.strip() for t in args.tags.split(",")]
    if args.add_tag:
        for t in args.add_tag:
            if t not in note["tags"]: note["tags"].append(t)
    if args.remove_tag:
        note["tags"] = [t for t in note["tags"] if t not in args.remove_tag]
    if args.content:
        note["content"] = args.content
    elif not (args.title or args.tags is not None or args.add_tag or args.remove_tag):
        note["content"] = open_editor(note["content"])
    note["updated"] = db.now()
    db.save(notes)
    print(c(f"✔ Note #{note['id']} updated.", GREEN))


def cmd_delete(args):
    notes = db.load()
    note = db.find(notes, args.id)
    if not note: print(c(f"Note #{args.id} not found.", RED)); sys.exit(1)
    if not args.yes:
        if input(c(f"Delete \"{note['title']}\" (#{args.id})? [y/N] ", YELLOW)).lower() != "y":
            print("Cancelled."); return
    db.save([n for n in notes if n["id"] != args.id])
    print(c(f"✔ Note #{args.id} deleted.", GREEN))


def cmd_search(args):
    q = args.query.lower()
    results = [n for n in db.load()
               if q in n["title"].lower() or q in n["content"].lower()
               or q in " ".join(n["tags"]).lower()]
    header(f"Search: \"{args.query}\"  —  {len(results)} result(s)")
    for n in results:
        tags_str = (" [" + ", ".join(n["tags"]) + "]") if n["tags"] else ""
        snippet = next((l.strip()[:80] for l in n["content"].split("\n") if q in l.lower()), "")
        print(f"  {c(str(n['id']).rjust(4), YELLOW)}  {c(n['title'], BOLD)}{c(tags_str, CYAN)}")
        if snippet: print(f"        {c(snippet, DIM)}")
    rule()


def cmd_tags(_):
    from collections import Counter
    counts = Counter(t for n in db.load() for t in n["tags"])
    if not counts: print(c("No tags found.", DIM)); return
    header("All Tags")
    for tag, cnt in sorted(counts.items()):
        print(f"  {c(tag, CYAN)}  {c(str(cnt) + ' note(s)', DIM)}")
    rule()


def cmd_export(args):
    notes = db.load()
    note = db.find(notes, args.id)
    if not note: print(c(f"Note #{args.id} not found.", RED)); sys.exit(1)
    out = args.output or f"note_{args.id}.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# {note['title']}\n\nTags: {', '.join(note['tags'])}\n"
                f"Created: {note['created']}  Updated: {note['updated']}\n\n---\n\n{note['content']}")
    print(c(f"✔ Exported to {out}", GREEN))


def cmd_import(args):
    from pathlib import Path
    path = Path(args.file)
    if not path.exists(): print(c(f"File not found: {args.file}", RED)); sys.exit(1)
    sfx = path.suffix.lower()
    if sfx == ".docx":
        try: content = db.read_docx(str(path))
        except ImportError as e: print(c(str(e), RED)); sys.exit(1)
    elif sfx in (".md", ".txt"):
        with open(path, encoding="utf-8") as f: content = f.read()
    else:
        print(c(f"Unsupported: {sfx}. Use .docx, .md, .txt", RED)); sys.exit(1)
    title = args.title or path.stem.replace("_", " ").title()
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    notes = db.load()
    note = {"id": db.next_id(notes), "title": title, "content": content,
            "tags": tags, "created": db.now(), "updated": db.now()}
    notes.append(note); db.save(notes)
    print(c(f"✔ Imported as Note #{note['id']}: {title}", GREEN))


def cmd_gui(_):
    from .gui import main as gui_main
    gui_main()


def build_parser():
    p = argparse.ArgumentParser(prog="notes",
        description="Custom CLI — markdown notes with tags, search, .docx import, and web GUI")
    sub = p.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    s = sub.add_parser("new", help="Create a new note")
    s.add_argument("title"); s.add_argument("-c", "--content")
    s.add_argument("-t", "--tags"); s.add_argument("--docx")
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("list", aliases=["ls"], help="List notes")
    s.add_argument("--tag"); s.set_defaults(func=cmd_list)

    s = sub.add_parser("view", aliases=["show"], help="View a note")
    s.add_argument("id", type=int); s.set_defaults(func=cmd_view)

    s = sub.add_parser("edit", help="Edit a note")
    s.add_argument("id", type=int); s.add_argument("-c", "--content")
    s.add_argument("--title"); s.add_argument("--tags")
    s.add_argument("--add-tag", nargs="+"); s.add_argument("--remove-tag", nargs="+")
    s.set_defaults(func=cmd_edit)

    s = sub.add_parser("delete", aliases=["rm"], help="Delete a note")
    s.add_argument("id", type=int); s.add_argument("-y", "--yes", action="store_true")
    s.set_defaults(func=cmd_delete)

    s = sub.add_parser("search", aliases=["find"], help="Search notes")
    s.add_argument("query"); s.set_defaults(func=cmd_search)

    s = sub.add_parser("tags", help="List all tags")
    s.set_defaults(func=cmd_tags)

    s = sub.add_parser("export", help="Export note to .md file")
    s.add_argument("id", type=int); s.add_argument("-o", "--output")
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("import", help="Import .docx/.md/.txt as a note")
    s.add_argument("file"); s.add_argument("--title"); s.add_argument("-t", "--tags")
    s.set_defaults(func=cmd_import)

    s = sub.add_parser("gui", help="Launch the web GUI in your browser")
    s.set_defaults(func=cmd_gui)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
