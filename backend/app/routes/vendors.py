from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.vendor import Vendor
from app.models.fund import FundTransaction
from app.routes.funds import debit_fund, build_fallback_plan, FALLBACK_FUND_ORDER
from datetime import datetime
import uuid

vendors_bp = Blueprint('vendors', __name__)

# Vendor category is the *profession* — kept distinct from a community
# issue's category (the *problem type*, see complaints.py VALID_CATEGORIES).
# This list is fixed by the DB model's Enum('vendor_categories') column —
# SQLAlchemy validates every value read back from the DB against this exact
# list (LookupError otherwise), so it can't be widened without a model
# change.
# Vendor category now matches CommunityIssue.category exactly (see
# app/models/community_issue.py) — same 8 values, same spellings — so a
# vendor's category can be compared directly against an issue's category
# with no translation layer needed. Previously this used profession words
# ('plumber', 'electrician', ...) which didn't line up 1:1 with issue
# categories ('plumbing', 'electrical', ...) and had no category at all
# for security/gardening/pest_control — this migration (see
# migrate_vendor_categories.py) backfills existing rows to the new values.
VALID_VENDOR_CATEGORIES = ('plumbing', 'electrical', 'cleaning', 'carpentry', 'security', 'gardening', 'pest_control', 'other')


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
    if not data:
        return jsonify({'error': 'No data provided'}), 400

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

    # SQLite (this app's default DB) doesn't enforce the vendor_id foreign
    # keys on service_requests/community_issues by default, so deleting a
    # vendor with existing history wouldn't fail loudly — it would silently
    # orphan those rows' vendor_id, and later code that does sr.vendor.name
    # (complete_request, rate_request) or issue.vendor.name would crash with
    # an AttributeError instead. Block the delete up front and point the
    # secretary at deactivating instead, which is reversible and keeps
    # history intact.
    from app.models.service_request import ServiceRequest
    from app.models.community_issue import CommunityIssue

    has_service_requests = ServiceRequest.query.filter_by(vendor_id=vendor.id).first() is not None
    has_assigned_issues = CommunityIssue.query.filter_by(vendor_id=vendor.id).first() is not None
    if has_service_requests or has_assigned_issues:
        return jsonify({
            'error': f'{vendor.name} has existing service requests or assigned complaints and cannot be deleted. '
                     f'Mark them inactive instead.',
        }), 400

    db.session.delete(vendor)
    db.session.commit()

    return jsonify({'message': f'{vendor.name} removed successfully'}), 200


def _already_paid_vendor_ids_this_month(vendor_ids):
    """Vendor IDs among vendor_ids that already have a vendor_salary debit
    recorded this calendar month — used to auto-skip them from a payment
    run instead of letting the secretary accidentally double-pay someone
    (nothing previously stopped the same vendor being paid any number of
    times in a month)."""
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    rows = (
        FundTransaction.query
        .filter(
            FundTransaction.source == 'vendor_salary',
            FundTransaction.reference_id.in_(vendor_ids),
            FundTransaction.created_at >= month_start,
        )
        .with_entities(FundTransaction.reference_id)
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


# ── shared validation for the salary-payment endpoints ────────

def _validate_salary_vendors(vendor_ids):
    """Returns (vendors, already_paid_names, error_response). Vendors already
    paid this month are silently excluded from `vendors` rather than
    rejecting the whole batch — same "top up what's missing" pattern
    generate_dues() already uses elsewhere in this codebase — so paying
    everyone at once just skips whoever's already been paid instead of
    erroring out. error_response is None on success."""
    if not vendor_ids or not isinstance(vendor_ids, list):
        return None, None, (jsonify({'error': 'vendor_ids (list) is required'}), 400)

    candidates = []
    for vendor_id in vendor_ids:
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return None, None, (jsonify({'error': f'Vendor {vendor_id} not found'}), 404)
        if not vendor.is_salaried or not vendor.salary:
            return None, None, (jsonify({'error': f'{vendor.name} is not a salaried vendor'}), 400)
        if vendor.status != 'active':
            return None, None, (jsonify({'error': f'{vendor.name} is inactive'}), 400)
        candidates.append(vendor)

    already_paid_ids = _already_paid_vendor_ids_this_month([v.id for v in candidates])
    vendors = [v for v in candidates if v.id not in already_paid_ids]
    already_paid_names = [v.name for v in candidates if v.id in already_paid_ids]

    return vendors, already_paid_names, None


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
    vendors, already_paid_names, err = _validate_salary_vendors(data.get('vendor_ids'))
    if err:
        return err
    if not vendors:
        return jsonify({
            'error': f"Already paid this month: {', '.join(already_paid_names)}. Nothing left to preview.",
            'already_paid': already_paid_names,
        }), 400

    items = [(v.id, float(v.salary)) for v in vendors]
    allocations, fund_summary, shortfall = build_fallback_plan(items)
    total = sum(a for _, a in items)

    return jsonify({
        'vendors':          [{'id': v.id, 'name': v.name, 'salary': float(v.salary)} for v in vendors],
        'already_paid':     already_paid_names,
        'total':            total,
        'funds':            fund_summary,
        'shortfall':        shortfall,
        'sufficient':       shortfall <= 0,
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
    vendors, already_paid_names, err = _validate_salary_vendors(data.get('vendor_ids'))
    if err:
        return err
    if not vendors:
        return jsonify({
            'error': f"Already paid this month: {', '.join(already_paid_names)}. Nothing left to pay.",
            'already_paid': already_paid_names,
        }), 400

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
    message = f'Paid {len(vendors)} vendor(s) · ₹{total} total'
    if already_paid_names:
        message += f" — skipped {len(already_paid_names)} already paid this month ({', '.join(already_paid_names)})"

    return jsonify({
        'message':      message,
        'paid_count':   len(vendors),
        'total_paid':   total,
        'already_paid': already_paid_names,
        'funds':        fund_summary,
    }), 201