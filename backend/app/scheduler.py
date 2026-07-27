import atexit
import os
from datetime import datetime, date as date_type
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


def release_expired_bookings(flask_app):
    """Complete approved bookings whose slot has passed and free their amenity."""
    from app.extensions import db
    from app.models.booking import Booking
    from app.models.amenity import Amenity

    with flask_app.app_context():
        today = date_type.today()
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
    scheduler.start()
    print(' * Amenity auto-release scheduler started (every 5 min)', flush=True)

    atexit.register(lambda: scheduler.shutdown(wait=False) if scheduler.running else None)
