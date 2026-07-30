from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models.dues import Dues
from app.models.resident import Resident
from app.routes.notifications import create_notification
import uuid
import os
from datetime import datetime, date
from calendar import monthrange

dues_bp = Blueprint('dues', __name__)


# ── helper ────────────────────────────────────────────────────

def due_to_dict(d):
    resident = d.resident
    return {
        'id':                d.id,
        'resident_id':       d.resident_id,
        'resident_name':     resident.name if resident else '—',
        'flat_number':       resident.flat.flat_number if resident and resident.flat else None,
        'month':             d.month.isoformat() if d.month else None,
        'amount_due':        float(d.amount_due),
        'amount_paid':       float(d.amount_paid or 0),
        'status':            d.status,
        'paid_date':         d.paid_date.isoformat() if d.paid_date else None,
        'reminder_sent_at':  d.reminder_sent_at.isoformat() if d.reminder_sent_at else None,
        'file_url':          d.file_url,
    }


# ── POST /api/dues/generate — secretary generates dues for a month ─────

@dues_bp.route('/generate', methods=['POST'])
@login_required
def generate_dues():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can generate dues'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    month_str  = data.get('month')       # expected 'YYYY-MM'
    amount_due = data.get('amount_due')

    if not month_str or amount_due is None:
        return jsonify({'error': 'month (YYYY-MM) and amount_due are required'}), 400

    try:
        year, mon = map(int, month_str.split('-'))
        month_date = date(year, mon, 1)
    except (ValueError, AttributeError):
        return jsonify({'error': 'month must be in YYYY-MM format'}), 400

    try:
        amount_due = float(amount_due)
        if amount_due <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({'error': 'amount_due must be a positive number'}), 400

    residents = Resident.query.filter_by(is_onboarded=True).all()
    created, skipped = [], []

    for resident in residents:
        exists = Dues.query.filter_by(resident_id=resident.id, month=month_date).first()
        if exists:
            skipped.append(resident.name)
            continue

        due = Dues(
            id=str(uuid.uuid4()),
            resident_id=resident.id,
            month=month_date,
            amount_due=amount_due,
            amount_paid=0,
        )
        db.session.add(due)
        created.append(due)

    db.session.commit()

    return jsonify({
        'message':          f'Generated dues for {len(created)} resident(s)',
        'created_count':    len(created),
        'skipped_count':    len(skipped),
        'dues':             [due_to_dict(d) for d in created],
    }), 201


# ── GET /api/dues — resident sees own, secretary sees all ──────

@dues_bp.route('', methods=['GET'])
@login_required
def list_dues():
    status = request.args.get('status')   # pending | paid | partial | overdue
    month  = request.args.get('month')    # YYYY-MM

    if current_user.role == 'resident' and current_user.resident:
        query = Dues.query.filter_by(resident_id=current_user.resident.id)
    elif current_user.role == 'secretary':
        query = Dues.query
    else:
        return jsonify({'error': 'Unauthorized'}), 403

    if month:
        try:
            year, mon = map(int, month.split('-'))
            query = query.filter_by(month=date(year, mon, 1))
        except ValueError:
            return jsonify({'error': 'month must be in YYYY-MM format'}), 400

    dues_list = query.order_by(Dues.month.desc()).all()

    if status:
        dues_list = [d for d in dues_list if d.status == status]

    return jsonify({
        'dues':  [due_to_dict(d) for d in dues_list],
        'total': len(dues_list),
    }), 200


# ── PATCH /api/dues/<id>/pay — resident pays a due ──────────────

@dues_bp.route('/<due_id>/pay', methods=['PATCH'])
@login_required
def pay_due(due_id):
    due = Dues.query.get_or_404(due_id)

    if current_user.role == 'resident':
        if not current_user.resident or due.resident_id != current_user.resident.id:
            return jsonify({'error': 'Unauthorized'}), 403
    elif current_user.role != 'secretary':
        return jsonify({'error': 'Unauthorized'}), 403

    if due.status == 'paid':
        return jsonify({'error': 'This due is already paid'}), 400

    # mock payment gateway — marks full amount paid immediately
    due.amount_paid = due.amount_due
    due.paid_date   = datetime.utcnow()

    create_notification(
        user_id=due.resident.user_id,
        message=f'Payment received for {due.month.strftime("%B %Y")} dues',
        type='dues_reminder',
    )

    db.session.commit()

    return jsonify({
        'message': 'Payment recorded successfully',
        'due':     due_to_dict(due),
    }), 200


# ── PATCH /api/dues/<id>/remind — secretary sends a reminder ───

@dues_bp.route('/<due_id>/remind', methods=['PATCH'])
@login_required
def remind_due(due_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can send reminders'}), 403

    due = Dues.query.get_or_404(due_id)

    if due.status == 'paid':
        return jsonify({'error': 'This due is already paid'}), 400

    due.reminder_sent_at = datetime.utcnow()

    create_notification(
        user_id=due.resident.user_id,
        message=f'Reminder: ₹{due.amount_due} due for {due.month.strftime("%B %Y")} maintenance',
        type='dues_reminder',
    )

    db.session.commit()

    return jsonify({
        'message': 'Reminder sent',
        'due':     due_to_dict(due),
    }), 200


# ── GET /api/dues/<id>/receipt — download PDF receipt ──────────

@dues_bp.route('/<due_id>/receipt', methods=['GET'])
@login_required
def download_receipt(due_id):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    due = Dues.query.get_or_404(due_id)

    if current_user.role == 'resident':
        if not current_user.resident or due.resident_id != current_user.resident.id:
            return jsonify({'error': 'Unauthorized'}), 403
    elif current_user.role != 'secretary':
        return jsonify({'error': 'Unauthorized'}), 403

    if due.status != 'paid':
        return jsonify({'error': 'Receipt is only available for paid dues'}), 400

    receipts_dir = os.path.join(current_app.instance_path, 'receipts')
    os.makedirs(receipts_dir, exist_ok=True)
    file_path = os.path.join(receipts_dir, f'{due.id}.pdf')

    c = canvas.Canvas(file_path, pagesize=A4)
    c.setFont('Helvetica-Bold', 18)
    c.drawString(50, 800, 'Niwaas RWA — Payment Receipt')
    c.setFont('Helvetica', 12)
    c.drawString(50, 760, f'Resident: {due.resident.name}')
    c.drawString(50, 740, f'Flat: {due.resident.flat.flat_number if due.resident.flat else "-"}')
    c.drawString(50, 720, f'Month: {due.month.strftime("%B %Y")}')
    c.drawString(50, 700, f'Amount Paid: Rs. {due.amount_paid}')
    c.drawString(50, 680, f'Paid On: {due.paid_date.strftime("%d %b %Y, %I:%M %p") if due.paid_date else "-"}')
    c.drawString(50, 660, f'Receipt ID: {due.id}')
    c.save()

    due.file_url = f'receipts/{due.id}.pdf'
    db.session.commit()

    return send_file(file_path, as_attachment=True, download_name=f'receipt_{due.month.strftime("%b%Y")}.pdf')