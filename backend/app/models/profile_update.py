from app.extensions import db
import json

class ProfileUpdateRequest(db.Model):
    __tablename__ = 'profile_update_requests'

    id               = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    resident_id      = db.Column(db.String(36), db.ForeignKey('residents.id'), nullable=False)
    proposed_changes = db.Column(db.Text,       nullable=False)
    status           = db.Column(db.Enum('pending', 'approved', 'rejected', name='profile_update_status'), default='pending')
    reviewed_by      = db.Column(db.String(36), db.ForeignKey('secretary.id'), nullable=True)
    created_at       = db.Column(db.DateTime,   default=__import__('datetime').datetime.utcnow)

    def get_changes(self):
        return json.loads(self.proposed_changes)

    def set_changes(self, changes_dict):
        self.proposed_changes = json.dumps(changes_dict)

    def __repr__(self):
        return f'<ProfileUpdateRequest {self.resident_id} ({self.status})>'