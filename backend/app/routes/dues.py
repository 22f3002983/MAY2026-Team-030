from app.extensions import db
from datetime import datetime

class Dues(db.Model):
    __tablename__ = 'dues'

    id               = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    resident_id      = db.Column(db.String(36), db.ForeignKey('residents.id'), nullable=False)
    month            = db.Column(db.Date,    nullable=False)
    amount_due       = db.Column(db.Numeric(10, 2), nullable=False)
    amount_paid      = db.Column(db.Numeric(10, 2), default=0)
    paid_date        = db.Column(db.DateTime, nullable=True)
    reminder_sent_at = db.Column(db.DateTime, nullable=True)
    file_url         = db.Column(db.String(300), nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    # `month` above stays the source of truth (existing code depends on it);
    # these mirror it as separate int columns per the target schema.
    month_number     = db.Column(db.Integer, nullable=True)
    year_number      = db.Column(db.Integer, nullable=True)

    @property
    def status(self):
        if self.amount_paid >= self.amount_due:
            return 'paid'
        if self.amount_paid > 0:
            return 'partial'
        if self.month < datetime.utcnow().date().replace(day=1):
            return 'overdue'
        return 'pending'

    def __repr__(self):
        return f'<Dues {self.resident_id} {self.month} ({self.status})>'


@db.event.listens_for(Dues, 'before_insert')
@db.event.listens_for(Dues, 'before_update')
def _sync_month_year(mapper, connection, due):
    """Keep month_number/year_number mirrored from `month` automatically,
    so every creation path (existing and future) stays in sync without
    each call site having to set them explicitly."""
    if due.month:
        due.month_number = due.month.month
        due.year_number  = due.month.year