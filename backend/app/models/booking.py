from app.extensions import db

class Booking(db.Model):
    __tablename__ = 'bookings'

    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    amenity_id  = db.Column(db.String(36), db.ForeignKey('amenities.id'),  nullable=False)
    resident_id = db.Column(db.String(36), db.ForeignKey('residents.id'),  nullable=False)
    date        = db.Column(db.Date,       nullable=False)
    start_time  = db.Column(db.Time,       nullable=False)
    end_time    = db.Column(db.Time,       nullable=False)
    reason      = db.Column(db.Text,       nullable=True)
    status      = db.Column(db.Enum('pending', 'approved', 'rejected', 'cancelled', 'completed', name='booking_status'), default='pending')
    approved_by = db.Column(db.String(36), db.ForeignKey('secretary.id'), nullable=True)
    created_at  = db.Column(db.DateTime,  default=__import__('datetime').datetime.utcnow)

    # multi-day (daily-priced) bookings span date -> end_date; single-day/hourly
    # bookings leave end_date equal to date.
    end_date       = db.Column(db.Date, nullable=True)
    event_type     = db.Column(db.String(100), nullable=True)
    guests         = db.Column(db.Integer, nullable=True)
    price          = db.Column(db.Numeric(10, 2), nullable=True)
    payment_status = db.Column(db.String(15), nullable=True)  # 'not_required' | 'pending' | 'paid'
    rejected_reason = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Booking {self.id} ({self.status})>'