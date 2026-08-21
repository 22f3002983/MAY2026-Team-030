from datetime import date

from app.extensions import db
from app.models.dues import Dues


def _shift_month(base, offset_months):
    year = base.year
    month = base.month + offset_months
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return date(year, month, 1)


def first_of_month(offset_months=0):
    return _shift_month(date.today(), offset_months).isoformat()


def test_secretary_can_generate_dues(resident_client, secretary_client):
    r = secretary_client.post('/api/dues/generate', json={
        'month': first_of_month(0), 'amount_due': 2500,
    })
    assert r.status_code == 201
    body = r.get_json()
    assert body['created'] == 1

    r2 = resident_client.get('/api/dues')
    assert r2.get_json()['total'] == 1
    assert r2.get_json()['dues'][0]['amount_due'] == 2500


def test_generate_blocks_duplicate_month(resident_client, secretary_client):
    # generating dues for a month that's already fully covered for every
    # current resident is now rejected outright, rather than silently
    # creating 0 and reporting a skip count.
    month = first_of_month(0)
    r1 = secretary_client.post('/api/dues/generate', json={'month': month, 'amount_due': 2500})
    assert r1.status_code == 201
    assert r1.get_json()['created'] == 1

    r2 = secretary_client.post('/api/dues/generate', json={'month': month, 'amount_due': 2500})
    assert r2.status_code == 400
    assert 'already been generated' in r2.get_json()['error']


def test_generate_rejects_past_month(secretary_client):
    # dues can only be generated for the current month or later
    r = secretary_client.post('/api/dues/generate', json={
        'month': first_of_month(-2), 'amount_due': 2500,
    })
    assert r.status_code == 400
    assert 'past month' in r.get_json()['error']


def test_mark_paid_sets_paid_status(resident_client, secretary_client):
    secretary_client.post('/api/dues/generate', json={'month': first_of_month(0), 'amount_due': 2500})
    due = resident_client.get('/api/dues').get_json()['dues'][0]

    r = secretary_client.patch(f"/api/dues/{due['id']}/pay", json={'amount_paid': 2500})
    assert r.status_code == 200
    updated = r.get_json()['due']
    assert updated['status'] == 'paid'
    assert updated['amount_paid'] == 2500


def test_unpaid_current_month_is_pending(resident_client, secretary_client):
    secretary_client.post('/api/dues/generate', json={'month': first_of_month(0), 'amount_due': 2500})
    due = resident_client.get('/api/dues').get_json()['dues'][0]
    assert due['status'] == 'pending'


def test_unpaid_past_month_is_overdue(app, resident_client, secretary_client):
    # the /generate endpoint refuses to create dues for a past month, so a
    # due only ever ends up dated in the past by aging there naturally —
    # simulate that by generating a legitimate current-month due and then
    # backdating it directly, the same way an old unpaid due would look.
    secretary_client.post('/api/dues/generate', json={'month': first_of_month(0), 'amount_due': 2500})
    due_id = resident_client.get('/api/dues').get_json()['dues'][0]['id']

    with app.app_context():
        due = Dues.query.get(due_id)
        due.month = _shift_month(date.today(), -2)
        db.session.commit()

    due = resident_client.get('/api/dues').get_json()['dues'][0]
    assert due['status'] == 'overdue'