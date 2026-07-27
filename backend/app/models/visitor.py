from app.extensions import db

class Visitor(db.Model):
    __tablename__ = 'visitors'

    id            = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    resident_id   = db.Column(db.String(36), db.ForeignKey('residents.id'), nullable=False)
    name          = db.Column(db.String(100), nullable=False)
    phone         = db.Column(db.String(20),  nullable=True)
    expected_date = db.Column(db.Date,        nullable=True)
    expected_time = db.Column(db.Time,        nullable=True)
    pass_code     = db.Column(db.String(20),  nullable=False, unique=True)
    id_verified   = db.Column(db.Boolean,     default=False)
    status        = db.Column(db.Enum('pre_registered', 'checked_in', 'checked_out', 'rejected', name='visitor_status'), default='pre_registered')
    check_in_time = db.Column(db.DateTime,    nullable=True)
    check_out_time= db.Column(db.DateTime,    nullable=True)
    created_at    = db.Column(db.DateTime,    default=__import__('datetime').datetime.utcnow)

    vehicle_number = db.Column(db.String(20), nullable=True)
    reason         = db.Column(db.Text, nullable=True)
    is_expired     = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Visitor {self.name} ({self.status})>'