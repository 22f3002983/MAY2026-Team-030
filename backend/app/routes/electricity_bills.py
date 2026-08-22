from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.electricity_bill import ElectricityBill
from app.services.ai_bill_analysis import analyze_electricity_bill
import uuid
from datetime import datetime

electricity_bills_bp = Blueprint('electricity_bills', __name__)


# ── helper ───────────────────────────────────────────────────

def bill_to_dict(b):
    return {
        'id':           b.id,
        'month':        b.month.isoformat() if b.month else None,
        'total_units':  float(b.total_units),
        'total_amount': float(b.total_amount),
        'uploaded_by':  b.uploaded_by,
        'file_url':     b.file_url,
        'ai_analysis':  b.ai_analysis,
        'uploaded_at':  b.uploaded_at.isoformat() if b.uploaded_at else None,
    }


def parse_month(month_raw):
    """Accepts 'YYYY-MM' (from an <input type="month">) or 'YYYY-MM-DD'."""
    if len(month_raw) == 7:
        return datetime.strptime(month_raw, '%Y-%m').date()
    return datetime.strptime(month_raw, '%Y-%m-%d').date()


# ── GET /api/electricity-bills — list bills (secretary only) ──

@electricity_bills_bp.route('', methods=['GET'])
@login_required
def list_bills():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can view electricity bills'}), 403

    bills = ElectricityBill.query.order_by(ElectricityBill.month.desc()).all()
    return jsonify({
        'bills': [bill_to_dict(b) for b in bills],
        'total': len(bills),
    }), 200


# ── POST /api/electricity-bills — upload a bill + AI analysis ─

@electricity_bills_bp.route('', methods=['POST'])
@login_required
def create_bill():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can upload electricity bills'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    month_raw    = (data.get('month') or '').strip()
    total_units  = data.get('total_units')
    total_amount = data.get('total_amount')

    if not month_raw or total_units is None or total_amount is None:
        return jsonify({'error': 'month, total_units and total_amount are required'}), 400

    try:
        month = parse_month(month_raw)
    except ValueError:
        return jsonify({'error': 'month must be in YYYY-MM format'}), 400

    try:
        total_units  = float(total_units)
        total_amount = float(total_amount)
    except (TypeError, ValueError):
        return jsonify({'error': 'total_units and total_amount must be numbers'}), 400

    bill = ElectricityBill(
        id=str(uuid.uuid4()),
        month=month,
        total_units=total_units,
        total_amount=total_amount,
        uploaded_by=current_user.secretary.id,
    )
    db.session.add(bill)
    db.session.commit()

    # compare against the 3 most recent other bills on record, regardless of
    # upload order — a bill entered out of chronological order (e.g.
    # backfilling an older month) should still get useful context
    previous_bills = (
        ElectricityBill.query
        .filter(ElectricityBill.id != bill.id)
        .order_by(ElectricityBill.month.desc())
        .limit(3)
        .all()
    )

    bill.ai_analysis = analyze_electricity_bill(
        {'month': month.isoformat(), 'total_units': total_units, 'total_amount': total_amount},
        [
            {'month': b.month.isoformat(), 'total_units': float(b.total_units), 'total_amount': float(b.total_amount)}
            for b in previous_bills
        ],
    )
    db.session.commit()

    return jsonify({
        'message': 'Electricity bill uploaded',
        'bill':    bill_to_dict(bill),
    }), 201


# ── POST /api/electricity-bills/<id>/retry-analysis — manual on-demand retry ─
# Analysis normally runs synchronously inside POST /electricity-bills at
# upload time. If that one attempt fails (timeout, rate limit, etc.) nothing
# ever revisits it automatically until the scheduler's next sweep. This lets
# the secretary force an immediate retry instead of waiting — but only when
# ai_analysis is still None, so a bill that already has a good analysis can
# never be overwritten by a stray click.

@electricity_bills_bp.route('/<bill_id>/retry-analysis', methods=['POST'])
@login_required
def retry_analysis(bill_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can retry bill analysis'}), 403

    bill = ElectricityBill.query.get_or_404(bill_id)

    if bill.ai_analysis:
        return jsonify({'message': 'Analysis already available', 'bill': bill_to_dict(bill)}), 200

    previous_bills = (
        ElectricityBill.query
        .filter(ElectricityBill.id != bill.id)
        .order_by(ElectricityBill.month.desc())
        .limit(3)
        .all()
    )

    bill.ai_analysis = analyze_electricity_bill(
        {'month': bill.month.isoformat(), 'total_units': float(bill.total_units), 'total_amount': float(bill.total_amount)},
        [
            {'month': b.month.isoformat(), 'total_units': float(b.total_units), 'total_amount': float(b.total_amount)}
            for b in previous_bills
        ],
    )
    db.session.commit()

    return jsonify({
        'message': 'Analysis still unavailable' if not bill.ai_analysis else 'Analysis generated',
        'bill':    bill_to_dict(bill),
    }), 200


# ── GET /api/electricity-bills/<id>/analysis — stored AI analysis ─

@electricity_bills_bp.route('/<bill_id>/analysis', methods=['GET'])
@login_required
def get_analysis(bill_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can view bill analysis'}), 403

    bill = ElectricityBill.query.get_or_404(bill_id)
    return jsonify({'ai_analysis': bill.ai_analysis}), 200