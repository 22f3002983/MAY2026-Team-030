from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.emergency import EmergencyAlert
import uuid
from datetime import datetime, timezone
from sqlalchemy import or_


emergency_bp = Blueprint('emergency', __name__)


# ── helper ────────────────────────────────────────────────────

def alert_to_dict(a):
    return {
        'id':          a.id,
        'type':        a.type,
        'message':     a.message,
        'created_by':  a.created_by,
        'status':      a.status,
        'location_info': a.location_info,
        'severity':    a.severity,
        'resolved_at': a.resolved_at.isoformat() if a.resolved_at else None,
        'created_at':  a.created_at.isoformat() if a.created_at else None,
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

    db.session.commit()

    return jsonify({
        'message': 'Alert resolved',
        'alert':   alert_to_dict(alert),
    }), 200