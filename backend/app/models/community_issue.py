from app.extensions import db
from datetime import datetime

class CommunityIssue(db.Model):
    """The shared ticket for a reported problem — one row per actual issue,
    regardless of how many residents report it. Individual reports live in
    the lightweight Complaint model, each pointing back here via issue_id."""
    __tablename__ = 'community_issues'

    id                       = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    title                    = db.Column(db.String(200), nullable=False)
    description              = db.Column(db.Text, nullable=False)
    ai_suggested_description = db.Column(db.Text, nullable=True)
    category                 = db.Column(db.Enum('plumbing', 'electrical', 'cleaning', 'carpentry', 'other', name='issue_categories'), nullable=False)
    ai_suggested_category    = db.Column(db.String(50), nullable=True)
    priority                 = db.Column(db.Enum('high', 'medium', 'low', name='issue_priority'), default='medium')
    ai_suggested_priority    = db.Column(db.String(10), nullable=True)
    type                     = db.Column(db.Enum('personal', 'common_area', name='issue_types'), nullable=False)
    location                 = db.Column(db.String(200), nullable=True)
    status                   = db.Column(db.Enum('open', 'in_progress', 'resolved', 'closed', name='issue_status'), default='open')
    vendor_id                = db.Column(db.String(36), db.ForeignKey('vendors.id'), nullable=True)
    vendor_whatsapp_status   = db.Column(db.Enum('notified', 'accepted', 'declined', 'no_response', name='issue_whatsapp_status'), nullable=True)
    vendor_start_time        = db.Column(db.DateTime, nullable=True)
    vendor_end_time          = db.Column(db.DateTime, nullable=True)
    created_by               = db.Column(db.String(36), db.ForeignKey('residents.id'), nullable=True)
    created_at               = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at              = db.Column(db.DateTime, nullable=True)

    # no delete-orphan cascade, and passive_deletes=True: reports are
    # explicitly reassigned to a new issue on merge before the old (now
    # childless) issue is deleted — without passive_deletes, SQLAlchemy's
    # default behavior tries to NULL each child's issue_id on parent
    # delete, which both clobbers the reassignment and violates the
    # NOT NULL constraint on that column.
    reports = db.relationship('Complaint', backref='issue', lazy=True, passive_deletes=True)

    def __repr__(self):
        return f'<CommunityIssue {self.id} ({self.status})>'
