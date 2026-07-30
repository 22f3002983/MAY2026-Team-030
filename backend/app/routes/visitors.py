from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.visitor import Visitor
import uuid
import random
import string
from datetime import datetime, date as date_type, time as time_type, timedelta

visitors_bp = Blueprint('visitors', __name__)

WALKIN_APPROVAL_MINUTES = 15  # fixed duration for a gate-approved walk-in


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
        'visit_type':     v.visit_type,
        'check_in_time':  v.check_in_time.isoformat() if v.check_in_time else None,
        'check_out_time': v.check_out_time.isoformat() if v.check_out_time else None,
        'vehicle_number': v.vehicle_number,
        'reason':         v.reason,
        'expires_at':     v.expires_at.isoformat() if v.expires_at else None,
        'revoked':        bool(v.revoked),
        'revoked_at':     v.revoked_at.isoformat() if v.revoked_at else None,
        # computed live from expires_at rather than trusting a stored flag —
        # no background job needed to keep this in sync. Kept separate from
        # `revoked` here so the resident can still tell the two apart.
        'is_expired':     _is_timed_out(v),
        'created_at':     v.created_at.isoformat() if v.created_at else None,
    }

def generate_pass_code():
    return 'GATE-' + ''.join(random.choices(string.digits, k=4))

def _is_timed_out(v):
    return bool(v.expires_at and datetime.utcnow() > v.expires_at)

def _is_usable(v):
    """A pass security can act on: not revoked, not timed out."""
    return not v.revoked and not _is_timed_out(v)

def visitor_to_security_dict(v):
    """Same shape as visitor_to_dict, but collapses revoked + timed-out
    into a single is_expired flag and drops revoked/revoked_at entirely —
    security only needs to know a pass is no longer valid, not why."""
    d = visitor_to_dict(v)
    d['is_expired'] = bool(v.revoked or _is_timed_out(v))
    d.pop('revoked', None)
    d.pop('revoked_at', None)
    return d

def _compute_expires_at(visit_type, expected_date, expected_time, duration_minutes):
    """Single place that decides when a pass stops being valid, for both
    walk-in and pre-registered passes."""
    if visit_type == 'walk_in':
        minutes = duration_minutes if duration_minutes else 15
        return datetime.utcnow() + timedelta(minutes=minutes)

    # pre_registered — valid any time on the expected day, expiring at
    # end of day regardless of the specific expected_time given
    if expected_date:
        return datetime.combine(expected_date, time_type(23, 59, 59))
    return None  # no fixed date given → open-ended pass, no expiry


# ── GET /api/visitors — list visitors ────────────────────────
# resident sees their own visitors
# secretary and security see all
# (also used by residents to fetch pending gate-approval requests via
# ?status=awaiting_approval — no separate endpoint needed)

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
    serialize = visitor_to_security_dict if current_user.role == 'security' else visitor_to_dict

    return jsonify({
        'visitors': [serialize(v) for v in visitors],
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
    serialize = visitor_to_security_dict if current_user.role == 'security' else visitor_to_dict

    return jsonify({
        'visitors': [serialize(v) for v in visitors],
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

    visit_type = data.get('visit_type', 'pre_registered')
    if visit_type not in ('pre_registered', 'walk_in'):
        return jsonify({'error': 'visit_type must be pre_registered or walk_in'}), 400

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

    duration_minutes = data.get('duration_minutes')
    if visit_type == 'walk_in' and duration_minutes is not None:
        try:
            duration_minutes = int(duration_minutes)
        except (TypeError, ValueError):
            return jsonify({'error': 'duration_minutes must be a number'}), 400

    expires_at = _compute_expires_at(visit_type, expected_date, expected_time, duration_minutes)

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
        visit_type=visit_type,
        expires_at=expires_at,
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


# ── POST /api/visitors/gate-request — security flags an unregistered
#    visitor at the gate and asks the resident to approve them ─────

@visitors_bp.route('/gate-request', methods=['POST'])
@login_required
def create_gate_request():
    if current_user.role != 'security':
        return jsonify({'error': 'Only security can raise a gate request'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Visitor name is required'}), 400

    resident_id = data.get('resident_id')
    if not resident_id:
        return jsonify({'error': 'resident_id is required'}), 400

    pass_code = generate_pass_code()
    while Visitor.query.filter_by(pass_code=pass_code).first():
        pass_code = generate_pass_code()

    visitor = Visitor(
        id=str(uuid.uuid4()),
        resident_id=resident_id,
        name=name,
        phone=data.get('phone'),
        pass_code=pass_code,
        id_verified=False,
        status='awaiting_approval',
        visit_type='walk_in',
        reason=data.get('reason', 'At the gate, awaiting approval'),
    )

    db.session.add(visitor)
    db.session.commit()

    return jsonify({
        'message': 'Gate request sent to resident',
        'visitor': visitor_to_dict(visitor),
    }), 201


# ── PATCH /api/visitors/<id>/approve — resident approves a gate request ──
# On approval, a 15-minute walk-in pass becomes active immediately;
# security still checks the visitor in via the existing /checkin route.

@visitors_bp.route('/<visitor_id>/approve', methods=['PATCH'])
@login_required
def approve_gate_request(visitor_id):
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can approve a gate request'}), 403

    visitor = Visitor.query.get_or_404(visitor_id)
    if visitor.resident_id != current_user.resident.id:
        return jsonify({'error': 'Not your visitor'}), 403
    if visitor.status != 'awaiting_approval':
        return jsonify({'error': 'This request is no longer pending'}), 400

    visitor.status     = 'pre_registered'
    visitor.expires_at = datetime.utcnow() + timedelta(minutes=WALKIN_APPROVAL_MINUTES)

    db.session.commit()

    return jsonify({
        'message': f'{visitor.name} approved — pass valid for {WALKIN_APPROVAL_MINUTES} minutes',
        'visitor': visitor_to_dict(visitor),
    }), 200


# ── PATCH /api/visitors/<id>/deny — resident denies a gate request ──

@visitors_bp.route('/<visitor_id>/deny', methods=['PATCH'])
@login_required
def deny_gate_request(visitor_id):
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can deny a gate request'}), 403

    visitor = Visitor.query.get_or_404(visitor_id)
    if visitor.resident_id != current_user.resident.id:
        return jsonify({'error': 'Not your visitor'}), 403
    if visitor.status != 'awaiting_approval':
        return jsonify({'error': 'This request is no longer pending'}), 400

    visitor.status = 'rejected'
    db.session.commit()

    return jsonify({
        'message': f'{visitor.name} denied entry',
        'visitor': visitor_to_dict(visitor),
    }), 200


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

    if not _is_usable(visitor):
        return jsonify({'error': 'Invalid or expired pass code'}), 404

    return jsonify({
        'message': 'Pass code verified',
        'visitor': visitor_to_security_dict(visitor),
    }), 200


# ── PATCH /api/visitors/<id>/checkin — check in (security only) ──

@visitors_bp.route('/<visitor_id>/checkin', methods=['PATCH'])
@login_required
def check_in(visitor_id):
    if current_user.role != 'security':
        return jsonify({'error': 'Only security can check in visitors'}), 403

    visitor = Visitor.query.get_or_404(visitor_id)

    if not _is_usable(visitor):
        return jsonify({'error': 'Invalid or expired pass code'}), 400

    visitor.status        = 'checked_in'
    visitor.id_verified   = True
    visitor.check_in_time = datetime.utcnow()

    db.session.commit()

    return jsonify({
        'message': f'{visitor.name} checked in successfully',
        'visitor': visitor_to_security_dict(visitor),
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
        'visitor': visitor_to_security_dict(visitor),
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


# ── PATCH /api/visitors/<id>/revoke — resident revokes their own pass ──
# Uses the `revoked` flag rather than `status`, so a resident-cancelled
# pass is never indistinguishable from a security-rejected one.

@visitors_bp.route('/<visitor_id>/revoke', methods=['PATCH'])
@login_required
def revoke_visitor(visitor_id):
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can revoke their own passes'}), 403

    visitor = Visitor.query.get_or_404(visitor_id)
    if visitor.resident_id != current_user.resident.id:
        return jsonify({'error': 'Not your visitor'}), 403
    if visitor.status != 'pre_registered':
        return jsonify({'error': 'Only an upcoming pass can be revoked'}), 400

    visitor.revoked    = True
    visitor.revoked_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        'message': 'Pass revoked',
        'visitor': visitor_to_dict(visitor),
    }), 200