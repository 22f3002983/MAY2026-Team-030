from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.flat import Flat

flats_bp = Blueprint('flats', __name__)


@flats_bp.route('/directory', methods=['GET'])
@login_required
def flat_directory():
    """
    Flat -> primary resident lookup, used by security to raise a gate
    request against a real resident_id (and by secretary if ever needed).

    A flat can have multiple residents (household_size > 1), but every
    visitor/approval flow in this app is tied to a single resident_id,
    so we surface one primary contact per flat here — preferring an
    onboarded resident, falling back to whichever resident record exists.
    Flats with no resident on record are left out, since there's no one
    to send a gate request to.
    """
    if current_user.role not in ('secretary', 'security'):
        return jsonify({'error': 'Unauthorized'}), 403

    flats = Flat.query.order_by(Flat.flat_number).all()

    result = []
    for f in flats:
        primary = next((r for r in f.residents if r.is_onboarded), None) \
                  or (f.residents[0] if f.residents else None)

        if not primary:
            continue  # nobody to route a gate request to

        result.append({
            'flat_id':       f.id,
            'flat_number':   f.flat_number,
            'tower':         f.tower,
            'floor':         f.floor,
            'status':        f.status,
            'resident_id':   primary.id,
            'resident_name': primary.name,
        })

    return jsonify({'flats': result, 'total': len(result)}), 200


@flats_bp.route('/blocks', methods=['GET'])
@login_required
def list_blocks():
    """Unique tower/block values from the flats table, used to populate
    the notice 'relevance' options so stored values always match what
    residents are filtered against (resident.flat.tower)."""
    if current_user.role not in ('secretary', 'security', 'resident'):
        return jsonify({'error': 'Unauthorized'}), 403

    rows = (
        db.session.query(Flat.tower)
        .distinct()
        .order_by(Flat.tower)
        .all()
    )
    blocks = [r[0] for r in rows if r[0]]

    return jsonify({'blocks': blocks}), 200