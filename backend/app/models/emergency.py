from app.extensions import db

class EmergencyAlert(db.Model):
    __tablename__ = 'emergency_alerts'

    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    type        = db.Column(db.Enum('Public', 'Private', name='alert_types'), nullable=False)
    message     = db.Column(db.Text,       nullable=False)
    created_by  = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    status      = db.Column(db.Enum('active', 'resolved', name='alert_status'), default='active')
    resolved_at = db.Column(db.DateTime,   nullable=True)
    created_at  = db.Column(db.DateTime,   default=__import__('datetime').datetime.utcnow)

    location_info = db.Column(db.String(200), nullable=True)
    severity      = db.Column(db.Enum('low', 'medium', 'high', 'critical', name='alert_severity'), nullable=True)

    def __repr__(self):
        return f'<EmergencyAlert {self.type} ({self.status})>'