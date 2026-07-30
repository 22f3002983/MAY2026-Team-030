from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.notification import Notification
import uuid

notifications_bp = Blueprint('notifications', __name__)


# ── helper — other blueprints import and call this ─────────────

def create_notification(user_id, message, type='general'):
    """Queue a notification on the current db.session — does not commit,
    so the caller's own commit() persists it atomically with its action."""
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        message=message,
        type=type,
    )
    db.session.add(notification)
    return notification


def notification_to_dict(n):
    return {
        'id':         n.id,
        'message':    n.message,
        'type':       n.type,
        'is_read':    n.is_read,
        # 'Z' suffix makes the naive UTC timestamp explicit so JS Date parsing
        # doesn't misinterpret it as local time
        'created_at': n.created_at.isoformat() + 'Z' if n.created_at else None,
    }


# ── GET /api/notifications — current user's notifications ─────

@notifications_bp.route('', methods=['GET'])
@login_required
def list_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id) \
        .order_by(Notification.created_at.desc()).limit(20).all()

    return jsonify({
        'notifications': [notification_to_dict(n) for n in notifications],
        'total':         len(notifications),
    }), 200


# ── GET /api/notifications/unread-count ────────────────────────

@notifications_bp.route('/unread-count', methods=['GET'])
@login_required
def unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count}), 200


# ── PATCH /api/notifications/<id>/read ──────────────────────────

@notifications_bp.route('/<notification_id>/read', methods=['PATCH'])
@login_required
def mark_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)

    if notification.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    notification.is_read = True
    db.session.commit()

    return jsonify({
        'message':      'Notification marked read',
        'notification': notification_to_dict(notification),
    }), 200


# ── PATCH /api/notifications/read-all ───────────────────────────

@notifications_bp.route('/read-all', methods=['PATCH'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False) \
        .update({'is_read': True})
    db.session.commit()

    return jsonify({'message': 'All notifications marked read'}), 200
