from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db

profile_bp = Blueprint('profile', __name__)

ALLOWED_FIELDS = {
    'name', 'phone', 'occupant_type', 'household_size',
    'vehicle1_name', 'vehicle1_number', 'vehicle2_name', 'vehicle2_number',
}

@profile_bp.route('', methods=['PATCH'])
@login_required
def update_profile():
    if current_user.role != 'resident' or not current_user.resident:
        return jsonify({'error': 'Only residents can update their profile this way'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    resident = current_user.resident

    for field in ALLOWED_FIELDS:
        if field in data and data[field] is not None:
            setattr(resident, field, data[field])

    db.session.commit()

    return jsonify({'message': 'Profile updated successfully'}), 200