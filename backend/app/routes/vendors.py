from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.vendor import Vendor
from app.routes.funds import debit_fund, build_fallback_plan, FALLBACK_FUND_ORDER
from datetime import datetime
import uuid

vendors_bp = Blueprint('vendors', __name__)

# Vendor category is the *profession* — kept distinct from a community
# issue's category (the *problem type*, see complaints.py VALID_CATEGORIES).
# This list is fixed by the DB model's Enum('vendor_categories') column —
# SQLAlchemy validates every value read back from the DB against this exact
# list (LookupError otherwise), so it can't be widened without a model
# change. Issue categories with no matching profession (security,
# gardening, pest_control) are mapped to 'other' at the frontend instead
# — see ISSUE_TO_VENDOR_CATEGORY in SecComplaintsView.vue.
VALID_VENDOR_CATEGORIES = ('plumber', 'electrician', 'carpenter', 'cleaner', 'other')


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

    if category not in VALID_VENDOR_CATEGORIES:
        return jsonify({'error': f'category must be one of {VALID_VENDOR_CATEGORIES}'}), 400

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
    if 'category'      in data:
        if data['category'] not in VALID_VENDOR_CATEGORIES:
            return jsonify({'error': f'category must be one of {VALID_VENDOR_CATEGORIES}'}), 400
        vendor.category = data['category']
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


# ── shared validation for the salary-payment endpoints ────────

def _validate_salary_vendors(vendor_ids):
    """Returns (vendors, error_response). error_response is None on success."""
    if not vendor_ids or not isinstance(vendor_ids, list):
        return None, (jsonify({'error': 'vendor_ids (list) is required'}), 400)

    vendors = []
    for vendor_id in vendor_ids:
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return None, (jsonify({'error': f'Vendor {vendor_id} not found'}), 404)
        if not vendor.is_salaried or not vendor.salary:
            return None, (jsonify({'error': f'{vendor.name} is not a salaried vendor'}), 400)
        if vendor.status != 'active':
            return None, (jsonify({'error': f'{vendor.name} is inactive'}), 400)
        vendors.append(vendor)
    return vendors, None


# ── POST /api/vendors/pay-salaries/preview — dry-run the payment (secretary only) ──
#
# Shows exactly which fund(s) the payment will come from before the
# secretary commits to it: operating first, then contingency, then sinking
# if the first two together still aren't enough. Nothing is written to the
# DB here.

@vendors_bp.route('/pay-salaries/preview', methods=['POST'])
@login_required
def preview_pay_salaries():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can pay vendor salaries'}), 403

    data = request.get_json() or {}
    vendors, err = _validate_salary_vendors(data.get('vendor_ids'))
    if err:
        return err

    items = [(v.id, float(v.salary)) for v in vendors]
    allocations, fund_summary, shortfall = build_fallback_plan(items)
    total = sum(a for _, a in items)

    return jsonify({
        'vendors':    [{'id': v.id, 'name': v.name, 'salary': float(v.salary)} for v in vendors],
        'total':      total,
        'funds':      fund_summary,
        'shortfall':  shortfall,
        'sufficient': shortfall <= 0,
    }), 200


# ── POST /api/vendors/pay-salaries — pay one or more salaried vendors (secretary only) ──
#
# Recomputes the same fallback plan the preview showed and executes it:
# draws from operating first, then contingency, then sinking if needed,
# splitting a single vendor's salary across funds if a fund runs out
# mid-payment. Every draw is written to the funds ledger (source=
# 'vendor_salary', reference_id=vendor.id) so it shows up in the funds
# transaction history and actually reduces the real balance.

@vendors_bp.route('/pay-salaries', methods=['POST'])
@login_required
def pay_salaries():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can pay vendor salaries'}), 403

    data = request.get_json() or {}
    vendors, err = _validate_salary_vendors(data.get('vendor_ids'))
    if err:
        return err

    vendors_by_id = {v.id: v for v in vendors}
    items = [(v.id, float(v.salary)) for v in vendors]
    allocations, fund_summary, shortfall = build_fallback_plan(items)

    if shortfall > 0:
        covered = sum(a['amount'] for a in allocations)
        return jsonify({
            'error': (
                f"{', '.join(f.title() for f in FALLBACK_FUND_ORDER)} funds together only cover "
                f'₹{covered:,.2f} of the ₹{covered + shortfall:,.2f} needed — short by ₹{shortfall:,.2f}.'
            ),
            'funds':     fund_summary,
            'shortfall': shortfall,
        }), 400

    month_label = datetime.utcnow().strftime('%b %Y')
    for alloc in allocations:
        vendor = vendors_by_id[alloc['label']]
        debit_fund(
            alloc['fund_name'],
            alloc['amount'],
            source='vendor_salary',
            reference_id=vendor.id,
            description=f"Salary payment — {vendor.name} ({month_label})",
            created_by=current_user.secretary.id,
        )

    db.session.commit()

    total = sum(float(v.salary) for v in vendors)
    return jsonify({
        'message':    f'Paid {len(vendors)} vendor(s) · ₹{total} total',
        'paid_count': len(vendors),
        'total_paid': total,
        'funds':      fund_summary,
    }), 201