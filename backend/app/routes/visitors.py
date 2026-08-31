from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.visitor import Visitor
from app.routes.notifications import create_notification
import uuid
import random
import string
from datetime import datetime, date as date_type, time as time_type, timedelta

visitors_bp = Blueprint('visitors', __name__)

WALKIN_APPROVAL_MINUTES = 15  # fixed duration for a gate-approved walk-in


# ── helper ────────────────────────────────────────────────────

def _iso_utc(dt):
    """Serialize a naive UTC datetime (from datetime.utcnow()) with an
    explicit 'Z' suffix. Without this, the frontend's `new Date(str)`
    parses a timezone-less ISO string as LOCAL time instead of UTC —
    for a resident ahead of UTC (e.g. IST, +5:30), that silently shifts
    every timestamp backwards by the offset. A short-lived walk-in pass
    (15-60 min expiry) then reads as already expired the moment it's
    created, since the misinterpreted expires_at lands before "now".
    Pre-registered passes mostly hid this because their end-of-day
    expiry usually still lands in the future even after the shift.
    date-only/time-only fields (expected_date, expected_time) don't
    need this — they're calendar/clock values, not instants."""
    return dt.isoformat() + 'Z' if dt else None

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
        'is_multi_use':   bool(v.is_multi_use),
        'valid_until':    v.valid_until.isoformat() if v.valid_until else None,
        'validity_mode':  v.validity_mode,
        'check_in_time':  _iso_utc(v.check_in_time),
        'check_out_time': _iso_utc(v.check_out_time),
        'vehicle_number': v.vehicle_number,
        'reason':         v.reason,
        'expires_at':     _iso_utc(v.expires_at),
        'revoked':        bool(v.revoked),
        'revoked_at':     _iso_utc(v.revoked_at),
        # computed live from expires_at rather than trusting a stored flag —
        # no background job needed to keep this in sync. Kept separate from
        # `revoked` here so the resident can still tell the two apart.
        'is_expired':     _is_timed_out(v),
        # Lower bound for exact_date passes — not usable before their single
        # expected day. Exposed here so callers don't need their own copy of
        # this rule just to show a "not valid yet" message.
        'is_not_yet_valid': _is_not_yet_valid(v),
        # Single resolved status, precedence applied once instead of by
        # every caller: an explicit revoke always wins; otherwise a real
        # timeout (only reachable from pre_registered/checked_out — once
        # checked_in, the visitor is already inside and the clock no
        # longer applies); otherwise the visitor's actual workflow status.
        # Frontends should read this directly rather than re-deriving it
        # from status/revoked/expires_at.
        'display_status': _display_status(v),
        'created_at':     _iso_utc(v.created_at),
    }

def generate_pass_code():
    return 'GATE-' + ''.join(random.choices(string.digits, k=4))

def _is_timed_out(v):
    return bool(v.expires_at and datetime.utcnow() > v.expires_at)

def _is_not_yet_valid(v):
    """Lower bound for 'exact_date' passes — not usable before their
    single expected day. This is separate from _is_usable() so callers
    that want a specific "not valid yet" message (rather than a generic
    "not valid") can check it on its own; expires_at only ever carries an
    upper bound, so this is the only place the lower bound is enforced."""
    return bool(v.validity_mode == 'exact_date' and v.expected_date and date_type.today() < v.expected_date)

def _display_status(v):
    if v.revoked:
        return 'revoked'
    if v.status in ('pre_registered', 'checked_out') and _is_timed_out(v):
        return 'expired'
    return v.status

def _is_usable(v):
    """A pass security can act on: not revoked, not timed out.
    Deliberately status-agnostic — a checked_in visitor's pass is still
    "usable" (e.g. multi-entry re-verification); status-specific rules
    for individual actions (checkin/checkout) are enforced at the route
    level instead, not here. Deliberately excludes _is_not_yet_valid() too
    — callers that care about that check it separately for a clearer
    "not yet" message instead of a generic "not valid" one."""
    return not v.revoked and not _is_timed_out(v)

def visitor_to_security_dict(v):
    """Same shape as visitor_to_dict, but collapses revoked + timed-out
    into a single is_expired flag and drops revoked/revoked_at entirely —
    security only needs to know a pass is no longer valid, not why. Also
    folds in the resident's flat details (flat number, unit, floor) so the
    gate-code verify modal can show who/where without a second lookup."""
    d = visitor_to_dict(v)
    d['is_expired'] = bool(v.revoked or _is_timed_out(v))
    d.pop('revoked', None)
    d.pop('revoked_at', None)
    # display_status can say 'revoked' — security doesn't get that
    # distinction (see is_expired above), so drop it rather than let it
    # contradict the collapsed is_expired flag.
    d.pop('display_status', None)

    resident = v.resident
    flat = resident.flat if resident else None
    d['resident_name'] = resident.name if resident else None
    d['flat_number']   = flat.flat_number if flat else None
    d['unit_number']   = flat.unit_number if flat else None
    d['floor']         = flat.floor if flat else None
    d['tower']         = flat.tower if flat else None

    return d

def _notify_resident_of_visitor_event(visitor, event, extra_line=None):
    """Single place for the check-in / check-out notification pair:
    one in-app Notification (queued on the current session — caller's own
    commit persists it) plus a fire-and-forget Telegram DM if the resident
    has linked their chat id. `event` is 'checked_in' or 'checked_out'."""
    resident = visitor.resident
    if not resident:
        return

    if event == 'checked_in':
        emoji, verb, ntype = '✅', 'checked in', 'visitor_checked_in'
    else:
        emoji, verb, ntype = '🚪', 'checked out', 'visitor_checked_out'

    in_app_message = f'{emoji} {visitor.name} has {verb} at the gate (pass {visitor.pass_code})'
    create_notification(user_id=resident.user_id, message=in_app_message, type=ntype)

    if resident.telegram_chat_id:
        from app.telegram_bot import send_telegram_message
        time_field = visitor.check_in_time if event == 'checked_in' else visitor.check_out_time
        time_line  = time_field.strftime('%d %b, %I:%M %p') if time_field else '—'
        telegram_message = (
            f'{emoji} Visitor {verb.title()} — Niwaas RWA\n\n'
            f'Visitor: {visitor.name}\n'
            f'Pass code: {visitor.pass_code}\n'
            f'{"Checked in" if event == "checked_in" else "Checked out"} at: {time_line}'
        )
        if extra_line:
            telegram_message += f'\n{extra_line}'
        send_telegram_message(resident.telegram_chat_id, telegram_message)


def _compute_expires_at(visit_type, expected_date, expected_time, duration_minutes,
                         validity_mode='no_date', valid_until=None):
    """Single place that decides when a pass stops being valid, for
    walk-in and pre-registered passes. validity_mode is independent of
    is_multi_use — either use-type can pick any of the three modes."""
    if visit_type == 'walk_in':
        minutes = duration_minutes if duration_minutes else 15
        return datetime.utcnow() + timedelta(minutes=minutes)

    # exact_date / until_date — both expire at end of the expected day.
    # The "not usable before expected_date" restriction that makes
    # exact_date different from until_date is enforced separately via
    # _is_not_yet_valid(), since expires_at only carries an upper bound.
    if validity_mode in ('exact_date', 'until_date'):
        return datetime.combine(expected_date, time_type(23, 59, 59))

    # no_date — stays valid through valid_until (resident-chosen), or
    # indefinitely if no validity date was given.
    if valid_until:
        return datetime.combine(valid_until, time_type(23, 59, 59))
    return None  # no validity date given → open-ended pass, no expiry


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


# ── GET /api/visitors/today — visitors for a given day (secretary/security) ──
# Defaults to today; pass ?date=YYYY-MM-DD to look at any other day (used
# by the secretary's Visitors section to filter by date). "For that day"
# means: expected on it, checked in on it, checked out on it, or (for
# walk-ins, which don't set expected_date) created on it.

@visitors_bp.route('/today', methods=['GET'])
@login_required
def visitors_today():
    if current_user.role not in ('secretary', 'security'):
        return jsonify({'error': 'Unauthorized'}), 403

    date_param = request.args.get('date')
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'date must be YYYY-MM-DD'}), 400
    else:
        target_date = date_type.today()

    day_start  = datetime.combine(target_date, datetime.min.time())
    day_end    = datetime.combine(target_date, datetime.max.time())

    visitors = Visitor.query.filter(
        db.or_(
            Visitor.expected_date == target_date,
            db.and_(Visitor.check_in_time >= day_start, Visitor.check_in_time <= day_end),
            db.and_(Visitor.check_out_time >= day_start, Visitor.check_out_time <= day_end),
            # walk-ins have no meaningful "expected" date of their own — for
            # them, "that day" means created that day, not expected_date
            # matching (a resident's self-service walk-in doesn't set
            # expected_date at all, so without this it wouldn't show up
            # here pre-checkin)
            db.and_(Visitor.visit_type == 'walk_in', Visitor.created_at >= day_start, Visitor.created_at <= day_end),
        )
    ).order_by(Visitor.created_at.desc()).all()
    # Both secretary and security get the flat/resident-enriched shape
    # here — the secretary's Visitors section needs flat number and
    # tower just as much as the gate does.
    serialize = visitor_to_security_dict

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

    # is_multi_use — whether the pass can be used for repeat entries
    # (e.g. a maid/driver) rather than a single visit. Defaults to True
    # to match the model default. Independent of validity_mode below —
    # either use-type can pick any validity mode.
    is_multi_use = data.get('is_multi_use', True)
    if not isinstance(is_multi_use, bool):
        return jsonify({'error': 'is_multi_use must be true or false'}), 400

    valid_until = None
    if data.get('valid_until'):
        try:
            valid_until = datetime.strptime(data['valid_until'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'valid_until must be YYYY-MM-DD'}), 400

    # validity_mode — the date window a pre-registered pass is usable in:
    #   exact_date  — usable only on expected_date, not before, not after
    #   until_date  — usable any time up through the end of expected_date
    #   no_date     — no expected_date required; open-ended (or bound by
    #                 the optional valid_until above)
    # If the caller doesn't send this at all, fall back to the defaults
    # this app had before validity_mode existed, keyed off is_multi_use:
    # multi-use → open-ended, one-time-use → bound to expected_date.
    #
    # 'until_date' behaves identically to 'no_date' + valid_until (both
    # just expire end-of-day on a chosen date, no lower bound) — the
    # resident-facing form no longer offers it as a separate choice and
    # always sends 'exact_date' or 'no_date' now. It's kept accepted here
    # for existing passes and any other caller still using it.
    validity_mode = data.get('validity_mode')
    if validity_mode is not None and validity_mode not in ('exact_date', 'until_date', 'no_date'):
        return jsonify({'error': 'validity_mode must be exact_date, until_date, or no_date'}), 400
    if validity_mode is None:
        validity_mode = 'no_date' if is_multi_use else 'until_date'

    if visit_type == 'pre_registered' and validity_mode in ('exact_date', 'until_date') and not expected_date:
        return jsonify({'error': 'Expected date is required for this validity mode'}), 400

    duration_minutes = data.get('duration_minutes')
    if visit_type == 'walk_in' and duration_minutes is not None:
        try:
            duration_minutes = int(duration_minutes)
        except (TypeError, ValueError):
            return jsonify({'error': 'duration_minutes must be a number'}), 400

    expires_at = _compute_expires_at(
        visit_type, expected_date, expected_time, duration_minutes,
        validity_mode=validity_mode, valid_until=valid_until,
    )

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
        is_multi_use=is_multi_use,
        valid_until=valid_until,
        validity_mode=validity_mode,
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
        expected_date=date_type.today(),   # ← added: gate requests are always "today"
        pass_code=pass_code,
        id_verified=False,
        status='awaiting_approval',
        visit_type='walk_in',
        reason=data.get('reason', 'At the gate, awaiting approval'),
        vehicle_number=data.get('vehicle_number')
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

    data      = request.get_json() or {}
    pass_code = data.get('pass_code', '').strip().upper()

    if not pass_code:
        return jsonify({'error': 'pass_code is required'}), 400

    visitor = Visitor.query.filter_by(pass_code=pass_code).first()
    if not visitor:
        return jsonify({'error': 'Invalid or expired pass code'}), 404

    # Status takes priority over revoked/expired: a visitor who's already
    # checked in (or already checked out) needs that surfaced regardless
    # of whether their pass has since been revoked or timed out.
    # Otherwise a resident revoking mid-visit would hide the "check them
    # out" shortcut behind a generic "not valid" message, even though
    # the visitor is still on the property.
    if visitor.status not in ('checked_in', 'checked_out'):
        if _is_not_yet_valid(visitor):
            return jsonify({'error': f"This pass isn't valid yet — valid on {visitor.expected_date.isoformat()}"}), 404
        if not _is_usable(visitor):
            return jsonify({'error': 'This pass is not valid'}), 404

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

    # ADDED — check status before usability: a checked-in visitor whose
    # pass gets revoked mid-visit should still be reported as "already
    # checked in", not bounced with a generic "not valid" error.
    if visitor.status == 'checked_in':
        return jsonify({'error': f'{visitor.name} is already checked in'}), 400

    if _is_not_yet_valid(visitor):
        return jsonify({'error': f"This pass isn't valid yet — valid on {visitor.expected_date.isoformat()}"}), 400

    if not _is_usable(visitor):
        return jsonify({'error': 'This pass is not valid'}), 400

    visitor.status        = 'checked_in'
    visitor.id_verified   = True
    visitor.check_in_time = datetime.utcnow()

    # queued on this same session — commits atomically with the checkin
    _notify_resident_of_visitor_event(visitor, 'checked_in')

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

    # ADDED — previously had no status check at all, so a visitor who was
    # never checked in (or already checked out) could still be "checked
    # out" again, overwriting check_out_time and leaving no error trail.
    if visitor.status != 'checked_in':
        return jsonify({'error': f'{visitor.name} is not currently checked in'}), 400

    visitor.status         = 'checked_out'
    visitor.check_out_time = datetime.utcnow()

    # A one-time-use pass is spent after its single visit — cut its
    # validity off right now so it can't be checked in again. A multi-use
    # pass is untouched here; it keeps whatever expiry (or none) it was
    # given at creation.
    if not visitor.is_multi_use:
        visitor.expires_at = datetime.utcnow()

    # queued on this same session — commits atomically with the checkout
    _notify_resident_of_visitor_event(visitor, 'checked_out')

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
    if visitor.revoked:
        return jsonify({'error': 'This pass has already been revoked'}), 400
    if _is_timed_out(visitor):
        return jsonify({'error': 'This pass has already expired'}), 400
    # any non-terminal status (pre_registered / checked_in / checked_out)
    # can be revoked as long as it's not already expired or revoked —
    # matches activePasses on the frontend, so anything shown there is
    # always revocable
    if visitor.status not in ('pre_registered', 'checked_in', 'checked_out'):
        return jsonify({'error': 'This pass can no longer be revoked'}), 400

    visitor.revoked    = True
    visitor.revoked_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        'message': 'Pass revoked',
        'visitor': visitor_to_dict(visitor),
    }), 200


# ── PATCH /api/visitors/<id>/schedule — resident edits expected_date /
# expected_time / valid_until on their own pre-registered pass ─────
# Deliberately narrow: only these three fields are editable, and only
# while the pass hasn't been used yet — a pass that's already checked in,
# checked out, revoked, or expired should go through "generate again"
# instead of being rewritten in place.

@visitors_bp.route('/<visitor_id>/schedule', methods=['PATCH'])
@login_required
def update_visitor_schedule(visitor_id):
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can edit their own passes'}), 403

    visitor = Visitor.query.get_or_404(visitor_id)
    if visitor.resident_id != current_user.resident.id:
        return jsonify({'error': 'Not your visitor'}), 403
    if visitor.visit_type != 'pre_registered':
        return jsonify({'error': 'Only pre-registered passes can be edited'}), 400
    if visitor.revoked:
        return jsonify({'error': 'Cannot edit a revoked pass'}), 400
    if _is_timed_out(visitor):
        return jsonify({'error': 'Cannot edit an expired pass'}), 400
    if visitor.status != 'pre_registered':
        return jsonify({'error': 'Can only edit a pass that hasn\'t been used yet'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Each field is only touched if the key is present at all, so the
    # resident can send just the one thing they're changing — `null`
    # explicitly clears a field, omitting the key leaves it untouched.
    expected_date = visitor.expected_date
    if 'expected_date' in data:
        if data['expected_date']:
            try:
                expected_date = datetime.strptime(data['expected_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'expected_date must be YYYY-MM-DD'}), 400
        else:
            expected_date = None

    expected_time = visitor.expected_time
    if 'expected_time' in data:
        if data['expected_time']:
            try:
                expected_time = datetime.strptime(data['expected_time'], '%H:%M').time()
            except ValueError:
                return jsonify({'error': 'expected_time must be HH:MM'}), 400
        else:
            expected_time = None

    valid_until = visitor.valid_until
    if 'valid_until' in data:
        if data['valid_until']:
            try:
                valid_until = datetime.strptime(data['valid_until'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'valid_until must be YYYY-MM-DD'}), 400
        else:
            valid_until = None

    # exact_date / until_date both need expected_date to expire against —
    # same rule as at creation time, so an edit can't leave the pass
    # without a date it actually requires.
    if visitor.validity_mode in ('exact_date', 'until_date') and not expected_date:
        return jsonify({'error': 'Expected date is required for this validity mode'}), 400

    visitor.expected_date = expected_date
    visitor.expected_time = expected_time
    visitor.valid_until   = valid_until
    visitor.expires_at    = _compute_expires_at(
        visitor.visit_type, expected_date, expected_time, None,
        validity_mode=visitor.validity_mode, valid_until=valid_until,
    )

    db.session.commit()

    return jsonify({
        'message': 'Pass updated',
        'visitor': visitor_to_dict(visitor),
    }), 200