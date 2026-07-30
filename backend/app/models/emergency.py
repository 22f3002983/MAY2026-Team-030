# app/models/emergency.py
from app.extensions import db
import uuid
from datetime import datetime

class EmergencyAlert(db.Model):
    __tablename__ = 'emergency_alerts'

    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type        = db.Column(db.Enum('Public', 'Private', name='alert_types'), nullable=False)
    message     = db.Column(db.Text,       nullable=False)
    created_by  = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    status      = db.Column(db.Enum('active', 'resolved', name='alert_status'), default='active')
    resolved_at = db.Column(db.DateTime,   nullable=True)
    resolved_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)   # ADDED
    created_at  = db.Column(db.DateTime,   default=datetime.utcnow)

    location_info = db.Column(db.String(200), nullable=True)
    severity      = db.Column(db.Enum('low', 'medium', 'high', 'critical', name='alert_severity'), nullable=True)

    # two FKs now point at users.id, so each relationship needs foreign_keys= to disambiguate
    creator  = db.relationship('User', foreign_keys=[created_by])    # CHANGED
    resolver = db.relationship('User', foreign_keys=[resolved_by])   # ADDED

    def __repr__(self):
        return f'<EmergencyAlert {self.type} ({self.status})>'