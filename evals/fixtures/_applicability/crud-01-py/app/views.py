from flask import Blueprint, abort, jsonify, request

from app import db
from app.models import Note

bp = Blueprint("notes", __name__, url_prefix="/notes")


@bp.get("/")
def list_notes():
    return jsonify([n.to_dict() for n in Note.query.order_by(Note.id).all()])


@bp.post("/")
def create_note():
    note = Note(title=request.json["title"], body=request.json.get("body", ""))
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@bp.put("/<int:note_id>")
def update_note(note_id: int):
    note = Note.query.get(note_id) or abort(404)
    note.title = request.json.get("title", note.title)
    note.body = request.json.get("body", note.body)
    db.session.commit()
    return jsonify(note.to_dict())


@bp.delete("/<int:note_id>")
def delete_note(note_id: int):
    note = Note.query.get(note_id) or abort(404)
    db.session.delete(note)
    db.session.commit()
    return "", 204
