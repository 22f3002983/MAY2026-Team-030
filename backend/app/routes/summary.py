from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models.complaint import Complaint
from app.models.community_issue import CommunityIssue
from app.models.dues import Dues
from app.models.vendor import Vendor
from app.models.notice import Notice
from app.models.booking import Booking
from app.models.visitor import Visitor
from app.models.emergency import EmergencyAlert
from datetime import datetime, date
from app.extensions import db

summary_bp = Blueprint('summary', __name__)


@summary_bp.route('/resident', methods=['GET'])
@login_required
def resident_summary():
    if current_user.role != 'resident':
        return jsonify({'error': 'Unauthorized'}), 403

    resident_id = current_user.resident.id

    own_reports = Complaint.query.filter_by(resident_id=resident_id).all()

    # open complaints
    open_complaints = sum(1 for r in own_reports if r.issue and r.issue.status in ('open', 'in_progress'))

    # in progress complaints
    in_progress = sum(1 for r in own_reports if r.issue and r.issue.status == 'in_progress')

    # pending dues
    all_dues    = Dues.query.filter_by(resident_id=resident_id).all()
    pending_due = sum(
        float(d.amount_due) - float(d.amount_paid)
        for d in all_dues
        if float(d.amount_paid) < float(d.amount_due)
    )

    # upcoming bookings
    today           = date.today()
    upcoming_booking = Booking.query.filter_by(
        resident_id=resident_id,
        status='approved'
    ).filter(
        Booking.date >= today
    ).order_by(Booking.date).first()

    # latest notice
    latest_notice = Notice.query.filter_by(
        is_active=True
    ).order_by(Notice.created_at.desc()).first()

    # recent complaints for feed — resident's own reports, newest first
    recent_reports = sorted(own_reports, key=lambda r: r.created_at or datetime.min, reverse=True)[:4]

    return jsonify({
        'open_complaints': open_complaints,
        'in_progress':     in_progress,
        'pending_due':     pending_due,
        'upcoming_booking': {
            'id':         upcoming_booking.id,
            'amenity_id': upcoming_booking.amenity_id,
            'date':       upcoming_booking.date.isoformat(),
        } if upcoming_booking else None,
        'latest_notice': {
            'title': latest_notice.title,
            'date':  latest_notice.created_at.strftime('%d %b'),
        } if latest_notice else None,
        'recent_complaints': [{
            'id':          r.id,
            'description': r.description,
            'category':    r.issue.category if r.issue else None,
            'status':      r.issue.status if r.issue else None,
            'priority':    r.issue.priority if r.issue else None,
            'created_at':  r.created_at.isoformat(),
        } for r in recent_reports],
    }), 200


@summary_bp.route('/secretary', methods=['GET'])
@login_required
def secretary_summary():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Unauthorized'}), 403

    # open complaints (issue-level — one row per actual problem)
    open_complaints = CommunityIssue.query.filter_by(status='open').count()
    today_complaints = CommunityIssue.query.filter(
        CommunityIssue.status == 'open',
        CommunityIssue.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()

    # pending dues
    all_dues    = Dues.query.all()
    pending_dues = sum(
        float(d.amount_due) - float(d.amount_paid)
        for d in all_dues
        if float(d.amount_paid) < float(d.amount_due)
    )
    pending_flats = len([d for d in all_dues if float(d.amount_paid) < float(d.amount_due)])

    # active vendors
    active_vendors = Vendor.query.filter_by(status='active').count()

    # unread notices
    unread_notices = Notice.query.filter_by(is_active=True).count()

    # unassigned issues
    unassigned = CommunityIssue.query.filter(
        CommunityIssue.vendor_id == None,
        CommunityIssue.status != 'resolved'
    ).count()

    # latest issues for feed
    recent_issues = CommunityIssue.query.order_by(
        CommunityIssue.created_at.desc()
    ).limit(4).all()

    return jsonify({
        'open_complaints':  open_complaints,
        'today_complaints': today_complaints,
        'pending_dues':     pending_dues,
        'pending_flats':    pending_flats,
        'active_vendors':   active_vendors,
        'unread_notices':   unread_notices,
        'unassigned':       unassigned,
        'recent_complaints': [{
            'id':          i.id,
            'description': i.description,
            'category':    i.category,
            'status':      i.status,
            'priority':    i.priority,
            'resident_id': i.created_by,
            'created_at':  i.created_at.isoformat(),
        } for i in recent_issues],
    }), 200

def _is_timed_out(v):
    return bool(v.expires_at and datetime.utcnow() > v.expires_at)


@summary_bp.route('/security', methods=['GET'])
@login_required
def security_summary():
    if current_user.role != 'security':
        return jsonify({'error': 'Unauthorized'}), 403

    today     = date.today()
    day_start = datetime.combine(today, datetime.min.time())
    day_end   = datetime.combine(today, datetime.max.time())

    todays_visitors = Visitor.query.filter(
        db.or_(
            Visitor.expected_date == today,
            db.and_(Visitor.check_in_time >= day_start, Visitor.check_in_time <= day_end),
        )
    ).all()

    visitors_inside   = Visitor.query.filter_by(status='checked_in').count()
    awaiting_approval = sum(1 for v in todays_visitors if v.status == 'awaiting_approval')
    pre_registered    = sum(
        1 for v in todays_visitors
        if v.status == 'pre_registered' and not v.revoked and not _is_timed_out(v)
    )
    # matches "delivery"/"deliveries" in the free-text reason field —
    # there is no dedicated visitor category for this yet
    deliveries_today = sum(
        1 for v in todays_visitors
        if v.reason and ('delivery' in v.reason.lower() or 'deliveries' in v.reason.lower())
    )

    return jsonify({
        'visitors_inside':     visitors_inside,
        'awaiting_approval':   awaiting_approval,
        'pre_registered':      pre_registered,
        'deliveries_today':    deliveries_today,
    }), 200