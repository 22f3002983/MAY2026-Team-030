import atexit
import os
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


def release_expired_bookings(flask_app):
    """Complete approved bookings whose slot has passed and free their amenity."""
    from app.extensions import db
    from app.models.booking import Booking
    from app.models.amenity import Amenity

    with flask_app.app_context():
        today = date.today()
        now_time = datetime.now().time()

        candidates = Booking.query.filter_by(status='approved').filter(
            Booking.date <= today
        ).all()

        changed = False
        for booking in candidates:
            slot_end_date = booking.end_date or booking.date
            if slot_end_date > today:
                continue
            if slot_end_date == today and booking.end_time and booking.end_time >= now_time:
                continue
            booking.status = 'completed'
            amenity = Amenity.query.get(booking.amenity_id)
            if amenity and amenity.status == 'booked':
                amenity.status = 'available'
            changed = True

        if changed:
            db.session.commit()


def auto_generate_next_month_dues(flask_app):
    """Runs daily. If it's the 5th (or later, as a safety net) and next
    month's dues haven't been generated yet, generate them automatically
    using each resident's most recent due amount as the default."""
    from app.extensions import db
    from app.models.dues import Dues
    from app.models.resident import Resident
    from app.routes.notifications import create_notification
    import uuid

    with flask_app.app_context():
        today = date.today()
        if today.day < 5:
            return  # not yet time

        # figure out "next month" the same way generate_dues does
        if today.month == 12:
            target_month = date(today.year + 1, 1, 1)
        else:
            target_month = date(today.year, today.month + 1, 1)

        residents = Resident.query.all()
        if not residents:
            return

        already_generated_count = Dues.query.filter_by(month=target_month).count()
        if already_generated_count >= len(residents):
            return  # secretary already did it manually

        created = 0
        for resident in residents:
            existing = Dues.query.filter_by(resident_id=resident.id, month=target_month).first()
            if existing:
                continue

            # use their most recent due amount as the default going forward
            last_due = Dues.query.filter_by(resident_id=resident.id).order_by(Dues.month.desc()).first()
            amount = float(last_due.amount_due) if last_due else 2500

            due = Dues(
                id=str(uuid.uuid4()),
                resident_id=resident.id,
                month=target_month,
                amount_due=amount,
                amount_paid=0,
            )
            db.session.add(due)
            created += 1

            # in-app only, same wording as the manual reminder/generate
            # endpoints — queued on the same session, commits atomically
            create_notification(
                user_id=resident.user_id,
                message=f'Maintenance dues reminder: ₹{amount:.2f} is due for {target_month.strftime("%B %Y")}',
                type='dues_reminder',
            )

        if created:
            db.session.commit()
            print(f' * Auto-generated dues for {created} residents — {target_month.strftime("%B %Y")}', flush=True)


def mark_expired_visitors(flask_app):
    """Runs every 5 minutes. The API already computes a visitor pass's
    expiry live from expires_at for every response (see _is_timed_out in
    routes/visitors.py), so nothing in the app's behavior depends on this —
    but the stored is_expired column itself was never being flipped, so
    anyone querying niwaas.db directly (or another tool reading the raw
    table) saw every pass as not-expired forever. This just keeps that
    column honest. Only ever flips it True; a pass that's expired stays
    expired, so there's nothing to walk back."""
    from app.extensions import db
    from app.models.visitor import Visitor

    with flask_app.app_context():
        now = datetime.utcnow()
        expired = Visitor.query.filter(
            Visitor.is_expired.is_(False),
            Visitor.expires_at.isnot(None),
            Visitor.expires_at < now,
        ).all()

        if not expired:
            return

        for visitor in expired:
            visitor.is_expired = True

        db.session.commit()
        print(f' * Marked {len(expired)} visitor pass(es) as expired', flush=True)


def retry_pending_ai_suggestions(flask_app):
    """Runs every 5 minutes. AI category/priority are normally set once, in a
    background thread, right when a complaint is created (see
    _run_ai_suggestions in routes/complaints.py) — but that's a single
    best-effort attempt with no retry of its own, so a transient failure
    (rate limit, timeout, momentary API hiccup) leaves ai_suggested_category
    / ai_suggested_priority permanently None with nothing to revisit them.

    This only ever looks at issues where a field is still None — it never
    re-queries or overwrites one that already has a value, so a working
    suggestion is never touched twice and this costs nothing beyond the
    complaints that are actually stuck. Only open/in_progress issues are
    retried; resolved/closed ones aren't worth spending an API call on."""
    from app.extensions import db
    from app.models.community_issue import CommunityIssue
    from app.routes.complaints import VALID_CATEGORIES
    from app.services.ai_category import suggest_category
    from app.services.ai_priority import suggest_priority

    with flask_app.app_context():
        stuck = CommunityIssue.query.filter(
            CommunityIssue.status.in_(['open', 'in_progress']),
            db.or_(
                CommunityIssue.ai_suggested_category.is_(None),
                CommunityIssue.ai_suggested_priority.is_(None),
            ),
        ).limit(20).all()  # capped per run so a bad backlog can't burst-call the API

        if not stuck:
            return

        retried = 0
        for issue in stuck:
            text = f'{issue.title}. {issue.description}'
            if issue.ai_suggested_category is None:
                issue.ai_suggested_category = suggest_category(text, VALID_CATEGORIES)
            if issue.ai_suggested_priority is None:
                issue.ai_suggested_priority = suggest_priority(issue.title, issue.description, issue.category)
            retried += 1

        db.session.commit()
        print(f' * Retried AI suggestions for {retried} stuck issue(s)', flush=True)


def start_scheduler(flask_app):
    """Start the background scheduler once per running process.

    Guards against Werkzeug's debug-mode reloader, which forks a watcher
    process in addition to the process that actually serves requests —
    without this check the job would run twice, every 5 minutes, in
    parallel processes.
    """
    if flask_app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return

    if scheduler.running:
        return

    scheduler.add_job(
        func=lambda: release_expired_bookings(flask_app),
        trigger='interval',
        minutes=5,
        id='release_expired_bookings',
        replace_existing=True,
    )

    scheduler.add_job(
        func=lambda: auto_generate_next_month_dues(flask_app),
        trigger='cron',
        hour=1,
        minute=0,
        id='auto_generate_next_month_dues',
        replace_existing=True,
    )

    scheduler.add_job(
        func=lambda: mark_expired_visitors(flask_app),
        trigger='interval',
        minutes=5,
        id='mark_expired_visitors',
        replace_existing=True,
    )

    scheduler.add_job(
        func=lambda: retry_pending_ai_suggestions(flask_app),
        trigger='interval',
        minutes=5,
        id='retry_pending_ai_suggestions',
        replace_existing=True,
    )

    scheduler.start()
    print(' * Amenity auto-release scheduler started (every 5 min)', flush=True)
    print(' * Dues auto-generation scheduler started (daily, checks from the 5th)', flush=True)
    print(' * Visitor pass expiry scheduler started (every 5 min)', flush=True)
    print(' * Stuck AI suggestion retry scheduler started (every 5 min)', flush=True)

    atexit.register(lambda: scheduler.shutdown(wait=False) if scheduler.running else None)