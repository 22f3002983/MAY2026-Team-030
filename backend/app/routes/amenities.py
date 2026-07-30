from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.amenity import Amenity
from app.models.booking import Booking
from datetime import datetime, time
import uuid
import json

amenities_bp = Blueprint('amenities', __name__)


# ── helpers ───────────────────────────────────────────────────

def amenity_to_dict(a):
    return {
        'id':                 a.id,
        'name':               a.name,
        'type':               a.type,
        'icon':               a.icon,
        'location':           a.location,
        'description':        a.description,
        'capacity':           a.capacity,
        'is_air_conditioned': a.is_air_conditioned,
        'is_decoratable':     a.is_decoratable,
        'features':           json.loads(a.features) if a.features else [],
        'special_booking':    a.special_booking,
        'booking_type':       a.booking_type,
        'pricing': {
            'type':       a.pricing_type,
            'rate':       float(a.price_rate) if a.price_rate is not None else None,
            'min_units':  a.price_min_units,
            'unit_label': a.price_unit_label,
        },
        'status':       a.status,
        'status_until': a.status_until.isoformat() if a.status_until else None,
    }


def booking_to_dict(b):
    return {
        'id':              b.id,
        'amenity_id':      b.amenity_id,
        'resident_id':     b.resident_id,
        'resident_name':   b.resident.name if b.resident else None,
        'date':            b.date.isoformat() if b.date else None,
        'end_date':        b.end_date.isoformat() if b.end_date else None,
        'start_time':      b.start_time.strftime('%H:%M') if b.start_time else None,
        'end_time':        b.end_time.strftime('%H:%M') if b.end_time else None,
        'reason':          b.reason,
        'status':          b.status,
        'event_type':      b.event_type,
        'guests':          b.guests,
        'price':           float(b.price) if b.price is not None else None,
        'payment_status':  b.payment_status,
        'rejected_reason': b.rejected_reason,
        'created_at':      b.created_at.isoformat() if b.created_at else None,
    }


def parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d').date()


def parse_time(value):
    return datetime.strptime(value, '%H:%M').time()


def find_conflicts(amenity, date, end_date, start_time, end_time):
    """Any pending/approved booking overlapping the given window blocks it —
    pending holds the slot tentatively until a secretary rejects it, same
    as approved. Compared in Python (not SQL) since Booking.end_date is
    nullable for single-day/hourly bookings."""
    candidates = Booking.query.filter(
        Booking.amenity_id == amenity.id,
        Booking.status.in_(['pending', 'approved']),
    ).all()

    conflicts = []
    for b in candidates:
        b_end = b.end_date or b.date
        if b_end < date or b.date > end_date:
            continue
        if amenity.pricing_type == 'hourly' and b.start_time and b.end_time:
            if b.start_time < end_time and b.end_time > start_time:
                conflicts.append(b)
        else:
            conflicts.append(b)
    return conflicts


# ── GET /api/amenities — list all amenities ────────────────────

@amenities_bp.route('', methods=['GET'])
@login_required
def list_amenities():
    amenities = Amenity.query.order_by(Amenity.name).all()
    return jsonify({'amenities': [amenity_to_dict(a) for a in amenities]}), 200


# ── GET /api/amenities/bookings — role-based booking list ──────

@amenities_bp.route('/bookings', methods=['GET'])
@login_required
def list_bookings():
    status = request.args.get('status')

    if current_user.role == 'resident':
        query = Booking.query.filter_by(resident_id=current_user.resident.id)
    elif current_user.role == 'secretary':
        query = Booking.query
    else:
        return jsonify({'error': 'Unauthorized'}), 403

    if status:
        query = query.filter_by(status=status)

    bookings = query.order_by(Booking.date.desc()).all()
    return jsonify({'bookings': [booking_to_dict(b) for b in bookings]}), 200


# ── GET /api/amenities/<id>/availability ────────────────────────

@amenities_bp.route('/<amenity_id>/availability', methods=['GET'])
@login_required
def check_availability(amenity_id):
    amenity = Amenity.query.get_or_404(amenity_id)

    date_str      = request.args.get('date')
    end_date_str  = request.args.get('end_date') or date_str
    start_time_str = request.args.get('start_time')
    end_time_str   = request.args.get('end_time')

    if not date_str:
        return jsonify({'error': 'date is required'}), 400

    date     = parse_date(date_str)
    end_date = parse_date(end_date_str)
    start_time = parse_time(start_time_str) if start_time_str else time(0, 0)
    end_time   = parse_time(end_time_str) if end_time_str else time(23, 59)

    conflicts = find_conflicts(amenity, date, end_date, start_time, end_time)

    if conflicts:
        return jsonify({'available': False, 'message': 'Already booked for part of this window'}), 200
    return jsonify({'available': True, 'message': 'Available for this slot'}), 200


# ── POST /api/amenities/<id>/book — resident books an amenity ──

@amenities_bp.route('/<amenity_id>/book', methods=['POST'])
@login_required
def book_amenity(amenity_id):
    if current_user.role != 'resident':
        return jsonify({'error': 'Only residents can book amenities'}), 403

    amenity = Amenity.query.get_or_404(amenity_id)

    if not amenity.booking_type:
        return jsonify({'error': 'This amenity cannot be booked'}), 400
    if amenity.status != 'available':
        return jsonify({'error': f'Amenity is currently {amenity.status}'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    date_str     = data.get('date')
    end_date_str = data.get('end_date') or date_str
    event_type   = data.get('event_type')
    guests       = data.get('guests')
    reason       = data.get('reason') or event_type

    if not date_str or not event_type or not guests:
        return jsonify({'error': 'date, event_type and guests are required'}), 400

    date     = parse_date(date_str)
    end_date = parse_date(end_date_str)

    if amenity.pricing_type == 'hourly':
        start_time_str = data.get('start_time')
        end_time_str   = data.get('end_time')
        if not start_time_str or not end_time_str:
            return jsonify({'error': 'start_time and end_time are required for hourly amenities'}), 400
        start_time = parse_time(start_time_str)
        end_time   = parse_time(end_time_str)
        if start_time >= end_time:
            return jsonify({'error': 'end_time must be after start_time'}), 400
    else:
        # daily-priced or free amenities book the whole day
        start_time = time(0, 0)
        end_time   = time(23, 59)

    if find_conflicts(amenity, date, end_date, start_time, end_time):
        return jsonify({'error': 'This slot is already booked'}), 409

    units = 1
    if amenity.pricing_type == 'hourly':
        start_dt = datetime.combine(date, start_time)
        end_dt   = datetime.combine(date, end_time)
        units = max(1, round((end_dt - start_dt).seconds / 3600))
    elif amenity.pricing_type == 'daily':
        units = max(1, (end_date - date).days + 1)

    price = float(amenity.price_rate) * max(units, amenity.price_min_units or 1) if amenity.price_rate is not None else None

    status = 'approved' if amenity.booking_type == 'automatic' else 'pending'
    payment_status = 'pending' if (status == 'approved' and price) else None

    booking = Booking(
        id=str(uuid.uuid4()),
        amenity_id=amenity.id,
        resident_id=current_user.resident.id,
        date=date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        reason=reason,
        status=status,
        event_type=event_type,
        guests=guests,
        price=price,
        payment_status=payment_status,
    )
    db.session.add(booking)
    db.session.commit()

    return jsonify({'message': 'Booking created', 'booking': booking_to_dict(booking)}), 201


# ── PATCH /api/amenities/bookings/<id>/cancel ───────────────────

@amenities_bp.route('/bookings/<booking_id>/cancel', methods=['PATCH'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.resident_id != current_user.resident.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if booking.status in ('cancelled', 'rejected', 'completed'):
        return jsonify({'error': f'Booking is already {booking.status}'}), 400

    booking.status = 'cancelled'
    db.session.commit()

    return jsonify({'message': 'Booking cancelled', 'booking': booking_to_dict(booking)}), 200


# ── PATCH /api/amenities/bookings/<id>/pay ──────────────────────

@amenities_bp.route('/bookings/<booking_id>/pay', methods=['PATCH'])
@login_required
def pay_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.resident_id != current_user.resident.id:
        return jsonify({'error': 'Unauthorized'}), 403
    if booking.status != 'approved':
        return jsonify({'error': 'Only approved bookings can be paid for'}), 400
    if booking.payment_status != 'pending':
        return jsonify({'error': 'No payment pending for this booking'}), 400

    booking.payment_status = 'paid'
    db.session.commit()

    return jsonify({'message': 'Payment recorded', 'booking': booking_to_dict(booking)}), 200


# ── GET /api/amenities/<id>/bookings — full history for one amenity (secretary) ──

@amenities_bp.route('/<amenity_id>/bookings', methods=['GET'])
@login_required
def amenity_bookings(amenity_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Unauthorized'}), 403

    bookings = Booking.query.filter_by(amenity_id=amenity_id).order_by(Booking.date.desc()).all()
    return jsonify({'bookings': [booking_to_dict(b) for b in bookings]}), 200


# ── PATCH /api/amenities/bookings/<id>/approve — secretary approves ─────

@amenities_bp.route('/bookings/<booking_id>/approve', methods=['PATCH'])
@login_required
def approve_booking(booking_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can approve bookings'}), 403

    booking = Booking.query.get_or_404(booking_id)
    if booking.status != 'pending':
        return jsonify({'error': f'Booking is {booking.status}, not pending'}), 400

    booking.status = 'approved'
    booking.payment_status = 'pending' if booking.price else None
    db.session.commit()

    return jsonify({'message': 'Booking approved', 'booking': booking_to_dict(booking)}), 200


# ── PATCH /api/amenities/bookings/<id>/reject — secretary rejects ──────

@amenities_bp.route('/bookings/<booking_id>/reject', methods=['PATCH'])
@login_required
def reject_booking(booking_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can reject bookings'}), 403

    booking = Booking.query.get_or_404(booking_id)
    if booking.status != 'pending':
        return jsonify({'error': f'Booking is {booking.status}, not pending'}), 400

    data = request.get_json() or {}
    booking.status = 'rejected'
    booking.rejected_reason = data.get('reason')
    db.session.commit()

    return jsonify({'message': 'Booking rejected', 'booking': booking_to_dict(booking)}), 200


# ── POST /api/amenities — create amenity (secretary) ────────────

@amenities_bp.route('', methods=['POST'])
@login_required
def create_amenity():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can add amenities'}), 403

    data = request.get_json()
    if not data or not data.get('name') or not data.get('type'):
        return jsonify({'error': 'name and type are required'}), 400

    if data['type'] not in ('exclusive', 'public', 'unbookable'):
        return jsonify({'error': "type must be one of ('exclusive', 'public', 'unbookable')"}), 400

    booking_type = data.get('booking_type')
    if booking_type and booking_type not in ('automatic', 'approval_required'):
        return jsonify({'error': "booking_type must be 'automatic', 'approval_required', or null"}), 400

    pricing = data.get('pricing') or {}

    amenity = Amenity(
        id=str(uuid.uuid4()),
        name=data['name'],
        type=data['type'],
        booking_type=booking_type,
        status=data.get('status', 'available'),
        description=data.get('description'),
        icon=data.get('icon'),
        location=data.get('location'),
        capacity=data.get('capacity'),
        is_air_conditioned=data.get('is_air_conditioned', False),
        is_decoratable=data.get('is_decoratable', False),
        features=json.dumps(data.get('features') or []),
        special_booking=data.get('special_booking', False),
        status_until=parse_date(data['status_until']) if data.get('status_until') else None,
        pricing_type=pricing.get('type'),
        price_rate=pricing.get('rate'),
        price_min_units=pricing.get('min_units', 1),
        price_unit_label=pricing.get('unit_label'),
    )
    db.session.add(amenity)
    db.session.commit()

    return jsonify({'message': 'Amenity created', 'amenity': amenity_to_dict(amenity)}), 201


# ── PATCH /api/amenities/<id> — update amenity (secretary) ──────

@amenities_bp.route('/<amenity_id>', methods=['PATCH'])
@login_required
def update_amenity(amenity_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can edit amenities'}), 403

    amenity = Amenity.query.get_or_404(amenity_id)
    data = request.get_json() or {}

    if 'name' in data:               amenity.name = data['name']
    if 'type' in data:               amenity.type = data['type']
    if 'booking_type' in data:       amenity.booking_type = data['booking_type']
    if 'status' in data:             amenity.status = data['status']
    if 'description' in data:        amenity.description = data['description']
    if 'icon' in data:                amenity.icon = data['icon']
    if 'location' in data:           amenity.location = data['location']
    if 'capacity' in data:           amenity.capacity = data['capacity']
    if 'is_air_conditioned' in data: amenity.is_air_conditioned = data['is_air_conditioned']
    if 'is_decoratable' in data:     amenity.is_decoratable = data['is_decoratable']
    if 'features' in data:           amenity.features = json.dumps(data['features'] or [])
    if 'special_booking' in data:    amenity.special_booking = data['special_booking']
    if 'status_until' in data:
        amenity.status_until = parse_date(data['status_until']) if data['status_until'] else None
    if 'pricing' in data:
        pricing = data['pricing'] or {}
        amenity.pricing_type     = pricing.get('type')
        amenity.price_rate       = pricing.get('rate')
        amenity.price_min_units  = pricing.get('min_units', 1)
        amenity.price_unit_label = pricing.get('unit_label')

    db.session.commit()

    return jsonify({'message': 'Amenity updated', 'amenity': amenity_to_dict(amenity)}), 200


# ── DELETE /api/amenities/<id> — delete amenity (secretary) ─────
# Blocked if any pending/approved bookings still exist for it.

@amenities_bp.route('/<amenity_id>', methods=['DELETE'])
@login_required
def delete_amenity(amenity_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can delete amenities'}), 403

    amenity = Amenity.query.get_or_404(amenity_id)

    active = Booking.query.filter(
        Booking.amenity_id == amenity_id,
        Booking.status.in_(['pending', 'approved']),
    ).count()
    if active:
        return jsonify({'error': f'{active} active booking(s) exist for this amenity. Cancel or complete them first.'}), 400

    db.session.delete(amenity)
    db.session.commit()

    return jsonify({'message': 'Amenity deleted'}), 200


# ── PATCH /api/amenities/<id>/status — maintenance toggle (secretary) ──

@amenities_bp.route('/<amenity_id>/status', methods=['PATCH'])
@login_required
def set_amenity_status(amenity_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can change amenity status'}), 403

    amenity = Amenity.query.get_or_404(amenity_id)
    data = request.get_json() or {}
    status = data.get('status')

    if status not in ('available', 'booked', 'closed', 'maintenance', 'inactive'):
        return jsonify({'error': 'invalid status'}), 400

    amenity.status = status
    amenity.status_until = parse_date(data['status_until']) if data.get('status_until') else None
    db.session.commit()

    return jsonify({'message': 'Status updated', 'amenity': amenity_to_dict(amenity)}), 200
