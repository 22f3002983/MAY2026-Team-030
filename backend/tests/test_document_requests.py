import base64


def request_doc(client, **overrides):
    payload = {'type': 'noc', 'reason': 'Need NOC for bank loan'}
    payload.update(overrides)
    return client.post('/api/document-requests', json=payload)


def test_resident_can_request_document(resident_client):
    r = request_doc(resident_client)
    assert r.status_code == 201
    assert r.get_json()['request']['status'] == 'requested'


def test_invalid_type_rejected(resident_client):
    r = request_doc(resident_client, type='not-a-type')
    assert r.status_code == 400


def test_secretary_upload_marks_ready(resident_client, secretary_client):
    doc = request_doc(resident_client).get_json()['request']
    file_data = base64.b64encode(b'%PDF-1.4 fake pdf content').decode()

    r = secretary_client.patch(f"/api/document-requests/{doc['id']}/upload", json={
        'filename': 'noc.pdf', 'file_data': file_data,
    })
    assert r.status_code == 200
    body = r.get_json()['request']
    assert body['status'] == 'ready'
    assert body['file_url']


def test_invalid_extension_rejected(resident_client, secretary_client):
    doc = request_doc(resident_client).get_json()['request']
    file_data = base64.b64encode(b'not really an exe').decode()

    r = secretary_client.patch(f"/api/document-requests/{doc['id']}/upload", json={
        'filename': 'malware.exe', 'file_data': file_data,
    })
    assert r.status_code == 400


def test_resident_cannot_upload(resident_client):
    doc = request_doc(resident_client).get_json()['request']
    r = resident_client.patch(f"/api/document-requests/{doc['id']}/upload", json={
        'filename': 'noc.pdf', 'file_data': 'abc',
    })
    assert r.status_code == 403


def test_download_blocked_until_delivered(resident_client, secretary_client):
    doc = request_doc(resident_client).get_json()['request']
    file_data = base64.b64encode(b'%PDF-1.4 fake pdf content').decode()
    secretary_client.patch(f"/api/document-requests/{doc['id']}/upload", json={
        'filename': 'noc.pdf', 'file_data': file_data,
    })

    pre = resident_client.get(f"/api/document-requests/{doc['id']}/download")
    assert pre.status_code == 403

    secretary_client.patch(f"/api/document-requests/{doc['id']}/deliver")

    r = resident_client.get(f"/api/document-requests/{doc['id']}/download")
    assert r.status_code == 200


def test_secretary_sees_all_resident_sees_own(resident_client, resident_client_2, secretary_client):
    request_doc(resident_client)
    request_doc(resident_client_2, type='payment_receipt')

    own = resident_client.get('/api/document-requests').get_json()
    assert own['total'] == 1

    all_reqs = secretary_client.get('/api/document-requests').get_json()
    assert all_reqs['total'] == 2