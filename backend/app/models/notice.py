from app.extensions import db

class Notice(db.Model):
    __tablename__ = 'notices'

    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text,        nullable=False)
    tag         = db.Column(db.Enum('General', 'Maintenance', 'Security', 'Event', 'Urgent', name='notice_tags'), default='General')
    relevance   = db.Column(db.String(20),  default='all')
    expiry_date = db.Column(db.Date,        nullable=False)
    created_by  = db.Column(db.String(36),  db.ForeignKey('secretary.id'), nullable=False)
    created_at  = db.Column(db.DateTime,    default=__import__('datetime').datetime.utcnow)
    is_active   = db.Column(db.Boolean,     default=True)

    priority    = db.Column(db.Enum('normal', 'urgent', name='notice_priority'), nullable=True)

    def __repr__(self):
        return f'<Notice {self.title}>'