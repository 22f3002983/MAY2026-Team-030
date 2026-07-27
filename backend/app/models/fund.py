from app.extensions import db
from datetime import datetime


class FundConfig(db.Model):
    """Defines how incoming society payments (dues, amenity fees) are split
    across funds. Percentages across active rows must sum to 100."""
    __tablename__ = 'fund_config'

    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    fund_name    = db.Column(db.String(50), nullable=False, unique=True)
    percentage   = db.Column(db.Numeric(5, 2), nullable=False)
    is_active    = db.Column(db.Boolean, default=True)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<FundConfig {self.fund_name} {self.percentage}%>'


class SocietyFund(db.Model):
    """Running balance for each fund category."""
    __tablename__ = 'society_funds'

    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    fund_name   = db.Column(db.String(50), nullable=False, unique=True)
    balance     = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SocietyFund {self.fund_name} ₹{self.balance}>'


class FundTransaction(db.Model):
    """Ledger entry — every credit (incoming payment split) or debit
    (secretary-recorded expense) against a fund."""
    __tablename__ = 'fund_transactions'

    id           = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    fund_name    = db.Column(db.String(50), nullable=False)
    type         = db.Column(db.Enum('credit', 'debit', name='fund_txn_types'), nullable=False)
    amount       = db.Column(db.Numeric(12, 2), nullable=False)
    source       = db.Column(db.String(50), nullable=False)   # 'dues_payment' | 'amenity_booking' | 'manual'
    reference_id = db.Column(db.String(36), nullable=True)    # id of the due / booking / etc. that triggered this
    description  = db.Column(db.Text, nullable=True)
    created_by   = db.Column(db.String(36), db.ForeignKey('secretary.id'), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<FundTransaction {self.fund_name} {self.type} ₹{self.amount}>'
