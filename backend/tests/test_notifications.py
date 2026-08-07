import base64


def _create_notification_for_resident(resident_client, secretary_client):
    """No direct 'create notification' endpoint exists — reuse the
    document-request upload flow, which notifies the requesting resident,
    to get a real notification row into the system."""
    doc = resident_client.post('/api/document-requests', json={
        'type': 'noc', 'reason': 'Need NOC',
    }).get_json()['request']

    file_data = base64.b64encode(b'%PDF-1.4 fake pdf content').decode()
    secretary_client.patch(f"/api/document-requests/{doc['id']}/upload", json={
        'filename': 'noc.pdf', 'file_data': file_data,
    })


def test_list_notifications(resident_client, secretary_client):
    _create_notification_for_resident(resident_client, secretary_client)

    r = resident_client.get('/api/notifications')
    assert r.status_code == 200
    body = r.get_json()
    assert body['total'] == 1
    assert body['notifications'][0]['is_read'] is False


def test_unread_count(resident_client, secretary_client):
    _create_notification_for_resident(resident_client, secretary_client)

    r = resident_client.get('/api/notifications/unread-count')
    assert r.status_code == 200
    assert r.get_json()['count'] == 1


def test_mark_read(resident_client, secretary_client):
    _create_notification_for_resident(resident_client, secretary_client)
    notif = resident_client.get('/api/notifications').get_json()['notifications'][0]

    r = resident_client.patch(f"/api/notifications/{notif['id']}/read")
    assert r.status_code == 200
    assert r.get_json()['notification']['is_read'] is True

    assert resident_client.get('/api/notifications/unread-count').get_json()['count'] == 0


def test_cannot_mark_someone_elses_notification_read(resident_client, resident_client_2, secretary_client):
    _create_notification_for_resident(resident_client, secretary_client)
    notif = resident_client.get('/api/notifications').get_json()['notifications'][0]

    r = resident_client_2.patch(f"/api/notifications/{notif['id']}/read")
    assert r.status_code == 403


def test_mark_all_read(resident_client, secretary_client):
    _create_notification_for_resident(resident_client, secretary_client)

    r = resident_client.patch('/api/notifications/read-all')
    assert r.status_code == 200
    assert resident_client.get('/api/notifications/unread-count').get_json()['count'] == 0