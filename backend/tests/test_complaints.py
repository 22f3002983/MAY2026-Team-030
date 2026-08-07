def raise_complaint(client, **overrides):
    payload = {
        'title': 'Leaking pipe',
        'description': 'Water leaking near the lift lobby',
        'category': 'plumbing',
        'type': 'common_area',
    }
    payload.update(overrides)
    return client.post('/api/complaints', json=payload)


def add_vendor(client, **overrides):
    payload = {'name': 'Kishore Plumbing', 'phone': '9900011122', 'category': 'plumber'}
    payload.update(overrides)
    return client.post('/api/vendors', json=payload)


def test_resident_can_raise_complaint(resident_client):
    r = raise_complaint(resident_client)
    assert r.status_code == 201
    body = r.get_json()['complaint']
    assert body['status'] == 'open'
    assert body['category'] == 'plumbing'


def test_second_report_same_title_joins_existing_issue(resident_client, resident_client_2):
    c1 = raise_complaint(resident_client).get_json()['complaint']
    r2 = raise_complaint(resident_client_2)  # same title/category as default payload
    assert r2.status_code == 201
    c2 = r2.get_json()['complaint']
    assert c2['issue_id'] == c1['issue_id']
    assert 'existing open issue' in r2.get_json()['message']


def test_invalid_category_rejected(resident_client):
    r = raise_complaint(resident_client, category='not-a-category')
    assert r.status_code == 400


def test_secretary_can_list_all_issues(resident_client, secretary_client):
    raise_complaint(resident_client)
    r = secretary_client.get('/api/complaints')
    assert r.status_code == 200
    body = r.get_json()
    assert body['total'] >= 1
    assert body['complaints'][0]['reporter_count'] >= 1


def test_resident_can_browse_society_issues(resident_client, resident_client_2):
    raise_complaint(resident_client)
    r = resident_client_2.get('/api/complaints?view=society')
    assert r.status_code == 200
    assert r.get_json()['total'] >= 1


def test_secretary_can_assign_vendor(resident_client, secretary_client):
    complaint = raise_complaint(resident_client).get_json()['complaint']
    vendor = add_vendor(secretary_client).get_json()['vendor']

    r = secretary_client.patch(f"/api/complaints/{complaint['id']}/assign", json={'vendor_id': vendor['id']})
    assert r.status_code == 200
    updated = r.get_json()['complaint']
    assert updated['status'] == 'in_progress'
    assert updated['vendor_id'] == vendor['id']


def test_resolve_then_feedback_flow(resident_client, secretary_client):
    complaint = raise_complaint(resident_client).get_json()['complaint']

    # feedback isn't allowed before the issue is resolved
    pre = resident_client.patch(f"/api/complaints/{complaint['id']}/feedback", json={'feedback_rating': 5})
    assert pre.status_code == 400

    r = secretary_client.patch(f"/api/complaints/{complaint['id']}/status", json={'status': 'resolved'})
    assert r.status_code == 200
    assert r.get_json()['complaint']['status'] == 'resolved'

    fb = resident_client.patch(
        f"/api/complaints/{complaint['id']}/feedback",
        json={'feedback_rating': 4, 'feedback_comment': 'Quick fix'},
    )
    assert fb.status_code == 200
    assert fb.get_json()['complaint']['feedback_rating'] == 4


def test_resident_cannot_view_others_complaint(resident_client, resident_client_2):
    complaint = raise_complaint(resident_client).get_json()['complaint']
    r = resident_client_2.get(f"/api/complaints/{complaint['id']}")
    assert r.status_code == 403


def test_resident_can_edit_own_description(resident_client):
    complaint = raise_complaint(resident_client).get_json()['complaint']
    r = resident_client.patch(
        f"/api/complaints/{complaint['id']}/description",
        json={'description': 'Updated description'},
    )
    assert r.status_code == 200
    assert r.get_json()['complaint']['description'] == 'Updated description'


def test_deleting_only_report_removes_the_issue(resident_client):
    complaint = raise_complaint(resident_client).get_json()['complaint']
    r = resident_client.delete(f"/api/complaints/{complaint['id']}")
    assert r.status_code == 200
    assert r.get_json()['issue_deleted'] is True


def test_secretary_can_merge_issues(resident_client, resident_client_2, secretary_client):
    c1 = raise_complaint(resident_client, title='Leaking pipe').get_json()['complaint']
    c2 = raise_complaint(resident_client_2, title='Broken tap').get_json()['complaint']
    assert c1['issue_id'] != c2['issue_id']

    r = secretary_client.post(f"/api/complaints/{c1['issue_id']}/merge", json={'other_issue_id': c2['issue_id']})
    assert r.status_code == 200
    assert r.get_json()['complaint']['reporter_count'] == 2