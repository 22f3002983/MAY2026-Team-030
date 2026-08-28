from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.complaint import Complaint
from app.models.community_issue import CommunityIssue
from app.models.resident import Resident
from app.models.vendor import Vendor
from app.routes.notifications import create_notification
from app.services.ai_priority import suggest_priority
from app.services.ai_category import suggest_category
from app.services.ai_summary import suggest_summary
from app.services.ai_duplicate import find_semantic_duplicates
import uuid
import threading
from datetime import datetime


complaints_bp = Blueprint('complaints', __name__)


VALID_CATEGORIES = ('plumbing', 'electrical', 'cleaning', 'carpentry', 'security', 'gardening', 'pest_control', 'other')
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
        # ADDED — resident's own view was missing schedule info that only
        # existed in issue_to_dict (secretary's shape). Needed so a resident
        # can see when the vendor is coming, same as the secretary does.
        'vendor_start_time':     issue.vendor_start_time.isoformat() if issue and issue.vendor_start_time else None,
        'vendor_end_time':       issue.vendor_end_time.isoformat() if issue and issue.vendor_end_time else None,
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




def notify_reporters(issue, message, notif_type, exclude_user_id=None):
    """Notifies everyone following this issue (i.e. everyone who reported it),
    optionally skipping the user who just triggered the change themselves."""
    for report in issue.reports:
        if report.resident and report.resident.user_id and report.resident.user_id != exclude_user_id:
            create_notification(user_id=report.resident.user_id, message=message, type=notif_type)






def _run_ai_suggestions(flask_app, issue_id, title, description, category, compute_category_priority):
    """Runs off the request thread so POST /api/complaints can return as soon
    as the complaint is saved — same daemon-thread + app_context pattern as
    app/telegram_bot.py and app/scheduler.py. suggest_category/suggest_priority/
    suggest_summary already degrade to None internally (no key / request
    failure), this try/except is just an extra guard so a DB hiccup here
    can't crash the thread silently without a trace.


    Runs on every complaint POST, not just new issues — suggest_summary()
    needs to re-merge descriptions whenever another resident joins an
    existing issue. compute_category_priority is False on the join path,
    since those fields are only meaningful once, at issue creation."""
    with flask_app.app_context():
        try:
            issue = CommunityIssue.query.get(issue_id)
            if not issue:
                return


            if compute_category_priority:
                issue.ai_suggested_category = suggest_category(f'{title}. {description}', VALID_CATEGORIES)
                issue.ai_suggested_priority = suggest_priority(title, description, category)


            all_descriptions = [c.description for c in Complaint.query.filter_by(issue_id=issue_id).all()]
            issue.ai_suggested_description = suggest_summary(issue.title, issue.category, all_descriptions)


            db.session.commit()
        except Exception as exc:
            print(f' * [ai] suggestion failed for issue {issue_id}: {exc}', flush=True)


# ── POST /api/complaints/check-duplicates — pre-submit AI duplicate check ──
# Resident-triggered (a button, not as-you-type) before raising a new issue.
# Returns just the matching issue ids — the frontend already has the full,
# correctly-shaped issue objects loaded for the "Open in Society" tab, so
# there's no need to duplicate that shape here.


@complaints_bp.route('/check-duplicates', methods=['POST'])
@login_required
def check_duplicates():
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can check for duplicates'}), 403


    data = request.get_json() or {}
    title       = data.get('title', '').strip()
    description = data.get('description', '').strip()
    category    = data.get('category', '')


    if not title or not description or category not in VALID_CATEGORIES:
        return jsonify({'error': 'title, description and a valid category are required'}), 400


    candidates = CommunityIssue.query.filter(
        CommunityIssue.category == category,
        CommunityIssue.status.in_(['open', 'in_progress']),
    ).order_by(CommunityIssue.created_at.desc()).limit(15).all()


    # skip issues this resident is already part of — they don't need an AI
    # suggestion to "join" something they already know about
    resident_id = current_user.resident.id
    candidates = [
        i for i in candidates
        if not Complaint.query.filter_by(issue_id=i.id, resident_id=resident_id).first()
    ]


    matched_ids = find_semantic_duplicates(
        title, description,
        [{'id': i.id, 'title': i.title, 'description': i.description} for i in candidates],
    )


    return jsonify({'matches': matched_ids}), 200






# ── POST /api/complaints/suggest — AI category suggestion (pre-submit) ──
# Resident-triggered (a button, not as-you-type) while filling out the raise
# form. Doesn't save anything — just previews what create_complaint's own
# suggest_category() call would land on.


@complaints_bp.route('/suggest', methods=['POST'])
@login_required
def suggest_category_endpoint():
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can request a category suggestion'}), 403


    data = request.get_json() or {}
    description = data.get('description', '').strip()


    if not description:
        return jsonify({'error': 'description is required'}), 400


    category = suggest_category(description, VALID_CATEGORIES)


    if not category:
        return jsonify({'category': None}), 200


    # ai_category.py has no confidence scoring of its own — 'medium' is a
    # fixed placeholder to satisfy the response shape, not a per-request signal
    return jsonify({'category': category, 'confidence': 'medium'}), 200




# ── POST /api/complaints/suggest-priority — AI priority suggestion ──────
# Resident-triggered, fired once a category is selected (not on every
# keystroke). `title` is optional — suggest_priority() takes it as a signal
# alongside description/category, so the frontend passes it when available
# for a better suggestion, but the endpoint works without it.


@complaints_bp.route('/suggest-priority', methods=['POST'])
@login_required
def suggest_priority_endpoint():
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can request a priority suggestion'}), 403


    data = request.get_json() or {}
    description = data.get('description', '').strip()
    category    = data.get('category', '')
    title       = data.get('title', '')


    if not description or category not in VALID_CATEGORIES:
        return jsonify({'error': 'description and a valid category are required'}), 400


    priority = suggest_priority(title, description, category)


    return jsonify({'priority': priority}), 200




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
            category=category,
            # ai_suggested_category=suggest_category(f'{title}. {description}', VALID_CATEGORIES),
            priority=data.get('priority', 'medium'),
            # ai_suggested_priority=suggest_priority(title, description, category),
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
    db.session.flush()  # include this report when gathering descriptions below






    # category/priority/summary all happen off-thread so the response above
    # doesn't wait on OpenRouter — summary re-runs on every post (a join
    # re-merges descriptions), category/priority only on a brand-new issue
    flask_app = current_app._get_current_object()
    threading.Thread(
        target=_run_ai_suggestions,
        args=(flask_app, issue.id, title, description, category, is_new_issue),
        daemon=True,
    ).start()


    db.session.commit()


    message = 'Complaint raised successfully' if is_new_issue else 'Added your report to an existing open issue'


    return jsonify({
        'message':   message,
        'complaint': complaint_to_dict(complaint),
    }), 201




# ── GET /api/complaints — list complaints ─────────────────────
# resident sees their own report rows (joined with issue data) by default.
# resident + ?view=society -> ADDED: all open/in_progress community issues
# society-wide (full reporter list per issue, same shape secretary gets),
# so a resident can browse what's already open and join instead of
# duplicating. Read-only, no ability to see resolved/closed issues they
# didn't participate in.
# secretary sees all community_issues with reporter counts


@complaints_bp.route('', methods=['GET'])
@login_required
def list_complaints():
    status   = request.args.get('status')
    category = request.args.get('category')
    priority = request.args.get('priority')
    view     = request.args.get('view')  # ADDED — 'society' for residents


    if current_user.role == 'resident':
        # ADDED: browse open issues society-wide, not just this resident's own
        if view == 'society':
            query = CommunityIssue.query.filter(CommunityIssue.status.in_(['open', 'in_progress']))
            if category:
                query = query.filter_by(category=category)
            if priority:
                query = query.filter_by(priority=priority)
            issues = query.order_by(CommunityIssue.created_at.desc()).all()
            return jsonify({
                'complaints': [issue_to_dict(i) for i in issues],
                'total':      len(issues),
            }), 200


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




# ── POST /api/complaints/<id>/retry-ai — manual on-demand retry (secretary) ──
# ai_suggested_category/priority are normally set once, in a background
# thread, right when the complaint is created — a single best-effort attempt
# with no retry of its own. The scheduler sweeps for stuck issues every 5
# minutes (see retry_pending_ai_suggestions in scheduler.py), but this lets
# the secretary force an immediate retry instead of waiting for that sweep.
# Only fills whichever field is still None — never overwrites one that
# already has a value, so a working suggestion can't be clobbered.

@complaints_bp.route('/<id_>/retry-ai', methods=['POST'])
@login_required
def retry_ai_suggestions(id_):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can retry AI suggestions'}), 403

    issue = resolve_issue(id_)
    if not issue:
        return jsonify({'error': 'Not found'}), 404

    text = f'{issue.title}. {issue.description}'
    if issue.ai_suggested_category is None:
        issue.ai_suggested_category = suggest_category(text, VALID_CATEGORIES)
    if issue.ai_suggested_priority is None:
        issue.ai_suggested_priority = suggest_priority(issue.title, issue.description, issue.category)

    # summary isn't "fill only if None" like category/priority — it's meant
    # to always reflect the latest set of reports, so a manual retry here
    # always regenerates it (same as _run_ai_suggestions does on every
    # complaint POST), not just when it's missing.
    all_descriptions = [c.description for c in Complaint.query.filter_by(issue_id=issue.id).all()]
    issue.ai_suggested_description = suggest_summary(issue.title, issue.category, all_descriptions)

    db.session.commit()
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


    start_raw = data.get('vendor_start_time')
    end_raw   = data.get('vendor_end_time')
    if start_raw:
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


    complaint = Complaint.query.get(id_)
    result = complaint_to_dict(complaint) if complaint else issue_to_dict(issue)


    # notify the vendor on Telegram if they've connected their account
    if vendor.telegram_chat_id:
        from app.telegram_bot import send_telegram_message
        reporter = complaint.resident if complaint else (issue.reports[0].resident if issue.reports else None)
        flat_number = reporter.flat.flat_number if reporter and reporter.flat else 'N/A'

        if issue.vendor_start_time:
            schedule_line = f"Scheduled: {issue.vendor_start_time.strftime('%d %b, %I:%M %p')}"
            if issue.vendor_end_time:
                schedule_line += f" – {issue.vendor_end_time.strftime('%I:%M %p')}"
            schedule_line += '\n'
        else:
            schedule_line = ''

        vendor_message = (
            f'🔧 New Job Assigned — Niwaas RWA\n\n'
            f'Complaint: {issue.title}\n'
            f'Category: {issue.category}\n'
            f'Description: {issue.description[:100]}\n'
            f'Resident Flat: {flat_number}\n'
            f'{schedule_line}\n'
            f'Please attend at the earliest.\n'
            f'— Niwaas Secretary'
        )
        send_telegram_message(vendor.telegram_chat_id, vendor_message)
    else:
        print(f' * [telegram] vendor {vendor.id} has no telegram_chat_id, skipping notification', flush=True)


    return jsonify({
        'message':   f'Complaint assigned to {vendor.name}',
        'complaint': result,
    }), 200




# ── PATCH /api/complaints/<id>/status — update status ────────


@complaints_bp.route('/<id_>/status', methods=['PATCH'])
@login_required
def update_status(id_):
    data           = request.get_json()
    new_status     = data.get('status')
    payment_amount = data.get('payment_amount')
    payment_fund   = data.get('payment_fund')


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


    # let everyone following this issue know it moved, minus whoever just
    # triggered this update themselves (no point notifying yourself)
    notify_reporters(
        issue,
        message=f'Your complaint ({issue.title}) is now {new_status.replace("_", " ")}',
        notif_type='complaint_updated',
        exclude_user_id=current_user.id if current_user.role == 'resident' else None,
    )


    # notify the assigned vendor on Telegram that the job is done, secretary-
    # initiated closures only — mirrors the assignment notification above
    if (
        current_user.role == 'secretary'
        and new_status in ('resolved', 'closed')
        and issue.vendor
        and issue.vendor.telegram_chat_id
    ):
        from app.telegram_bot import send_telegram_message
        if payment_amount:
            payment_line = f'Payment: ₹{payment_amount}' + (f' ({payment_fund})' if payment_fund else '')
        else:
            payment_line = 'Payment: not applicable'
        vendor_message = (
            f'✅ Job Completed — Niwaas RWA\n\n'
            f'Complaint: {issue.title}\n'
            f'Category: {issue.category}\n'
            f'{payment_line}\n\n'
            f'Thank you for your work!\n'
            f'— Niwaas Secretary'
        )
        send_telegram_message(issue.vendor.telegram_chat_id, vendor_message)

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


# ── PATCH /api/complaints/<id>/description — resident edits their own report ──

@complaints_bp.route('/<complaint_id>/description', methods=['PATCH'])
@login_required
def edit_complaint_description(complaint_id):
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can edit their own report'}), 403

    complaint = Complaint.query.get_or_404(complaint_id)

    if complaint.resident_id != current_user.resident.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    description = data.get('description', '').strip()

    if not description:
        return jsonify({'error': 'description is required'}), 400

    complaint.description = description
    db.session.commit()

    return jsonify({
        'message':   'Report updated',
        'complaint': complaint_to_dict(complaint),
    }), 200


# ── DELETE /api/complaints/<id> — resident deletes their own report ──
# If this was the only report on the parent issue, the issue itself is
# deleted too — mirrors the cleanup the original mock UI implied
# ("Issue removed — you were the only one reporting it").

@complaints_bp.route('/<complaint_id>', methods=['DELETE'])
@login_required
def delete_complaint(complaint_id):
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can delete their own report'}), 403

    complaint = Complaint.query.get_or_404(complaint_id)

    if complaint.resident_id != current_user.resident.id:
        return jsonify({'error': 'Unauthorized'}), 403

    issue = complaint.issue
    db.session.delete(complaint)
    db.session.flush()

    remaining = Complaint.query.filter_by(issue_id=issue.id).count() if issue else 0
    issue_deleted = False

    if issue and remaining == 0:
        db.session.delete(issue)
        issue_deleted = True

    db.session.commit()

    return jsonify({
        'message':       'Issue removed — you were the only one reporting it' if issue_deleted else 'Your report was removed',
        'issue_deleted': issue_deleted,
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