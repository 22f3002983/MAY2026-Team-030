from app.extensions import db

class Amenity(db.Model):
    __tablename__ = 'amenities'

    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    name         = db.Column(db.String(100), nullable=False)
    type         = db.Column(db.Enum('exclusive', 'public', 'unbookable', name='amenity_types'), nullable=False)
    booking_type = db.Column(db.Enum('automatic', 'approval_required', name='booking_types'), nullable=True)
    status       = db.Column(db.Enum('available', 'booked', 'closed', 'maintenance', 'inactive', name='amenity_status'), default='available')
    description  = db.Column(db.Text, nullable=True)
    created_at   = db.Column(db.DateTime, default=__import__('datetime').datetime.utcnow)

    # catalog / display fields
    icon               = db.Column(db.String(10),  nullable=True)
    location           = db.Column(db.String(200), nullable=True)
    capacity           = db.Column(db.Integer,      nullable=True)
    is_air_conditioned = db.Column(db.Boolean, default=False)
    is_decoratable     = db.Column(db.Boolean, default=False)
    features           = db.Column(db.Text, nullable=True)  # JSON-encoded list of strings
    special_booking    = db.Column(db.Boolean, default=False)  # shared facility, exceptionally bookable
    status_until       = db.Column(db.Date, nullable=True)

    # pricing
    pricing_type      = db.Column(db.String(10),  nullable=True)  # 'hourly' | 'daily' | null
    price_rate        = db.Column(db.Numeric(10, 2), nullable=True)
    price_min_units   = db.Column(db.Integer, default=1)
    price_unit_label  = db.Column(db.String(20), nullable=True)

    bookings     = db.relationship('Booking', backref='amenity', lazy=True)

    def __repr__(self):
        return f'<Amenity {self.name}>'