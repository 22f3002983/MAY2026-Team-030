from app.extensions import db

class Security(db.Model):
    __tablename__ = 'security'

    id         = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    user_id    = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    name       = db.Column(db.String(100), nullable=False)
    phone      = db.Column(db.String(20),  nullable=False)
    telegram_chat_id = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=__import__('datetime').datetime.utcnow)

    def __repr__(self):
        return f'<Security {self.name}>'