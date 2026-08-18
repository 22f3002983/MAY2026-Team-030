from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.emergency import EmergencyAlert
from app.routes.notifications import create_notification
import uuid
from datetime import datetime, timezone
from sqlalchemy import or_


emergency_bp = Blueprint('emergency', __name__)


def _alert_audience(alert_type):
    """user_ids that should hear about this alert in-app: secretary + security
    always, residents too if it's Public. Mirrors the telegram broadcast list
    in create_alert, but keyed by user_id (not telegram_chat_id) since every
    user should get the in-app notification regardless of telegram linkage."""
    from app.models.resident import Resident
    from app.models.secretary import Secretary
    from app.models.security import Security

    user_ids = [s.user_id for s in Secretary.query.all()]
    user_ids += [s.user_id for s in Security.query.all()]
    if alert_type == 'Public':
        user_ids += [r.user_id for r in Resident.query.all()]
    return user_ids


# ── helper ────────────────────────────────────────────────────

def _display_name(user):
    if not user:
        return None
    if user.role == 'resident' and user.resident:
        return user.resident.name
    if user.role == 'secretary' and user.secretary:
        return user.secretary.name
    if user.role == 'security' and user.security:
        return user.security.name
    return None


def alert_to_dict(a):
    return {
        'id':               a.id,
        'type':             a.type,
        'message':          a.message,
        'created_by':       a.created_by,
        'created_by_name':  _display_name(a.creator),
        'status':           a.status,
        'location_info':    a.location_info,
        'severity':         a.severity,
        'resolved_at':      a.resolved_at.isoformat() if a.resolved_at else None,
        'resolved_by':      a.resolved_by,
        'resolved_by_name': _display_name(a.resolver),
        'created_at':       a.created_at.isoformat() if a.created_at else None,
    }


# ── GET /api/emergency — list alerts ──────────────────────────

@emergency_bp.route('/<alert_id>', methods=['GET'])
@login_required
def get_alert(alert_id):
    alert = EmergencyAlert.query.get_or_404(alert_id)
    return jsonify(alert_to_dict(alert)), 200

@emergency_bp.route('', methods=['GET'])
@login_required
def list_alerts():
    status = request.args.get('status')
    query  = EmergencyAlert.query

    # residents only see public alerts or alerts raised by themselves
    if current_user.role == 'resident':
        query = query.filter(
            or_(EmergencyAlert.type == 'Public',
                EmergencyAlert.created_by == current_user.id)
    )

    if status:
        query = query.filter_by(status=status)

    alerts = query.order_by(EmergencyAlert.created_at.desc()).all()

    return jsonify({
        'alerts': [alert_to_dict(a) for a in alerts],
        'total':  len(alerts),
    }), 200


# ── POST /api/emergency — create alert ────────────────────────

@emergency_bp.route('', methods=['POST'])
@login_required
def create_alert():
    # resident, secretary and security can all trigger alerts
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    message    = data.get('message', '').strip()
    alert_type = data.get('type', 'Public')

    if not message:
        return jsonify({'error': 'message is required'}), 400

    if alert_type not in ('Public', 'Private'):
        return jsonify({'error': 'type must be Public or Private'}), 400

    severity = data.get('severity')
    if severity and severity not in ('low', 'medium', 'high', 'critical'):
        return jsonify({'error': 'severity must be one of low, medium, high, critical'}), 400

    alert = EmergencyAlert(
        id=str(uuid.uuid4()),
        type=alert_type,
        message=message,
        created_by=current_user.id,
        status='active',
        location_info=data.get('location_info'),
        severity=severity,
    )

    db.session.add(alert)
    db.session.commit()
    
    from app.telegram_bot import send_telegram_message_bulk
    from app.models.resident import Resident
    from app.models.secretary import Secretary
    from app.models.security import Security


    telegram_message = (
        f'🚨 EMERGENCY ALERT — Niwaas RWA\n\n'
        f'Message: {message}\n'
        f'Type: {alert_type}\n'
        f'Raised by: {current_user.role}\n\n'
        f'Please take immediate action.'
    )


    chat_ids = [s.telegram_chat_id for s in Secretary.query.filter(Secretary.telegram_chat_id.isnot(None)).all()]
    chat_ids += [s.telegram_chat_id for s in Security.query.filter(Security.telegram_chat_id.isnot(None)).all()]
    if alert_type == 'Public':
        chat_ids += [r.telegram_chat_id for r in Resident.query.filter(Resident.telegram_chat_id.isnot(None)).all()]


    send_telegram_message_bulk(chat_ids, telegram_message)

    in_app_message = f'🚨 {alert_type} emergency alert: {message}'
    for user_id in _alert_audience(alert_type):
        # don't notify the person who just raised it
        if user_id == current_user.id:
            continue
        create_notification(user_id=user_id, message=in_app_message, type='emergency_alert')
    db.session.commit()

    return jsonify({
        'message': 'Emergency alert sent',
        'alert':   alert_to_dict(alert),
    }), 201


# ── PATCH /api/emergency/<id>/resolve — resolve alert ─────────

@emergency_bp.route('/<alert_id>/resolve', methods=['PATCH'])
@login_required
def resolve_alert(alert_id):
    if current_user.role not in ('secretary', 'security'):
        return jsonify({'error': 'Only secretary or security can resolve alerts'}), 403

    alert = EmergencyAlert.query.get_or_404(alert_id)
    alert.status      = 'resolved'
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = current_user.id

    resolved_message = f'✅ {alert.type} emergency alert resolved: {alert.message}'
    for user_id in _alert_audience(alert.type):
        if user_id == current_user.id:
            continue
        create_notification(user_id=user_id, message=resolved_message, type='emergency_alert')

    db.session.commit()

    return jsonify({
        'message': 'Alert resolved',
        'alert':   alert_to_dict(alert),
    }), 200