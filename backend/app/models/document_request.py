from app.extensions import db

class DocumentRequest(db.Model):
    __tablename__ = 'document_requests'

    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    resident_id  = db.Column(db.String(36), db.ForeignKey('residents.id'), nullable=False)
    type         = db.Column(db.Enum('noc', 'payment_receipt', 'other', name='doc_types'), nullable=False)
    reason       = db.Column(db.Text,       nullable=True)
    status       = db.Column(db.Enum('requested', 'in_progress', 'ready', 'delivered', name='doc_status'), default='requested')
    file_url     = db.Column(db.String(300), nullable=True)
    requested_at = db.Column(db.DateTime,   default=__import__('datetime').datetime.utcnow)
    ready_at     = db.Column(db.DateTime,   nullable=True)

    def __repr__(self):
        return f'<DocumentRequest {self.type} ({self.status})>'