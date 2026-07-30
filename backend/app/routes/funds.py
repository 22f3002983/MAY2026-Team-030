from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.fund import FundConfig, SocietyFund, FundTransaction
import uuid
from datetime import datetime

funds_bp = Blueprint('funds', __name__)

DEFAULT_CONFIG = (
    ('operating',    70),
    ('sinking',      20),
    ('contingency',  10),
)


# ── helpers ───────────────────────────────────────────────────

def config_to_dict(c):
    return {
        'id':          c.id,
        'fund_name':   c.fund_name,
        'percentage':  float(c.percentage),
        'is_active':   c.is_active,
        'updated_at':  c.updated_at.isoformat() if c.updated_at else None,
    }

def fund_to_dict(f):
    return {
        'id':         f.id,
        'fund_name':  f.fund_name,
        'balance':    float(f.balance),
        'updated_at': f.updated_at.isoformat() if f.updated_at else None,
    }

def txn_to_dict(t):
    return {
        'id':           t.id,
        'fund_name':    t.fund_name,
        'type':         t.type,
        'amount':       float(t.amount),
        'source':       t.source,
        'reference_id': t.reference_id,
        'description':  t.description,
        'created_by':   t.created_by,
        'created_at':   t.created_at.isoformat() + 'Z' if t.created_at else None,
    }


def ensure_default_config():
    """Seed any missing default fund rows — checked per fund name so it's
    safe to call repeatedly, even under concurrent requests, without ever
    trying to insert a fund that already exists."""
    added = False
    for fund_name, pct in DEFAULT_CONFIG:
        existing = FundConfig.query.filter_by(fund_name=fund_name).first()
        if existing:
            continue
        db.session.add(FundConfig(id=str(uuid.uuid4()), fund_name=fund_name, percentage=pct))
        added = True
    if added:
        db.session.commit()


def get_or_create_fund(fund_name):
    fund = SocietyFund.query.filter_by(fund_name=fund_name).first()
    if not fund:
        fund = SocietyFund(id=str(uuid.uuid4()), fund_name=fund_name, balance=0)
        db.session.add(fund)
    return fund


def distribute_payment(amount, source, reference_id=None, description=None, created_by=None):
    """Split an incoming society payment (dues, amenity booking fee, or a
    manual credit entry) across active funds per their configured
    percentage, crediting each fund's balance and recording a ledger entry.
    Call this from wherever a resident payment actually reaches the society
    (not vendor-direct payments like Home Services, which never touch
    society funds), and also from the manual-credit path in
    create_transaction below."""
    ensure_default_config()
    amount = float(amount)
    if amount <= 0:
        return

    active_configs = FundConfig.query.filter_by(is_active=True).all()
    if not active_configs:
        return

    for cfg in active_configs:
        share = round(amount * float(cfg.percentage) / 100, 2)
        if share <= 0:
            continue
        fund = get_or_create_fund(cfg.fund_name)
        fund.balance = float(fund.balance or 0) + share

        db.session.add(FundTransaction(
            id=str(uuid.uuid4()),
            fund_name=cfg.fund_name,
            type='credit',
            amount=share,
            source=source,
            reference_id=reference_id,
            description=description,
            created_by=created_by,
        ))

    db.session.commit()


# ── GET /api/funds — list fund balances (secretary only) ─────

@funds_bp.route('', methods=['GET'])
@login_required
def list_funds():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can view society funds'}), 403

    ensure_default_config()
    for fund_name, _ in DEFAULT_CONFIG:
        get_or_create_fund(fund_name)
    db.session.commit()

    funds = SocietyFund.query.order_by(SocietyFund.fund_name).all()
    return jsonify({
        'funds': [fund_to_dict(f) for f in funds],
        'total_balance': sum(float(f.balance) for f in funds),
    }), 200


# ── GET /api/funds/config — list the split configuration ─────

@funds_bp.route('/config', methods=['GET'])
@login_required
def list_config():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can view fund configuration'}), 403

    ensure_default_config()
    configs = FundConfig.query.order_by(FundConfig.fund_name).all()
    return jsonify({'config': [config_to_dict(c) for c in configs]}), 200


# ── PATCH /api/funds/config/<id> — edit a fund's split percentage ────

@funds_bp.route('/config/<config_id>', methods=['PATCH'])
@login_required
def update_config(config_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can edit fund configuration'}), 403

    cfg  = FundConfig.query.get_or_404(config_id)
    data = request.get_json() or {}

    new_pct = data.get('percentage', float(cfg.percentage))
    is_active = data.get('is_active', cfg.is_active)

    try:
        new_pct = float(new_pct)
    except (TypeError, ValueError):
        return jsonify({'error': 'percentage must be a number'}), 400
    if new_pct < 0 or new_pct > 100:
        return jsonify({'error': 'percentage must be between 0 and 100'}), 400

    # validate the total across all active funds (with this edit applied) is 100
    others_total = sum(
        float(c.percentage) for c in
        FundConfig.query.filter(FundConfig.id != config_id, FundConfig.is_active.is_(True)).all()
    )
    projected_total = others_total + (new_pct if is_active else 0)
    if is_active and round(projected_total, 2) != 100:
        return jsonify({'error': f'Active fund percentages must sum to 100 (would be {projected_total})'}), 400

    cfg.percentage = new_pct
    cfg.is_active  = is_active
    db.session.commit()

    return jsonify({
        'message': 'Fund configuration updated',
        'config':  config_to_dict(cfg),
    }), 200


# ── GET /api/funds/transactions — ledger (secretary only) ────

@funds_bp.route('/transactions', methods=['GET'])
@login_required
def list_transactions():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can view fund transactions'}), 403

    fund_name = request.args.get('fund_name')
    query = FundTransaction.query
    if fund_name:
        query = query.filter_by(fund_name=fund_name)

    txns = query.order_by(FundTransaction.created_at.desc()).all()
    return jsonify({
        'transactions': [txn_to_dict(t) for t in txns],
        'total': len(txns),
    }), 200


# ── POST /api/funds/transactions — manual entry (secretary only) ─────
#
# CREDIT: always split across active funds per FundConfig — the secretary
#         cannot direct a credit to one specific fund, since incoming money
#         is never "for" a single fund category.
#
# DEBIT: a specific fund must be chosen. Operating is the default and
#        preferred source — another fund can only be selected once
#        operating's balance is fully at zero.

@funds_bp.route('/transactions', methods=['POST'])
@login_required
def create_transaction():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can record fund transactions'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    txn_type    = data.get('type', '')
    amount      = data.get('amount')
    description = data.get('description', '').strip()

    if txn_type not in ('credit', 'debit') or amount is None or not description:
        return jsonify({'error': 'type (credit/debit), amount and description are required'}), 400

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({'error': 'amount must be a number'}), 400
    if amount <= 0:
        return jsonify({'error': 'amount must be greater than 0'}), 400

    # ── CREDIT ─────────────────────────────────────────────────────────
    if txn_type == 'credit':
        distribute_payment(
            amount,
            source='manual',
            description=description,
            created_by=current_user.secretary.id,
        )
        funds = SocietyFund.query.order_by(SocietyFund.fund_name).all()
        return jsonify({
            'message': 'Credit split across active funds',
            'funds': [fund_to_dict(f) for f in funds],
        }), 201

    # ── DEBIT ──────────────────────────────────────────────────────────
    fund_name = data.get('fund_name', '').strip()
    if not fund_name:
        return jsonify({'error': 'fund_name is required for a debit'}), 400

    ensure_default_config()
    operating_fund = get_or_create_fund('operating')

    if fund_name != 'operating' and float(operating_fund.balance) >= amount:
        return jsonify({
            'error': f'Operating fund has enough balance (₹{operating_fund.balance}) to cover this ₹{amount} payment — debit from operating instead.'
                     f'Other funds become selectable once operating is empty.'
        }), 400

    fund = get_or_create_fund(fund_name)
    if float(fund.balance) < amount:
        return jsonify({'error': f'Insufficient balance in {fund_name} fund (₹{fund.balance} available)'}), 400

    fund.balance = float(fund.balance) - amount

    txn = FundTransaction(
        id=str(uuid.uuid4()),
        fund_name=fund_name,
        type='debit',
        amount=amount,
        source='manual',
        description=description,
        created_by=current_user.secretary.id,
    )
    db.session.add(txn)
    db.session.commit()

    return jsonify({
        'message': 'Transaction recorded',
        'transaction': txn_to_dict(txn),
        'fund': fund_to_dict(fund),
    }), 201


# ── PATCH /api/funds/config — bulk update all splits at once ─────

@funds_bp.route('/config', methods=['PATCH'])
@login_required
def update_config_bulk():
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can edit fund configuration'}), 403

    data = request.get_json()
    if not data or 'configs' not in data:
        return jsonify({'error': 'configs (list) is required'}), 400

    updates = data['configs']  # [{ id, percentage, is_active }, ...]

    configs = {}
    for u in updates:
        cfg = FundConfig.query.get(u.get('id'))
        if not cfg:
            return jsonify({'error': f"Config {u.get('id')} not found"}), 404
        try:
            pct = float(u.get('percentage', cfg.percentage))
        except (TypeError, ValueError):
            return jsonify({'error': 'percentage must be a number'}), 400
        if pct < 0 or pct > 100:
            return jsonify({'error': 'percentage must be between 0 and 100'}), 400
        configs[cfg.id] = {
            'cfg': cfg,
            'percentage': pct,
            'is_active': u.get('is_active', cfg.is_active),
        }

    # validate the FULL resulting set of active percentages sums to 100
    all_configs = FundConfig.query.all()
    total = 0
    for c in all_configs:
        if c.id in configs:
            entry = configs[c.id]
            if entry['is_active']:
                total += entry['percentage']
        elif c.is_active:
            total += float(c.percentage)

    if round(total, 2) != 100:
        return jsonify({'error': f'Active fund percentages must sum to 100 (would be {total})'}), 400

    for entry in configs.values():
        entry['cfg'].percentage = entry['percentage']
        entry['cfg'].is_active  = entry['is_active']

    db.session.commit()

    return jsonify({
        'message': 'Fund configuration updated',
        'config':  [config_to_dict(c) for c in FundConfig.query.order_by(FundConfig.fund_name).all()],
    }), 200