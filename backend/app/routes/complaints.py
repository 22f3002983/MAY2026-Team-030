from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.complaint import Complaint
from app.models.community_issue import CommunityIssue
from app.models.resident import Resident
from app.models.vendor import Vendor
from app.routes.notifications import create_notification
from app.services.ai_priority import suggest_priority
import uuid
from datetime import datetime

complaints_bp = Blueprint('complaints', __name__)

VALID_CATEGORIES = ('plumbing', 'electrical', 'cleaning', 'carpentry', 'other')
VALID_TYPES      = ('personal', 'common_area')
VALID_STATUSES   = ('open', 'in_progress', 'resolved', 'closed')


# ── helpers ───────────────────────────────────────────────────

def complaint_to_dict(c):
    """Flattened view of one resident's report, joined with its parent
    community issue — matches the pre-re-architecture API shape so existing
    frontend code and tests keep working unchanged."""
    issue = c.issue
    return {
        'id':                    c.id,
        'issue_id':              c.issue_id,
        'resident_id':           c.resident_id,
        'description':           c.description,
        'feedback_rating':       c.feedback_rating,
        'feedback_comment':      c.feedback_comment,
        'created_at':            c.created_at.isoformat() if c.created_at else None,
        'title':                 issue.title if issue else None,
        'category':              issue.category if issue else None,
        'ai_suggested_category': issue.ai_suggested_category if issue else None,
        'priority':              issue.priority if issue else None,
        'ai_suggested_priority': issue.ai_suggested_priority if issue else None,
        'type':                  issue.type if issue else None,
        'location':              issue.location if issue else None,
        'status':                issue.status if issue else None,
        'vendor_id':             issue.vendor_id if issue else None,
        'vendor_whatsapp_status':issue.vendor_whatsapp_status if issue else None,
        'resolved_at':           issue.resolved_at.isoformat() if issue and issue.resolved_at else None,
    }


def issue_to_dict(issue, include_reporters=True):
    # query fresh rather than trusting issue.reports' in-memory state, which
    # can go stale within the same request after a merge reassigns rows via
    # direct FK updates on the *other* issue's Complaint objects
    reports = Complaint.query.filter_by(issue_id=issue.id).order_by(Complaint.created_at).all()
    d = {
        'id':                       issue.id,
        'title':                    issue.title,
        'description':              issue.description,
        'ai_suggested_description': issue.ai_suggested_description,
        'category':                 issue.category,
        'ai_suggested_category':    issue.ai_suggested_category,
        'priority':                 issue.priority,
        'ai_suggested_priority':    issue.ai_suggested_priority,
        'type':                     issue.type,
        'location':                 issue.location,
        'status':                   issue.status,
        'vendor_id':                issue.vendor_id,
        'vendor_whatsapp_status':   issue.vendor_whatsapp_status,
        'vendor_start_time':        issue.vendor_start_time.isoformat() if issue.vendor_start_time else None,
        'vendor_end_time':          issue.vendor_end_time.isoformat() if issue.vendor_end_time else None,
        'created_by':               issue.created_by,
        'created_at':               issue.created_at.isoformat() if issue.created_at else None,
        'resolved_at':              issue.resolved_at.isoformat() if issue.resolved_at else None,
        'reporter_count':           len(reports),
    }
    if include_reporters:
        d['reporters'] = [{
            'complaint_id':     r.id,
            'resident_id':      r.resident_id,
            'resident_name':    r.resident.name if r.resident else None,
            'description':      r.description,
            'feedback_rating':  r.feedback_rating,
            'feedback_comment': r.feedback_comment,
            'created_at':       r.created_at.isoformat() if r.created_at else None,
        } for r in reports]
    return d


def resolve_issue(id_):
    """Accepts either a CommunityIssue id or a Complaint (report) id and
    always returns the parent CommunityIssue — lets secretary actions work
    whether they're operating from an issue-level list or a complaint id."""
    issue = CommunityIssue.query.get(id_)
    if issue:
        return issue
    complaint = Complaint.query.get(id_)
    if complaint:
        return CommunityIssue.query.get(complaint.issue_id)
    return None


def find_matching_issue(title, category):
    """An issue 'matches' a new report if it has the same (normalized)
    title and category and is still open/in_progress — deliberately simple
    and deterministic, consistent with the rest of the app's AI heuristics."""
    normalized_title = title.strip().lower()
    candidates = CommunityIssue.query.filter(
        CommunityIssue.category == category,
        CommunityIssue.status.in_(['open', 'in_progress']),
    ).all()
    for candidate in candidates:
        if candidate.title.strip().lower() == normalized_title:
            return candidate
    return None


def notify_reporters(issue, message, notif_type):
    for report in issue.reports:
        if report.resident and report.resident.user_id:
            create_notification(user_id=report.resident.user_id, message=message, type=notif_type)


# ── POST /api/complaints — raise a complaint (resident only) ──

@complaints_bp.route('', methods=['POST'])
@login_required
def create_complaint():
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can raise complaints'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    title       = data.get('title', '').strip()
    description = data.get('description', '').strip()
    category    = data.get('category', '')
    type_       = data.get('type', '')

    if not title or not description or not category or not type_:
        return jsonify({'error': 'title, description, category and type are required'}), 400

    if category not in VALID_CATEGORIES:
        return jsonify({'error': f'category must be one of {VALID_CATEGORIES}'}), 400

    if type_ not in VALID_TYPES:
        return jsonify({'error': f'type must be one of {VALID_TYPES}'}), 400

    issue = find_matching_issue(title, category)
    is_new_issue = issue is None

    if is_new_issue:
        issue = CommunityIssue(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            ai_suggested_description=data.get('ai_suggested_description'),
            category=category,
            ai_suggested_category=data.get('ai_suggested_category'),
            priority=data.get('priority', 'medium'),
            ai_suggested_priority=suggest_priority(title, description, category),
            type=type_,
            location=data.get('location'),
            status='open',
            created_by=current_user.resident.id,
        )
        db.session.add(issue)
        db.session.flush()  # get issue.id before the complaint row references it

    complaint = Complaint(
        id=str(uuid.uuid4()),
        issue_id=issue.id,
        resident_id=current_user.resident.id,
        description=description,
    )
    db.session.add(complaint)
    db.session.commit()

    message = 'Complaint raised successfully' if is_new_issue else 'Added your report to an existing open issue'

    return jsonify({
        'message':   message,
        'complaint': complaint_to_dict(complaint),
    }), 201


# ── GET /api/complaints — list complaints ─────────────────────
# resident sees their own report rows (joined with issue data)
# secretary sees all community_issues with reporter counts

@complaints_bp.route('', methods=['GET'])
@login_required
def list_complaints():
    status   = request.args.get('status')
    category = request.args.get('category')
    priority = request.args.get('priority')

    if current_user.role == 'resident':
        query = Complaint.query.filter_by(resident_id=current_user.resident.id)
        reports = query.order_by(Complaint.created_at.desc()).all()

        if status:
            reports = [r for r in reports if r.issue and r.issue.status == status]
        if category:
            reports = [r for r in reports if r.issue and r.issue.category == category]
        if priority:
            reports = [r for r in reports if r.issue and r.issue.priority == priority]

        return jsonify({
            'complaints': [complaint_to_dict(r) for r in reports],
            'total':      len(reports),
        }), 200

    elif current_user.role == 'secretary':
        query = CommunityIssue.query
        if status:
            query = query.filter_by(status=status)
        if category:
            query = query.filter_by(category=category)
        if priority:
            query = query.filter_by(priority=priority)

        issues = query.order_by(CommunityIssue.created_at.desc()).all()

        return jsonify({
            'complaints': [issue_to_dict(i) for i in issues],
            'total':      len(issues),
        }), 200

    else:
        return jsonify({'error': 'Unauthorized'}), 403


# ── GET /api/complaints/<id> — get single complaint/issue ─────

@complaints_bp.route('/<id_>', methods=['GET'])
@login_required
def get_complaint(id_):
    if current_user.role == 'resident':
        complaint = Complaint.query.get_or_404(id_)
        if complaint.resident_id != current_user.resident.id:
            return jsonify({'error': 'Unauthorized'}), 403
        return jsonify({'complaint': complaint_to_dict(complaint)}), 200

    issue = resolve_issue(id_)
    if not issue:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'complaint': issue_to_dict(issue)}), 200


# ── PATCH /api/complaints/<id>/assign — assign vendor (secretary only) ──

@complaints_bp.route('/<id_>/assign', methods=['PATCH'])
@login_required
def assign_vendor(id_):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can assign vendors'}), 403

    issue = resolve_issue(id_)
    if not issue:
        return jsonify({'error': 'Not found'}), 404

    data      = request.get_json()
    vendor_id = data.get('vendor_id')

    if not vendor_id:
        return jsonify({'error': 'vendor_id is required'}), 400

    vendor = Vendor.query.get_or_404(vendor_id)

    # optional — lets the secretary schedule the vendor's visit in the same
    # call; columns already existed on CommunityIssue but were unused until now
    start_raw = data.get('vendor_start_time')
    end_raw   = data.get('vendor_end_time')
    if start_raw:
        # JS's toISOString() emits a trailing 'Z', which Python 3.10's
        # fromisoformat() can't parse directly
        issue.vendor_start_time = datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
    if end_raw:
        issue.vendor_end_time = datetime.fromisoformat(end_raw.replace('Z', '+00:00'))

    issue.vendor_id              = vendor.id
    issue.vendor_whatsapp_status = 'notified'
    if issue.status == 'open':
        issue.status = 'in_progress'

    notify_reporters(
        issue,
        message=f'Your complaint ({issue.title}) has been assigned to {vendor.name}',
        notif_type='complaint_updated',
    )

    db.session.commit()

    # respond with whichever report row the id resolved through, so the
    # response shape stays consistent whether called with a complaint id
    # or an issue id
    complaint = Complaint.query.get(id_)
    result = complaint_to_dict(complaint) if complaint else issue_to_dict(issue)

    return jsonify({
        'message':   f'Complaint assigned to {vendor.name}',
        'complaint': result,
    }), 200


# ── PATCH /api/complaints/<id>/status — update status ────────

@complaints_bp.route('/<id_>/status', methods=['PATCH'])
@login_required
def update_status(id_):
    data       = request.get_json()
    new_status = data.get('status')

    if new_status not in VALID_STATUSES:
        return jsonify({'error': f'status must be one of {VALID_STATUSES}'}), 400

    if current_user.role == 'resident':
        complaint = Complaint.query.get_or_404(id_)
        if complaint.resident_id != current_user.resident.id:
            return jsonify({'error': 'Unauthorized'}), 403
        issue = complaint.issue
    elif current_user.role == 'secretary':
        issue = resolve_issue(id_)
        if not issue:
            return jsonify({'error': 'Not found'}), 404
    else:
        return jsonify({'error': 'Unauthorized'}), 403

    issue.status = new_status
    if new_status == 'resolved':
        issue.resolved_at = datetime.utcnow()

    db.session.commit()

    complaint = Complaint.query.get(id_)
    result = complaint_to_dict(complaint) if complaint else issue_to_dict(issue)

    return jsonify({
        'message':   'Status updated',
        'complaint': result,
    }), 200


# ── PATCH /api/complaints/<id>/feedback — resident submits feedback ──

@complaints_bp.route('/<complaint_id>/feedback', methods=['PATCH'])
@login_required
def submit_feedback(complaint_id):
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can submit feedback'}), 403

    complaint = Complaint.query.get_or_404(complaint_id)

    if complaint.resident_id != current_user.resident.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if not complaint.issue or complaint.issue.status != 'resolved':
        return jsonify({'error': 'Can only submit feedback on resolved complaints'}), 400

    data   = request.get_json()
    rating = data.get('feedback_rating')
    comment= data.get('feedback_comment', '')

    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'error': 'feedback_rating must be an integer between 1 and 5'}), 400

    complaint.feedback_rating  = rating
    complaint.feedback_comment = comment

    db.session.commit()

    return jsonify({
        'message':   'Feedback submitted',
        'complaint': complaint_to_dict(complaint),
    }), 200


# ── POST /api/complaints/<id>/merge — merge two issues (secretary only) ──

@complaints_bp.route('/<id_>/merge', methods=['POST'])
@login_required
def merge_issues(id_):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can merge issues'}), 403

    data          = request.get_json() or {}
    other_issue_id = data.get('other_issue_id')

    if not other_issue_id:
        return jsonify({'error': 'other_issue_id is required'}), 400

    primary = resolve_issue(id_)
    other   = resolve_issue(other_issue_id)

    if not primary or not other:
        return jsonify({'error': 'Not found'}), 404

    if primary.id == other.id:
        return jsonify({'error': 'Cannot merge an issue into itself'}), 400

    moved = 0
    for report in Complaint.query.filter_by(issue_id=other.id).all():
        report.issue_id = primary.id
        moved += 1

    db.session.delete(other)
    db.session.commit()

    return jsonify({
        'message':  f'Merged {moved} report(s) into this issue',
        'complaint': issue_to_dict(primary),
    }), 200
