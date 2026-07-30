from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.extensions import db
from app.models.notice import Notice
import uuid
from datetime import datetime, date
from app.models.flat import Flat

notices_bp = Blueprint('notices', __name__)

VALID_TAGS = ('General', 'Maintenance', 'Security', 'Event', 'Urgent')
VALID_PRIORITIES = ('normal', 'urgent')
VALID_STATUSES = ('active', 'expired', 'all')


# ── helper ────────────────────────────────────────────────────

def notice_to_dict(n):
    return {
        'id':          n.id,
        'title':       n.title,
        'description': n.description,
        'tag':         n.tag,
        'priority':    n.priority,
        'relevance':   n.relevance,
        'expiry_date': n.expiry_date.isoformat() if n.expiry_date else None,
        'created_by':  n.created_by,
        'created_at':  n.created_at.isoformat() if n.created_at else None,
        'is_active':   n.is_active,
    }


def auto_expire_notices():
    """Bulk-flip is_active=False for any notice whose expiry_date has passed.
    Runs as a single UPDATE so it isn't scoped to whatever tag/relevance
    filters the current request happens to apply."""
    today = date.today()
    Notice.query.filter(
        Notice.is_active.is_(True),
        Notice.expiry_date.isnot(None),
        Notice.expiry_date < today,
    ).update({'is_active': False}, synchronize_session=False)
    db.session.commit()


# ── GET /api/notices — list notices ────────────────────────────

@notices_bp.route('', methods=['GET'])
@login_required
def list_notices():
    tag       = request.args.get('tag')
    relevance = request.args.get('relevance')
    status    = request.args.get('status', 'active')  # active | expired | all

    if status not in VALID_STATUSES:
        return jsonify({'error': f'status must be one of {VALID_STATUSES}'}), 400

    # keep is_active accurate before filtering on it
    auto_expire_notices()

    query = Notice.query

    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'expired':
        query = query.filter_by(is_active=False)
    # status == 'all' -> no is_active filter

    if tag:
        query = query.filter_by(tag=tag)
    if relevance is None and current_user.role == 'resident':
        resident = current_user.resident
        if resident and resident.flat_id and resident.flat:
            relevance = resident.flat.tower
    if relevance:
        # a resident filtering by their block should still see 'all'-relevance notices
        query = query.filter(or_(Notice.relevance == relevance, Notice.relevance == 'all'))

    notices = query.order_by(Notice.created_at.desc()).all()

    return jsonify({
        'notices': [notice_to_dict(n) for n in notices],
        'total':   len(notices),
    }), 200


# ── GET /api/notices/<id> — get single notice ─────────────────

@notices_bp.route('/<notice_id>', methods=['GET'])
@login_required
def get_notice(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    return jsonify({'notice': notice_to_dict(notice)}), 200


# ── POST /api/notices — create notice (secretary only) ────────

@notices_bp.route('', methods=['POST'])
@login_required
def create_notice():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can post notices'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title       = data.get('title', '').strip()
    description = data.get('description', '').strip()
    expiry_date = data.get('expiry_date')

    if not title or not description or not expiry_date:
        return jsonify({'error': 'title, description and expiry_date are required'}), 400

    try:
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'expiry_date must be in YYYY-MM-DD format'}), 400

    if expiry < date.today():
        return jsonify({'error': 'expiry_date cannot be in the past'}), 400

    tag = data.get('tag', 'General')
    if tag not in VALID_TAGS:
        return jsonify({'error': f'tag must be one of {VALID_TAGS}'}), 400

    priority = data.get('priority', 'normal')
    if priority not in VALID_PRIORITIES:
        return jsonify({'error': f'priority must be one of {VALID_PRIORITIES}'}), 400

    notice = Notice(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        tag=tag,
        priority=priority,
        relevance=data.get('relevance', 'all'),
        expiry_date=expiry,
        created_by=current_user.secretary.id,
        is_active=True,
    )

    db.session.add(notice)
    db.session.commit()

    return jsonify({
        'message': 'Notice posted successfully',
        'notice':  notice_to_dict(notice),
    }), 201


# ── PATCH /api/notices/<id> — edit notice (secretary only) ────

@notices_bp.route('/<notice_id>', methods=['PATCH'])
@login_required
def update_notice(notice_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can edit notices'}), 403

    notice = Notice.query.get_or_404(notice_id)

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'title' in data:
        title = (data['title'] or '').strip()
        if not title:
            return jsonify({'error': 'title cannot be empty'}), 400
        notice.title = title

    if 'description' in data:
        description = (data['description'] or '').strip()
        if not description:
            return jsonify({'error': 'description cannot be empty'}), 400
        notice.description = description

    if 'tag' in data:
        if data['tag'] not in VALID_TAGS:
            return jsonify({'error': f'tag must be one of {VALID_TAGS}'}), 400
        notice.tag = data['tag']

    if 'priority' in data:
        if data['priority'] not in VALID_PRIORITIES:
            return jsonify({'error': f'priority must be one of {VALID_PRIORITIES}'}), 400
        notice.priority = data['priority']

    if 'relevance' in data:
        notice.relevance = data['relevance']

    if 'expiry_date' in data:
        try:
            expiry = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'expiry_date must be in YYYY-MM-DD format'}), 400
        if expiry < date.today():
            return jsonify({'error': 'expiry_date cannot be in the past'}), 400
        notice.expiry_date = expiry
        # editing the expiry forward implies the notice should be live again
        notice.is_active = True

    db.session.commit()

    return jsonify({
        'message': 'Notice updated successfully',
        'notice':  notice_to_dict(notice),
    }), 200


# ── PATCH /api/notices/<id>/status — activate/deactivate ──────

@notices_bp.route('/<notice_id>/status', methods=['PATCH'])
@login_required
def set_notice_status(notice_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can change notice status'}), 403

    notice = Notice.query.get_or_404(notice_id)

    data = request.get_json()
    if not data or 'is_active' not in data:
        return jsonify({'error': 'is_active (boolean) is required'}), 400

    is_active = data['is_active']
    if not isinstance(is_active, bool):
        return jsonify({'error': 'is_active must be a boolean'}), 400

    notice.is_active = is_active
    db.session.commit()

    return jsonify({
        'message': 'Notice reactivated successfully' if is_active else 'Notice deactivated successfully',
        'notice':  notice_to_dict(notice),
    }), 200


# ── DELETE /api/notices/<id> — delete notice (secretary only) ─

@notices_bp.route('/<notice_id>', methods=['DELETE'])
@login_required
def delete_notice(notice_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can delete notices'}), 403

    notice = Notice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()

    return jsonify({'message': 'Notice deleted successfully'}), 200
