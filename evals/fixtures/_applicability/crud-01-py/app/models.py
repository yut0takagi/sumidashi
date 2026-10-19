from app import db


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, default="")

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "body": self.body}
