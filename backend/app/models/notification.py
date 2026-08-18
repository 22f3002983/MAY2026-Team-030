from app.extensions import db
from datetime import datetime

class Notification(db.Model):
    __tablename__ = 'notifications'

    id         = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    user_id    = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    message    = db.Column(db.String(300), nullable=False)
    type       = db.Column(db.Enum(
        'booking_approved', 'booking_rejected', 'complaint_updated',
        'dues_reminder', 'document_ready', 'emergency_alert',
        'notice_posted', 'general',
        name='notification_types'
    ), default='general')
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification {self.type} user={self.user_id} read={self.is_read}>'