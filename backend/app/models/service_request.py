from app.extensions import db
from datetime import datetime

class ServiceRequest(db.Model):
    """Home Services — personal channel. A resident books a society-empanelled
    vendor directly for work inside their own flat. Unrelated to community
    complaints (see Complaint model) which the secretary triages."""
    __tablename__ = 'service_requests'

    id               = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    resident_id      = db.Column(db.String(36), db.ForeignKey('residents.id'), nullable=False)
    vendor_id        = db.Column(db.String(36), db.ForeignKey('vendors.id'), nullable=False)
    category         = db.Column(db.Enum('plumber', 'electrician', 'carpenter', 'cleaner', 'other', name='service_categories'), nullable=False)
    description      = db.Column(db.Text, nullable=False)
    scheduled_date   = db.Column(db.Date, nullable=False)
    scheduled_time   = db.Column(db.Time, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    status           = db.Column(db.Enum('scheduled', 'completed', 'cancelled', name='service_request_status'), default='scheduled')
    payment_status   = db.Column(db.Enum('paid', name='service_payment_status'), nullable=True)
    payment_amount   = db.Column(db.Numeric(10, 2), nullable=True)
    rating           = db.Column(db.Integer, nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    resident = db.relationship('Resident', backref='service_requests', lazy=True)
    vendor   = db.relationship('Vendor', backref='service_requests', lazy=True)

    def __repr__(self):
        return f'<ServiceRequest {self.id} ({self.status})>'
