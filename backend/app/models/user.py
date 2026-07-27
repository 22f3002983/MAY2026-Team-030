from app.extensions import db, login_manager
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.Enum('resident', 'secretary', 'security', name='user_roles'), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=__import__('datetime').datetime.utcnow)

    resident  = db.relationship('Resident',  backref='user', uselist=False)
    secretary = db.relationship('Secretary', backref='user', uselist=False)
    security  = db.relationship('Security',  backref='user', uselist=False)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)