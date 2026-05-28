"""
app.py  -  Flask web interface for PageWalker
Run:  python app.py   then open http://localhost:5000
"""

import re
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename

from walker import WalkProject, ProjectStore, detect_chapters, preprocess_gutenberg

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
UPLOAD_DIR = Path("texts")
UPLOAD_DIR.mkdir(exist_ok=True)
store = ProjectStore("data")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)


# ---------------------------------------------------------------------------
# Project management
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", projects=store.list_projects())


@app.route("/project/new", methods=["POST"])
def new_project():
    title = request.form.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title required"}), 400
    file = request.files.get("text_file")
    if not file or file.filename == "":
        return jsonify({"error": "Text file required"}), 400

    slug = slugify(title)
    save_path = UPLOAD_DIR / secure_filename(f"{slug}.txt")
    file.save(str(save_path))

    try:
        first_page = int(request.form.get("first_page", 1))
        last_page = int(request.form.get("last_page", 200))
    except ValueError:
        return jsonify({"error": "Page numbers must be integers"}), 400

    chapters_new_page = bool(request.form.get("chapters_new_page"))

    # Preprocess and detect chapters
    raw = save_path.read_text(encoding='utf-8', errors='replace')
    text = preprocess_gutenberg(raw)
    chapter_offsets = detect_chapters(text)

    project = WalkProject(
        title=title, slug=slug, text_path=str(save_path),
        first_page=first_page, last_page=last_page,
        current_page=first_page,
        chapters_new_page=chapters_new_page,
        chapter_offsets=chapter_offsets,
    )
    store.save(project)
    return redirect(url_for("walk_view", slug=slug))


@app.route("/project/<slug>")
def walk_view(slug):
    project = store.load(slug)
    if not project:
        return "Project not found", 404
    return render_template("walk.html", project=project)


@app.route("/project/<slug>/markers")
def markers_view(slug):
    project = store.load(slug)
    if not project:
        return "Project not found", 404
    return render_template("markers.html", project=project)


@app.route("/project/<slug>/delete", methods=["POST"])
def delete_project(slug):
    store.delete(slug)
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Walk API
# ---------------------------------------------------------------------------

@app.route("/api/<slug>/state")
def api_state(slug):
    project = store.load(slug)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(project.walk_state())


@app.route("/api/<slug>/candidates/<int:page>")
def api_candidates(slug, page):
    project = store.load(slug)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # Search mode: type-to-find within page zone
    q = request.args.get("q", "").strip()
    if q and len(q) >= 2:
        result = project.search_candidates(page, q)
        result["type"] = "search"
        return jsonify(result)

    # Check for chapter boundary
    chapter = project.detect_chapter_boundary(page)
    if chapter:
        return jsonify({"type": "chapter", **chapter})

    # No query yet — return empty candidates (user needs to type)
    return jsonify({"type": "empty", "candidates": []})


@app.route("/api/<slug>/pick/<int:page>", methods=["POST"])
def api_pick(slug, page):
    project = store.load(slug)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    data = request.get_json()
    pos = data.get("pos")
    word = data.get("word", "")
    if pos is None:
        return jsonify({"error": "pos required"}), 400

    result = project.set_page_boundary(
        page, int(pos), method="picked", input_text=word,
    )
    store.save(project)
    return jsonify(result)


@app.route("/api/<slug>/accept_chapter/<int:page>", methods=["POST"])
def api_accept_chapter(slug, page):
    project = store.load(slug)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    chapter = project.detect_chapter_boundary(page)
    if not chapter:
        return jsonify({"error": "No chapter boundary detected for this page"}), 400

    result = project.set_page_boundary(
        page, chapter["end_offset"], method="auto_chapter",
        input_text=chapter["heading"],
    )
    store.save(project)
    return jsonify(result)


@app.route("/api/<slug>/goto/<int:page>", methods=["POST"])
def api_goto(slug, page):
    project = store.load(slug)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    result = project.goto_page(page)
    store.save(project)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Markers API
# ---------------------------------------------------------------------------

@app.route("/api/<slug>/markers")
def api_markers(slug):
    project = store.load(slug)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(project.get_all_markers())


@app.route("/api/<slug>/edit/<int:page>", methods=["POST"])
def api_edit(slug, page):
    project = store.load(slug)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    data = request.get_json()
    pos = data.get("pos")
    word = data.get("word", "")
    if pos is None:
        return jsonify({"error": "pos required"}), 400
    result = project.edit_page_boundary(page, int(pos), input_text=word)
    if result["success"]:
        store.save(project)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Lookup API
# ---------------------------------------------------------------------------

@app.route("/api/<slug>/lookup/<int:page>")
def api_lookup(slug, page):
    project = store.load(slug)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    result = project.get_page_text(page)
    if result is None:
        return jsonify({"error": f"Page {page} not yet mapped"}), 404
    return jsonify(result)


@app.route("/api/<slug>/export")
def api_export(slug):
    project = store.load(slug)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(project.export_pages())


@app.route("/api/<slug>/find", methods=["POST"])
def api_find(slug):
    project = store.load(slug)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    phrase = request.get_json().get("phrase", "").strip()
    if not phrase:
        return jsonify({"error": "phrase required"}), 400
    return jsonify(project.find_page_for_phrase(phrase))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
