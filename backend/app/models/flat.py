from app.extensions import db

class Flat(db.Model):
    __tablename__ = 'flats'

    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    tower       = db.Column(db.String(10),  nullable=False)
    floor       = db.Column(db.Integer,     nullable=False)
    unit_number = db.Column(db.String(10),  nullable=False)
    flat_number = db.Column(db.String(20),  nullable=False, unique=True)
    status      = db.Column(db.Enum('occupied', 'vacant', 'under_renovation', name='flat_status'), default='vacant')
    created_at  = db.Column(db.DateTime, default=__import__('datetime').datetime.utcnow)

    residents   = db.relationship('Resident', backref='flat', lazy=True)

    def __repr__(self):
        return f'<Flat {self.flat_number}>'