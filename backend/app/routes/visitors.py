from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.visitor import Visitor
import uuid
import random
import string
from datetime import datetime, date as date_type

visitors_bp = Blueprint('visitors', __name__)


# ── helper ────────────────────────────────────────────────────

def visitor_to_dict(v):
    return {
        'id':             v.id,
        'resident_id':    v.resident_id,
        'name':           v.name,
        'phone':          v.phone,
        'expected_date':  v.expected_date.isoformat() if v.expected_date else None,
        'expected_time':  str(v.expected_time) if v.expected_time else None,
        'pass_code':      v.pass_code,
        'id_verified':    v.id_verified,
        'status':         v.status,
        'check_in_time':  v.check_in_time.isoformat() if v.check_in_time else None,
        'check_out_time': v.check_out_time.isoformat() if v.check_out_time else None,
        'vehicle_number': v.vehicle_number,
        'reason':         v.reason,
        'is_expired':     bool(v.is_expired),
        'created_at':     v.created_at.isoformat() if v.created_at else None,
    }

def generate_pass_code():
    return 'GATE-' + ''.join(random.choices(string.digits, k=4))


# ── GET /api/visitors — list visitors ────────────────────────
# resident sees their own visitors
# secretary and security see all

@visitors_bp.route('', methods=['GET'])
@login_required
def list_visitors():
    status = request.args.get('status')

    if current_user.role == 'resident':
        query = Visitor.query.filter_by(resident_id=current_user.resident.id)
    elif current_user.role in ('secretary', 'security'):
        query = Visitor.query
    else:
        return jsonify({'error': 'Unauthorized'}), 403

    if status:
        query = query.filter_by(status=status)

    visitors = query.order_by(Visitor.created_at.desc()).all()

    return jsonify({
        'visitors': [visitor_to_dict(v) for v in visitors],
        'total':    len(visitors),
    }), 200


# ── GET /api/visitors/today — today's visitors (secretary/security only) ──

@visitors_bp.route('/today', methods=['GET'])
@login_required
def visitors_today():
    if current_user.role not in ('secretary', 'security'):
        return jsonify({'error': 'Unauthorized'}), 403

    today      = date_type.today()
    day_start  = datetime.combine(today, datetime.min.time())
    day_end    = datetime.combine(today, datetime.max.time())

    visitors = Visitor.query.filter(
        db.or_(
            Visitor.expected_date == today,
            db.and_(Visitor.check_in_time >= day_start, Visitor.check_in_time <= day_end),
        )
    ).order_by(Visitor.created_at.desc()).all()

    return jsonify({
        'visitors': [visitor_to_dict(v) for v in visitors],
        'total':    len(visitors),
    }), 200


# ── GET /api/visitors/inside — currently checked-in visitors (security only) ──

@visitors_bp.route('/inside', methods=['GET'])
@login_required
def visitors_inside():
    if current_user.role != 'security':
        return jsonify({'error': 'Only security can view currently inside visitors'}), 403

    visitors = Visitor.query.filter_by(status='checked_in').order_by(Visitor.check_in_time.desc()).all()

    return jsonify({
        'visitors': [visitor_to_dict(v) for v in visitors],
        'total':    len(visitors),
    }), 200


# ── POST /api/visitors — pre-register a visitor (resident only) ──

@visitors_bp.route('', methods=['POST'])
@login_required
def pre_register():
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can pre-register visitors'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Visitor name is required'}), 400

    # generate unique pass code
    pass_code = generate_pass_code()
    while Visitor.query.filter_by(pass_code=pass_code).first():
        pass_code = generate_pass_code()

    expected_date = None
    expected_time = None

    if data.get('expected_date'):
        try:
            expected_date = datetime.strptime(data['expected_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'expected_date must be YYYY-MM-DD'}), 400

    if data.get('expected_time'):
        try:
            expected_time = datetime.strptime(data['expected_time'], '%H:%M').time()
        except ValueError:
            return jsonify({'error': 'expected_time must be HH:MM'}), 400

    visitor = Visitor(
        id=str(uuid.uuid4()),
        resident_id=current_user.resident.id,
        name=name,
        phone=data.get('phone'),
        expected_date=expected_date,
        expected_time=expected_time,
        pass_code=pass_code,
        id_verified=False,
        status='pre_registered',
        vehicle_number=data.get('vehicle_number'),
        reason=data.get('reason'),
    )

    db.session.add(visitor)
    db.session.commit()

    return jsonify({
        'message':  'Visitor pre-registered successfully',
        'visitor':  visitor_to_dict(visitor),
        'pass_code': pass_code,
    }), 201


# ── PATCH /api/visitors/verify — verify pass code (security only) ──

@visitors_bp.route('/verify', methods=['PATCH'])
@login_required
def verify_visitor():
    if current_user.role != 'security':
        return jsonify({'error': 'Only security can verify visitors'}), 403

    data      = request.get_json()
    pass_code = data.get('pass_code', '').strip().upper()

    if not pass_code:
        return jsonify({'error': 'pass_code is required'}), 400

    visitor = Visitor.query.filter_by(pass_code=pass_code).first()
    if not visitor:
        return jsonify({'error': 'Invalid or expired pass code'}), 404

    return jsonify({
        'message': 'Pass code verified',
        'visitor': visitor_to_dict(visitor),
    }), 200


# ── PATCH /api/visitors/<id>/checkin — check in (security only) ──

@visitors_bp.route('/<visitor_id>/checkin', methods=['PATCH'])
@login_required
def check_in(visitor_id):
    if current_user.role != 'security':
        return jsonify({'error': 'Only security can check in visitors'}), 403

    visitor = Visitor.query.get_or_404(visitor_id)

    visitor.status        = 'checked_in'
    visitor.id_verified   = True
    visitor.check_in_time = datetime.utcnow()

    db.session.commit()

    return jsonify({
        'message': f'{visitor.name} checked in successfully',
        'visitor': visitor_to_dict(visitor),
    }), 200


# ── PATCH /api/visitors/<id>/checkout — check out (security only) ──

@visitors_bp.route('/<visitor_id>/checkout', methods=['PATCH'])
@login_required
def check_out(visitor_id):
    if current_user.role != 'security':
        return jsonify({'error': 'Only security can check out visitors'}), 403

    visitor = Visitor.query.get_or_404(visitor_id)
    visitor.status         = 'checked_out'
    visitor.check_out_time = datetime.utcnow()

    db.session.commit()

    return jsonify({
        'message': f'{visitor.name} checked out successfully',
        'visitor': visitor_to_dict(visitor),
    }), 200


# ── PATCH /api/visitors/<id>/reject — reject entry (security only) ──

@visitors_bp.route('/<visitor_id>/reject', methods=['PATCH'])
@login_required
def reject_visitor(visitor_id):
    if current_user.role != 'security':
        return jsonify({'error': 'Only security can reject visitors'}), 403

    visitor = Visitor.query.get_or_404(visitor_id)
    visitor.status = 'rejected'

    db.session.commit()

    return jsonify({
        'message': f'{visitor.name} entry rejected',
        'visitor': visitor_to_dict(visitor),
    }), 200