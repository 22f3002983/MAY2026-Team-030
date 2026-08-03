from app.extensions import db

class Resident(db.Model):
    __tablename__ = 'residents'

    id                  = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    user_id             = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    flat_id             = db.Column(db.String(36), db.ForeignKey('flats.id'), nullable=True)
    name                = db.Column(db.String(100), nullable=False)
    phone               = db.Column(db.String(20),  nullable=False)
    occupant_type       = db.Column(db.Enum('owner', 'tenant', name='occupant_types'), default='owner')
    household_size      = db.Column(db.Integer, default=1)
    invite_code         = db.Column(db.String(20),  nullable=True)
    invite_code_expiry  = db.Column(db.DateTime,    nullable=True)
    is_onboarded        = db.Column(db.Boolean, default=False)
    onboarded_at        = db.Column(db.DateTime, nullable=True)
    vehicle1_name        = db.Column(db.String(100), nullable=True)
    vehicle1_number      = db.Column(db.String(20),  nullable=True)
    vehicle2_name        = db.Column(db.String(100), nullable=True)
    vehicle2_number      = db.Column(db.String(20),  nullable=True)
    created_at          = db.Column(db.DateTime, default=__import__('datetime').datetime.utcnow)

    complaints          = db.relationship('Complaint',         backref='resident', lazy=True)
    bookings            = db.relationship('Booking',           backref='resident', lazy=True)
    dues                = db.relationship('Dues',              backref='resident', lazy=True)
    visitors            = db.relationship('Visitor',           backref='resident', lazy=True)
    document_requests   = db.relationship('DocumentRequest',   backref='resident', lazy=True)
    profile_updates     = db.relationship('ProfileUpdateRequest', backref='resident', lazy=True)

    def __repr__(self):
        return f'<Resident {self.name}>'