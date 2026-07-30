from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.service_request import ServiceRequest
from app.models.vendor import Vendor
import uuid
from datetime import datetime

service_requests_bp = Blueprint('service_requests', __name__)

VALID_CATEGORIES = ('plumber', 'electrician', 'carpenter', 'cleaner', 'other')

# Estimated job duration by category — mirrors the resident-facing estimate
# shown before a vendor even confirms.
DURATION_BY_CATEGORY = {
    'plumber':     60,
    'electrician': 45,
    'carpenter':   90,
    'cleaner':     45,
    'other':       60,
}


# ── helper ────────────────────────────────────────────────────

def request_to_dict(r):
    vendor = r.vendor
    return {
        'id':               r.id,
        'resident_id':      r.resident_id,
        'category':         r.category,
        'description':      r.description,
        'vendor_id':        r.vendor_id,
        'vendor_name':      vendor.name if vendor else None,
        'scheduled_date':   r.scheduled_date.isoformat() if r.scheduled_date else None,
        'scheduled_time':   str(r.scheduled_time) if r.scheduled_time else None,
        'duration_minutes': r.duration_minutes,
        'status':           r.status,
        'payment_status':   r.payment_status,
        'payment_amount':   float(r.payment_amount) if r.payment_amount is not None else None,
        'rating':           r.rating,
        'created_at':       r.created_at.isoformat() + 'Z' if r.created_at else None,
    }


def _parse_date_time(data, errors):
    scheduled_date = None
    scheduled_time = None
    if 'scheduled_date' in data:
        try:
            scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            errors.append('scheduled_date must be YYYY-MM-DD')
    if 'scheduled_time' in data:
        try:
            scheduled_time = datetime.strptime(data['scheduled_time'], '%H:%M').time()
        except (ValueError, TypeError):
            errors.append('scheduled_time must be HH:MM')
    return scheduled_date, scheduled_time


# ── POST /api/service-requests — book a home service ───────────

@service_requests_bp.route('', methods=['POST'])
@login_required
def create_request():
    if current_user.role != 'resident' or not current_user.resident:
        return jsonify({'error': 'Only residents can book home services'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    category    = data.get('category', '')
    description = data.get('description', '').strip()
    vendor_id   = data.get('vendor_id')

    if category not in VALID_CATEGORIES:
        return jsonify({'error': f'category must be one of {VALID_CATEGORIES}'}), 400
    if not description or not vendor_id:
        return jsonify({'error': 'description and vendor_id are required'}), 400

    errors = []
    scheduled_date, scheduled_time = _parse_date_time(data, errors)
    if not data.get('scheduled_date') or not data.get('scheduled_time'):
        errors.append('scheduled_date and scheduled_time are required')
    if errors:
        return jsonify({'error': ' / '.join(errors)}), 400

    vendor = Vendor.query.get(vendor_id)
    if not vendor:
        return jsonify({'error': 'Vendor not found'}), 404

    sr = ServiceRequest(
        id=str(uuid.uuid4()),
        resident_id=current_user.resident.id,
        vendor_id=vendor_id,
        category=category,
        description=description,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        duration_minutes=DURATION_BY_CATEGORY.get(category, 60),
        status='scheduled',
    )

    db.session.add(sr)
    db.session.commit()

    return jsonify({
        'message': f'Booked with {vendor.name}',
        'request': request_to_dict(sr),
    }), 201


# ── GET /api/service-requests — resident's own requests ────────

@service_requests_bp.route('', methods=['GET'])
@login_required
def list_requests():
    if current_user.role != 'resident' or not current_user.resident:
        return jsonify({'error': 'Only residents can view home services'}), 403

    status = request.args.get('status')
    query = ServiceRequest.query.filter_by(resident_id=current_user.resident.id)
    if status:
        query = query.filter_by(status=status)

    requests_list = query.order_by(ServiceRequest.created_at.desc()).all()

    return jsonify({
        'requests': [request_to_dict(r) for r in requests_list],
        'total':    len(requests_list),
    }), 200


# ── PATCH /api/service-requests/<id> — reschedule a scheduled request ──

@service_requests_bp.route('/<request_id>', methods=['PATCH'])
@login_required
def reschedule_request(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)

    if current_user.role != 'resident' or not current_user.resident or sr.resident_id != current_user.resident.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if sr.status != 'scheduled':
        return jsonify({'error': 'Only scheduled requests can be rescheduled'}), 400

    data = request.get_json() or {}

    if 'category' in data:
        if data['category'] not in VALID_CATEGORIES:
            return jsonify({'error': f'category must be one of {VALID_CATEGORIES}'}), 400
        sr.category = data['category']
        sr.duration_minutes = DURATION_BY_CATEGORY.get(sr.category, 60)

    if 'description' in data:
        sr.description = data['description'].strip()

    if 'vendor_id' in data:
        vendor = Vendor.query.get(data['vendor_id'])
        if not vendor:
            return jsonify({'error': 'Vendor not found'}), 404
        sr.vendor_id = data['vendor_id']

    errors = []
    scheduled_date, scheduled_time = _parse_date_time(data, errors)
    if errors:
        return jsonify({'error': ' / '.join(errors)}), 400
    if scheduled_date:
        sr.scheduled_date = scheduled_date
    if scheduled_time:
        sr.scheduled_time = scheduled_time

    db.session.commit()

    return jsonify({
        'message': 'Request rescheduled',
        'request': request_to_dict(sr),
    }), 200


# ── PATCH /api/service-requests/<id>/cancel ─────────────────────

@service_requests_bp.route('/<request_id>/cancel', methods=['PATCH'])
@login_required
def cancel_request(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)

    if current_user.role != 'resident' or not current_user.resident or sr.resident_id != current_user.resident.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if sr.status != 'scheduled':
        return jsonify({'error': 'Only scheduled requests can be cancelled'}), 400

    sr.status = 'cancelled'
    db.session.commit()

    return jsonify({
        'message': 'Request cancelled',
        'request': request_to_dict(sr),
    }), 200


# ── PATCH /api/service-requests/<id>/complete — mark done + pay ────

@service_requests_bp.route('/<request_id>/complete', methods=['PATCH'])
@login_required
def complete_request(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)

    if current_user.role != 'resident' or not current_user.resident or sr.resident_id != current_user.resident.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if sr.status != 'scheduled':
        return jsonify({'error': 'Only scheduled requests can be marked complete'}), 400

    data = request.get_json() or {}
    amount = data.get('amount')
    if amount is None:
        return jsonify({'error': 'amount is required'}), 400
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({'error': 'amount must be a number'}), 400

    sr.status         = 'completed'
    sr.payment_status = 'paid'
    sr.payment_amount = amount
    db.session.commit()

    return jsonify({
        'message': f'Marked complete — ₹{amount:.0f} paid to {sr.vendor.name}',
        'request': request_to_dict(sr),
    }), 200


# ── PATCH /api/service-requests/<id>/rate — rate a completed job ───

@service_requests_bp.route('/<request_id>/rate', methods=['PATCH'])
@login_required
def rate_request(request_id):
    sr = ServiceRequest.query.get_or_404(request_id)

    if current_user.role != 'resident' or not current_user.resident or sr.resident_id != current_user.resident.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if sr.status != 'completed':
        return jsonify({'error': 'Only completed requests can be rated'}), 400

    data   = request.get_json() or {}
    rating = data.get('rating')
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'error': 'rating must be an integer between 1 and 5'}), 400

    sr.rating = rating
    db.session.commit()

    return jsonify({
        'message': f'Thanks for rating {sr.vendor.name}',
        'request': request_to_dict(sr),
    }), 200
