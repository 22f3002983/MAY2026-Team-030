from app.extensions import db
import json

class ElectricityBill(db.Model):
    __tablename__ = 'electricity_bills'

    id          = db.Column(db.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    month       = db.Column(db.Date,       nullable=False)
    total_units = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount= db.Column(db.Numeric(10, 2), nullable=False)
    uploaded_by = db.Column(db.String(36), db.ForeignKey('secretary.id'), nullable=False)
    file_url    = db.Column(db.String(300), nullable=True)
    ai_analysis = db.Column(db.Text,        nullable=True)
    uploaded_at = db.Column(db.DateTime,    default=__import__('datetime').datetime.utcnow)

    def get_analysis(self):
        return json.loads(self.ai_analysis) if self.ai_analysis else None

    def set_analysis(self, analysis_dict):
        self.ai_analysis = json.dumps(analysis_dict)

    def __repr__(self):
        return f'<ElectricityBill {self.month}>'