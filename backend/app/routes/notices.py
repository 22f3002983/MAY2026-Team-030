from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.notice import Notice
import uuid
from datetime import datetime, date


notices_bp = Blueprint('notices', __name__)




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




# ── GET /api/notices — list all active notices ────────────────


@notices_bp.route('', methods=['GET'])
@login_required
def list_notices():
    tag       = request.args.get('tag')
    relevance = request.args.get('relevance')


    query = Notice.query.filter_by(is_active=True)


    if tag:
        query = query.filter_by(tag=tag)
    if relevance:
        query = query.filter_by(relevance=relevance)


    notices = query.order_by(Notice.created_at.desc()).all()


    # auto-expire notices past their expiry date
    today = date.today()
    for n in notices:
        if n.expiry_date and n.expiry_date < today:
            n.is_active = False
    db.session.commit()


    active = [n for n in notices if n.is_active]


    return jsonify({
        'notices': [notice_to_dict(n) for n in active],
        'total':   len(active),
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


    valid_tags = ('General', 'Maintenance', 'Security', 'Event', 'Urgent')
    tag = data.get('tag', 'General')
    if tag not in valid_tags:
        return jsonify({'error': f'tag must be one of {valid_tags}'}), 400


    priority = data.get('priority')
    if priority and priority not in ('high', 'medium', 'low'):
        return jsonify({'error': 'priority must be one of high, medium, low'}), 400


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

