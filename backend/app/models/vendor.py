from app.extensions import db

class Vendor(db.Model):
    __tablename__ = 'vendors'

    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    name         = db.Column(db.String(100), nullable=False)
    phone        = db.Column(db.String(20),  nullable=False)
    category     = db.Column(db.Enum('plumber', 'electrician', 'carpenter', 'cleaner', 'other', name='vendor_categories'), nullable=False)
    description  = db.Column(db.Text, nullable=True)
    working_hours= db.Column(db.String(50), nullable=True)
    status       = db.Column(db.Enum('active', 'inactive', name='vendor_status'), default='active')
    created_at   = db.Column(db.DateTime, default=__import__('datetime').datetime.utcnow)

    is_salaried  = db.Column(db.Boolean, default=False)
    salary       = db.Column(db.Numeric(10, 2), nullable=True)

    issues       = db.relationship('CommunityIssue', backref='vendor', lazy=True)

    def __repr__(self):
        return f'<Vendor {self.name}>'