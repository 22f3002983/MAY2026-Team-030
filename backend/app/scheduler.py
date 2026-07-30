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

        if created:
            db.session.commit()
            print(f' * Auto-generated dues for {created} residents — {target_month.strftime("%B %Y")}', flush=True)


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

    scheduler.start()
    print(' * Amenity auto-release scheduler started (every 5 min)', flush=True)
    print(' * Dues auto-generation scheduler started (daily, checks from the 5th)', flush=True)

    atexit.register(lambda: scheduler.shutdown(wait=False) if scheduler.running else None)