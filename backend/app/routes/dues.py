from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models.dues import Dues
from app.models.resident import Resident
from app.routes.notifications import create_notification
from app.routes.funds import distribute_payment
import os
import uuid
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

dues_bp = Blueprint('dues', __name__)


# ── helper ────────────────────────────────────────────────────

def dues_to_dict(d):
    return {
        'id':               d.id,
        'resident_id':      d.resident_id,
        'month':            d.month.isoformat() if d.month else None,
        'month_number':     d.month_number,
        'year_number':      d.year_number,
        'amount_due':       float(d.amount_due),
        'amount_paid':      float(d.amount_paid),
        'status':           d.status,
        'paid_date':        d.paid_date.isoformat() if d.paid_date else None,
        'reminder_sent_at': d.reminder_sent_at.isoformat() if d.reminder_sent_at else None,
        'file_url':         d.file_url,
        'created_at':       d.created_at.isoformat() if d.created_at else None,
    }


def generate_receipt_pdf(due):
    """Render a PDF receipt for a paid due and save it under instance/receipts/.
    Returns the path relative to the Flask instance folder."""
    resident    = due.resident
    flat_number = resident.flat.flat_number if resident.flat else 'N/A'
    receipt_no  = due.id[:8].upper()

    receipts_dir = os.path.join(current_app.instance_path, 'receipts')
    os.makedirs(receipts_dir, exist_ok=True)

    file_path = os.path.join(receipts_dir, f'{due.id}.pdf')

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    c.setFont('Helvetica-Bold', 18)
    c.drawCentredString(width / 2, height - 35 * mm, 'Raghvendra Sai Society')

    c.setFont('Helvetica', 12)
    c.drawCentredString(width / 2, height - 43 * mm, 'Maintenance Payment Receipt')

    c.line(30 * mm, height - 48 * mm, width - 30 * mm, height - 48 * mm)

    rows = [
        ('Receipt No.',   receipt_no),
        ('Resident Name', resident.name),
        ('Flat Number',   flat_number),
        ('Month',         due.month.strftime('%B %Y') if due.month else '—'),
        ('Amount Paid',   f'Rs. {float(due.amount_paid):.2f}'),
        ('Payment Date',  due.paid_date.strftime('%d %b %Y, %I:%M %p') if due.paid_date else '—'),
    ]

    y = height - 65 * mm
    for label, value in rows:
        c.setFont('Helvetica-Bold', 11)
        c.drawString(30 * mm, y, f'{label}:')
        c.setFont('Helvetica', 11)
        c.drawString(80 * mm, y, str(value))
        y -= 9 * mm

    c.setFont('Helvetica-Oblique', 9)
    c.drawCentredString(width / 2, 20 * mm, 'This is a system-generated receipt.')

    c.showPage()
    c.save()

    return f'receipts/{due.id}.pdf'


# ── GET /api/dues — list dues ─────────────────────────────────
# resident sees only their own
# secretary sees all

@dues_bp.route('', methods=['GET'])
@login_required
def list_dues():
    if current_user.role == 'resident':
        dues = Dues.query.filter_by(
            resident_id=current_user.resident.id
        ).order_by(Dues.month.desc()).all()

    elif current_user.role == 'secretary':
        status = request.args.get('status')
        query  = Dues.query
        dues   = query.order_by(Dues.month.desc()).all()

        if status:
            dues = [d for d in dues if d.status == status]
    else:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'dues':  [dues_to_dict(d) for d in dues],
        'total': len(dues),
    }), 200


# ── GET /api/dues/<id> — get single due ───────────────────────

@dues_bp.route('/<due_id>', methods=['GET'])
@login_required
def get_due(due_id):
    due = Dues.query.get_or_404(due_id)

    if current_user.role == 'resident':
        if due.resident_id != current_user.resident.id:
            return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({'due': dues_to_dict(due)}), 200


# ── POST /api/dues/generate — generate monthly dues (secretary only) ──

@dues_bp.route('/generate', methods=['POST'])
@login_required
def generate_dues():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can generate dues'}), 403

    data       = request.get_json()
    month_str  = data.get('month')
    amount_due = data.get('amount_due')

    if not month_str or not amount_due:
        return jsonify({'error': 'month and amount_due are required'}), 400

    try:
        month = datetime.strptime(month_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'month must be in YYYY-MM-DD format (use first day of month)'}), 400

    # normalize to first-of-month regardless of what day was passed
    month = month.replace(day=1)

    # reject past or current-and-earlier months — only the upcoming month is allowed
    today = date.today()
    current_month_start = today.replace(day=1)
    if month <= current_month_start:
        return jsonify({'error': 'Cannot generate dues for the current month or earlier — only future months are allowed'}), 400

    residents = Resident.query.all()
    if not residents:
        return jsonify({'error': 'No residents found'}), 400

    # if every resident already has a due for this month, treat it as already generated
    already_generated_count = Dues.query.filter_by(month=month).count()
    if already_generated_count >= len(residents):
        return jsonify({'error': f'Dues have already been generated for {month.strftime("%B %Y")}'}), 400

    created = []
    skipped = []

    for resident in residents:
        existing = Dues.query.filter_by(resident_id=resident.id, month=month).first()
        if existing:
            skipped.append(resident.id)
            continue

        due = Dues(
            id=str(uuid.uuid4()),
            resident_id=resident.id,
            month=month,
            amount_due=amount_due,
            amount_paid=0,
        )
        db.session.add(due)
        created.append(resident.id)

    db.session.commit()

    return jsonify({
        'message': f'Dues generated for {len(created)} residents',
        'created': len(created),
        'skipped': len(skipped),
    }), 201

# ── PATCH /api/dues/<id>/pay — mark as paid (secretary or the resident who owns it) ──

@dues_bp.route('/<due_id>/pay', methods=['PATCH'])
@login_required
def mark_paid(due_id):
    due = Dues.query.get_or_404(due_id)

    if current_user.role == 'secretary':
        pass  # secretary can pay any due
    elif current_user.role == 'resident':
        if not current_user.resident or due.resident_id != current_user.resident.id:
            return jsonify({'error': 'You can only pay your own dues'}), 403
    else:
        return jsonify({'error': 'Unauthorized'}), 403

    if due.status == 'paid':
        return jsonify({'error': 'This due has already been paid'}), 400

    data = request.get_json() or {}
    amount_paid = data.get('amount_paid', float(due.amount_due))

    due.amount_paid = amount_paid
    due.paid_date   = datetime.utcnow()

    db.session.commit()

    distribute_payment(amount_paid, source='dues_payment', reference_id=due.id,
                        description=f'Dues payment — {due.month.strftime("%b %Y")}')

    due.file_url = generate_receipt_pdf(due)
    db.session.commit()

    return jsonify({
        'message': 'Payment recorded',
        'due':     dues_to_dict(due),
    }), 200

# ── GET /api/dues/<id>/receipt — download the PDF receipt ─────

@dues_bp.route('/<due_id>/receipt', methods=['GET'])
@login_required
def get_receipt(due_id):
    due = Dues.query.get_or_404(due_id)

    if current_user.role == 'resident' and due.resident_id != current_user.resident.id:
        return jsonify({'error': 'Unauthorized'}), 403
    elif current_user.role not in ('resident', 'secretary'):
        return jsonify({'error': 'Unauthorized'}), 403

    if not due.file_url:
        return jsonify({'error': 'Receipt not available for this due'}), 404

    file_path = os.path.join(current_app.instance_path, due.file_url)
    if not os.path.exists(file_path):
        return jsonify({'error': 'Receipt file not found'}), 404

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f'receipt_{due.id[:8]}.pdf',
        mimetype='application/pdf',
    )


# ── POST /api/dues/reminder — send bulk reminder (secretary only) ──

@dues_bp.route('/reminder', methods=['POST'])
@login_required
def send_reminder():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can send reminders'}), 403

    # get all unpaid dues
    all_dues = Dues.query.all()
    pending  = [d for d in all_dues if d.status in ('pending', 'overdue')]

    for due in pending:
        due.reminder_sent_at = datetime.utcnow()
        create_notification(
            user_id=due.resident.user_id,
            message=f'Maintenance dues reminder: ₹{float(due.amount_due):.2f} is due for {due.month.strftime("%B %Y")}',
            type='dues_reminder',
        )

    db.session.commit()

    return jsonify({
        'message':  f'Reminder sent to {len(pending)} residents',
        'notified': len(pending),
    }), 200

