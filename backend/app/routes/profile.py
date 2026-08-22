from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
import re

profile_bp = Blueprint('profile', __name__)

ALLOWED_FIELDS = {
    'name', 'phone', 'occupant_type', 'household_size',
    'vehicle1_name', 'vehicle1_number', 'vehicle2_name', 'vehicle2_number',
}

VALID_OCCUPANT_TYPES = ('owner', 'tenant')

# Matches what the frontend's utils/phone.js toStoredPhone() sends
# ('+91' + 10 digits), but tolerant of a bare 10-digit number too —
# either way, always at least 10 digits.
PHONE_RE = re.compile(r'^\+?\d{10,15}$')


def _validate_profile_fields(data):
    """Returns an error message string, or None if everything checks out."""
    if 'name' in data:
        name = data['name']
        if not isinstance(name, str) or not name.strip():
            return 'name cannot be empty'
        if len(name.strip()) > 100:
            return 'name is too long (max 100 characters)'

    if 'phone' in data:
        phone = data['phone']
        if not isinstance(phone, str) or not PHONE_RE.match(phone.strip()):
            return 'Enter a valid phone number'

    if 'occupant_type' in data and data['occupant_type'] not in VALID_OCCUPANT_TYPES:
        return f'occupant_type must be one of {VALID_OCCUPANT_TYPES}'

    if 'household_size' in data:
        size = data['household_size']
        try:
            size = int(size)
        except (TypeError, ValueError):
            return 'household_size must be a number'
        if size < 1 or size > 20:
            return 'household_size must be between 1 and 20'

    for field in ('vehicle1_name', 'vehicle2_name'):
        if field in data and data[field] and len(str(data[field])) > 100:
            return f'{field} is too long (max 100 characters)'

    for field in ('vehicle1_number', 'vehicle2_number'):
        if field in data and data[field] and len(str(data[field])) > 20:
            return f'{field} is too long (max 20 characters)'

    return None


@profile_bp.route('', methods=['PATCH'])
@login_required
def update_profile():
    if current_user.role != 'resident' or not current_user.resident:
        return jsonify({'error': 'Only residents can update their profile this way'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    error = _validate_profile_fields(data)
    if error:
        return jsonify({'error': error}), 400

    resident = current_user.resident

    for field in ALLOWED_FIELDS:
        if field in data and data[field] is not None:
            value = data[field]
            if isinstance(value, str):
                value = value.strip()
            if field == 'household_size':
                value = int(value)
            setattr(resident, field, value)

    db.session.commit()

    return jsonify({'message': 'Profile updated successfully'}), 200