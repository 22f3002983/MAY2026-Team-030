from app.extensions import db
from datetime import datetime


class Complaint(db.Model):
    """A single resident's report against a CommunityIssue. Multiple
    residents can report the same issue — each gets their own row here,
    with their own description and (once resolved) their own feedback."""
    __tablename__ = 'complaints'


    id               = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    issue_id         = db.Column(db.String(36), db.ForeignKey('community_issues.id'), nullable=False)
    resident_id      = db.Column(db.String(36), db.ForeignKey('residents.id'), nullable=False)
    description      = db.Column(db.Text, nullable=False)
    feedback_rating  = db.Column(db.Integer, nullable=True)
    feedback_comment = db.Column(db.Text, nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)


    def __repr__(self):
        return f'<Complaint {self.id} (issue {self.issue_id})>'





