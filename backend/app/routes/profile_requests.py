from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.profile_update import ProfileUpdateRequest
import uuid


profile_requests_bp = Blueprint('profile_requests', __name__)


ALLOWED_FIELDS = {
    'name', 'phone', 'occupant_type', 'household_size',
    'vehicle1_name', 'vehicle1_number', 'vehicle2_name', 'vehicle2_number',
}


def request_to_dict(r):
    resident = r.resident
    return {
        'id':               r.id,
        'resident_id':      r.resident_id,
        'resident_name':    resident.name,
        'flat_id':          resident.flat_id,
        'proposed_changes': r.get_changes(),
        'current_values': {
            'name':             resident.name,
            'phone':            resident.phone,
            'occupant_type':    resident.occupant_type,
            'household_size':   resident.household_size,
            'vehicle1_name':    resident.vehicle1_name,
            'vehicle1_number':  resident.vehicle1_number,
            'vehicle2_name':    resident.vehicle2_name,
            'vehicle2_number':  resident.vehicle2_number,
        },
        'status':      r.status,
        'reviewed_by': r.reviewed_by,
        'created_at':  r.created_at.isoformat() if r.created_at else None,
    }


@profile_requests_bp.route('', methods=['POST'])
@login_required
def create_request():
    if current_user.role != 'resident' or not current_user.resident:
        return jsonify({'error': 'Only residents can submit profile update requests'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    changes = {
        k: v for k, v in data.items()
        if k in ALLOWED_FIELDS and v is not None and str(v).strip() != ''
    }

    if not changes:
        return jsonify({'error': 'No valid fields to update'}), 400

    if 'occupant_type' in changes and changes['occupant_type'] not in ('owner', 'tenant'):
        return jsonify({'error': 'occupant_type must be owner or tenant'}), 400

    if 'household_size' in changes:
        try:
            changes['household_size'] = int(changes['household_size'])
        except (TypeError, ValueError):
            return jsonify({'error': 'household_size must be a number'}), 400

    for field in ('vehicle1_name', 'vehicle2_name'):
        if field in changes and len(str(changes[field])) > 100:
            return jsonify({'error': f'{field} must be 100 characters or fewer'}), 400
    for field in ('vehicle1_number', 'vehicle2_number'):
        if field in changes and len(str(changes[field])) > 20:
            return jsonify({'error': f'{field} must be 20 characters or fewer'}), 400

    resident = current_user.resident

    existing = ProfileUpdateRequest.query.filter_by(resident_id=resident.id, status='pending').first()
    if existing:
        return jsonify({'error': 'You already have a pending profile update request'}), 409

    req = ProfileUpdateRequest(id=str(uuid.uuid4()), resident_id=resident.id, status='pending')
    req.set_changes(changes)

    db.session.add(req)
    db.session.commit()

    return jsonify({
        'message': 'Profile update request submitted',
        'request': request_to_dict(req),
    }), 201


@profile_requests_bp.route('', methods=['GET'])
@login_required
def list_requests():
    status = request.args.get('status')

    if current_user.role == 'secretary':
        query = ProfileUpdateRequest.query
    elif current_user.role == 'resident' and current_user.resident:
        query = ProfileUpdateRequest.query.filter_by(resident_id=current_user.resident.id)
    else:
        return jsonify({'error': 'Not authorized'}), 403

    if status:
        query = query.filter_by(status=status)

    requests_list = query.order_by(ProfileUpdateRequest.created_at.desc()).all()

    return jsonify({
        'requests': [request_to_dict(r) for r in requests_list],
        'total':    len(requests_list),
    }), 200


@profile_requests_bp.route('/<request_id>/approve', methods=['PATCH'])
@login_required
def approve_request(request_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can approve profile update requests'}), 403

    req = ProfileUpdateRequest.query.get_or_404(request_id)

    if req.status != 'pending':
        return jsonify({'error': f'Request is already {req.status}'}), 400

    resident = req.resident
    changes  = req.get_changes()

    if 'name' in changes:
        resident.name = changes['name']
    if 'phone' in changes:
        resident.phone = changes['phone']
    if 'occupant_type' in changes:
        resident.occupant_type = changes['occupant_type']
    if 'household_size' in changes:
        resident.household_size = changes['household_size']
    if 'vehicle1_name' in changes:
        resident.vehicle1_name = changes['vehicle1_name']
    if 'vehicle1_number' in changes:
        resident.vehicle1_number = changes['vehicle1_number']
    if 'vehicle2_name' in changes:
        resident.vehicle2_name = changes['vehicle2_name']
    if 'vehicle2_number' in changes:
        resident.vehicle2_number = changes['vehicle2_number']

    req.status      = 'approved'
    req.reviewed_by = current_user.secretary.id

    db.session.commit()

    return jsonify({
        'message': 'Profile update approved',
        'request': request_to_dict(req),
    }), 200


@profile_requests_bp.route('/<request_id>/reject', methods=['PATCH'])
@login_required
def reject_request(request_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can reject profile update requests'}), 403

    req = ProfileUpdateRequest.query.get_or_404(request_id)

    if req.status != 'pending':
        return jsonify({'error': f'Request is already {req.status}'}), 400

    req.status      = 'rejected'
    req.reviewed_by = current_user.secretary.id

    db.session.commit()

    return jsonify({
        'message': 'Profile update rejected',
        'request': request_to_dict(req),
    }), 200