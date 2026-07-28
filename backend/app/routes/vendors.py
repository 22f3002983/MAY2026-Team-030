from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.vendor import Vendor
import uuid

vendors_bp = Blueprint('vendors', __name__)


# ── helper ────────────────────────────────────────────────────

def vendor_to_dict(v):
    return {
        'id':            v.id,
        'name':          v.name,
        'phone':         v.phone,
        'category':      v.category,
        'description':   v.description,
        'working_hours': v.working_hours,
        'status':        v.status,
        'is_salaried':   bool(v.is_salaried),
        'salary':        float(v.salary) if v.salary is not None else None,
        'created_at':    v.created_at.isoformat() if v.created_at else None,
    }


# ── GET /api/vendors — list all vendors ───────────────────────

@vendors_bp.route('', methods=['GET'])
@login_required
def list_vendors():
    category = request.args.get('category')
    status   = request.args.get('status', 'active')

    query = Vendor.query

    if category:
        query = query.filter_by(category=category)
    if status:
        query = query.filter_by(status=status)

    vendors = query.order_by(Vendor.name).all()

    return jsonify({
        'vendors': [vendor_to_dict(v) for v in vendors],
        'total':   len(vendors),
    }), 200


# ── GET /api/vendors/<id> — get single vendor ─────────────────

@vendors_bp.route('/<vendor_id>', methods=['GET'])
@login_required
def get_vendor(vendor_id):
    vendor = Vendor.query.get_or_404(vendor_id)
    return jsonify({'vendor': vendor_to_dict(vendor)}), 200


# ── POST /api/vendors — add vendor (secretary only) ───────────

@vendors_bp.route('', methods=['POST'])
@login_required
def add_vendor():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can add vendors'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name     = data.get('name', '').strip()
    phone    = data.get('phone', '').strip()
    category = data.get('category', '')

    if not name or not phone or not category:
        return jsonify({'error': 'name, phone and category are required'}), 400

    valid_categories = ('plumber', 'electrician', 'carpenter', 'cleaner', 'other')
    if category not in valid_categories:
        return jsonify({'error': f'category must be one of {valid_categories}'}), 400

    vendor = Vendor(
        id=str(uuid.uuid4()),
        name=name,
        phone=phone,
        category=category,
        description=data.get('description'),
        working_hours=data.get('working_hours'),
        status='active',
        is_salaried=bool(data.get('is_salaried', False)),
        salary=data.get('salary'),
    )

    db.session.add(vendor)
    db.session.commit()

    return jsonify({
        'message': 'Vendor added successfully',
        'vendor':  vendor_to_dict(vendor),
    }), 201


# ── PATCH /api/vendors/<id> — edit vendor (secretary only) ────

@vendors_bp.route('/<vendor_id>', methods=['PATCH'])
@login_required
def edit_vendor(vendor_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can edit vendors'}), 403

    vendor = Vendor.query.get_or_404(vendor_id)
    data   = request.get_json()

    if 'name'          in data: vendor.name          = data['name'].strip()
    if 'phone'         in data: vendor.phone         = data['phone'].strip()
    if 'category'      in data: vendor.category      = data['category']
    if 'description'   in data: vendor.description   = data['description']
    if 'working_hours' in data: vendor.working_hours = data['working_hours']
    if 'status'        in data: vendor.status        = data['status']
    if 'is_salaried'   in data: vendor.is_salaried   = bool(data['is_salaried'])
    if 'salary'        in data: vendor.salary        = data['salary']

    db.session.commit()

    return jsonify({
        'message': 'Vendor updated successfully',
        'vendor':  vendor_to_dict(vendor),
    }), 200

# ── PATCH /api/vendors/<id>/toggle — toggle active/inactive (secretary only) ──

@vendors_bp.route('/<vendor_id>/toggle', methods=['PATCH'])
@login_required
def toggle_vendor_status(vendor_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can toggle vendor status'}), 403

    vendor = Vendor.query.get_or_404(vendor_id)
    vendor.status = 'inactive' if vendor.status == 'active' else 'active'
    db.session.commit()

    return jsonify({
        'message': f'{vendor.name} is now {vendor.status}',
        'vendor':  vendor_to_dict(vendor),
    }), 200
# ── DELETE /api/vendors/<id> — remove vendor (secretary only) ─

@vendors_bp.route('/<vendor_id>', methods=['DELETE'])
@login_required
def delete_vendor(vendor_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can remove vendors'}), 403

    vendor = Vendor.query.get_or_404(vendor_id)
    db.session.delete(vendor)
    db.session.commit()

    return jsonify({'message': f'{vendor.name} removed successfully'}), 200