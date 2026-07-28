from app.extensions import db

class Secretary(db.Model):
    __tablename__ = 'secretary'

    id         = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    user_id    = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    name       = db.Column(db.String(100), nullable=False)
    phone      = db.Column(db.String(20),  nullable=False)
    term_start = db.Column(db.Date,    nullable=True)
    term_end   = db.Column(db.Date,    nullable=True)
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=__import__('datetime').datetime.utcnow)

    def __repr__(self):
        return f'<Secretary {self.name}>'