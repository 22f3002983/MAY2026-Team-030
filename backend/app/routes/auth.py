from flask import Blueprint, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.resident import Resident
from app.models.secretary import Secretary
from app.models.security import Security
from datetime import datetime, timedelta
import uuid
import secrets
import string

auth_bp = Blueprint('auth', __name__)

INVITE_CODE_VALIDITY_DAYS = 7


# ── helpers ──────────────────────────────────────────────────────────────────

def generate_invite_code(length=8):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def user_to_dict(user):
    """Return a safe dictionary representation of a user."""
    base = {
        'id':         user.id,
        'email':      user.email,
        'role':       user.role,
        'is_active':  user.is_active,
    }

    if user.role == 'resident' and user.resident:
        base['resident_id']    = user.resident.id
        base['name']           = user.resident.name
        base['flat_id']        = user.resident.flat_id
        base['flat_number']    = user.resident.flat.flat_number if user.resident.flat else None
        base['phone']          = user.resident.phone
        base['occupant_type']  = user.resident.occupant_type
        base['household_size'] = user.resident.household_size
        base['is_onboarded']   = user.resident.is_onboarded
    elif user.role == 'secretary' and user.secretary:
        base['name'] = user.secretary.name
    elif user.role == 'security' and user.security:
        base['name'] = user.security.name

    return base


# ── routes ───────────────────────────────────────────────────────────────────

@auth_bp.route('/ping')
def ping():
    return jsonify({'message': 'auth blueprint working'}), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    Body: { email, password, role, name, phone, flat_id (optional) }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role     = data.get('role', '')
    name     = data.get('name', '').strip()
    phone    = data.get('phone', '').strip()

    # basic validation
    if not email or not password or not role or not name:
        return jsonify({'error': 'email, password, role and name are required'}), 400

    if role not in ('resident', 'secretary', 'security'):
        return jsonify({'error': 'role must be resident, secretary or security'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    # create user
    user = User(id=str(uuid.uuid4()), email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # get user.id before committing

    # create role-specific profile
    if role == 'resident':
        profile = Resident(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=name,
            phone=phone,
            flat_id=data.get('flat_id'),
            occupant_type=data.get('occupant_type', 'owner'),
            household_size=data.get('household_size', 1),
            invite_code=generate_invite_code(),
            invite_code_expiry=datetime.utcnow() + timedelta(days=INVITE_CODE_VALIDITY_DAYS),
        )
        db.session.add(profile)

    elif role == 'secretary':
        profile = Secretary(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=name,
            phone=phone,
        )
        db.session.add(profile)

    elif role == 'security':
        profile = Security(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=name,
            phone=phone,
        )
        db.session.add(profile)

    db.session.commit()

    response = {
        'message': 'User registered successfully',
        'user':    user_to_dict(user),
    }

    if role == 'resident':
        response['invite_code']        = profile.invite_code
        response['invite_code_expiry'] = profile.invite_code_expiry.isoformat()

    return jsonify(response), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login with email and password.
    Body: { email, password }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 403

    login_user(user, remember=True)

    return jsonify({
        'message': 'Login successful',
        'user':    user_to_dict(user),
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout current user and clear session."""
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    """Return current logged in user details."""
    return jsonify({'user': user_to_dict(current_user)}), 200

@auth_bp.route('/residents', methods=['GET'])
@login_required
def list_residents():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can view residents'}), 403

    from app.models.resident import Resident
    residents = Resident.query.all()

    return jsonify({
        'residents': [{
            'id':           r.id,
            'name':         r.name,
            'phone':        r.phone,
            'occupant_type':r.occupant_type,
            'household_size':r.household_size,
            'is_onboarded': r.is_onboarded,
            'invite_code':  r.invite_code,
            'flat_id':      r.flat_id,
        } for r in residents],
        'total': len(residents),
    }), 200


@auth_bp.route('/invite', methods=['POST'])
@login_required
def create_invite():
    """
    Secretary (re)generates an invite code for a resident.
    Body: { resident_id }
    """
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can generate invite codes'}), 403

    data = request.get_json() or {}
    resident_id = data.get('resident_id')

    if not resident_id:
        return jsonify({'error': 'resident_id is required'}), 400

    resident = Resident.query.get(resident_id)
    if not resident:
        return jsonify({'error': 'Resident not found'}), 404

    if resident.is_onboarded:
        return jsonify({'error': 'Resident has already completed onboarding'}), 400

    resident.invite_code = generate_invite_code()
    resident.invite_code_expiry = datetime.utcnow() + timedelta(days=INVITE_CODE_VALIDITY_DAYS)
    db.session.commit()

    return jsonify({
        'invite_code':        resident.invite_code,
        'invite_code_expiry': resident.invite_code_expiry.isoformat(),
    }), 200


@auth_bp.route('/onboard', methods=['POST'])
@login_required
def onboard():
    """
    Resident redeems their invite code and sets a permanent password.
    Body: { invite_code, new_password }
    """
    if current_user.role != 'resident' or not current_user.resident:
        return jsonify({'error': 'Only residents can onboard'}), 403

    resident = current_user.resident

    if resident.is_onboarded:
        return jsonify({'error': 'Account is already onboarded'}), 400

    data = request.get_json() or {}
    invite_code  = data.get('invite_code', '').strip().upper()
    new_password = data.get('new_password', '')

    if not invite_code or not new_password:
        return jsonify({'error': 'invite_code and new_password are required'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    if not resident.invite_code or resident.invite_code != invite_code:
        return jsonify({'error': 'Invalid invite code'}), 400

    if not resident.invite_code_expiry or resident.invite_code_expiry < datetime.utcnow():
        return jsonify({'error': 'Invite code has expired — ask your secretary for a new one'}), 400

    current_user.set_password(new_password)
    resident.is_onboarded = True
    resident.onboarded_at = datetime.utcnow()
    resident.invite_code = None
    resident.invite_code_expiry = None
    db.session.commit()

    return jsonify({
        'message': 'Onboarding complete',
        'user':    user_to_dict(current_user),
    }), 200


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """
    Change the current user's password.
    Body: { current_password, new_password }
    """
    data = request.get_json() or {}
    current_password = data.get('current_password', '')
    new_password      = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({'error': 'current_password and new_password are required'}), 400

    if not current_user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401

    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    current_user.set_password(new_password)
    db.session.commit()

    return jsonify({'message': 'Password updated successfully'}), 200