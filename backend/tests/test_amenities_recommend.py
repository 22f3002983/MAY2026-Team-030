import pytest


import app.routes.amenities as amenities_module


# NOTE: conftest.py's shared `resident_client` fixture doesn't pass the
# tower/floor/unit_number/flat_number fields resident registration requires,
# so it silently 400s and never logs in. Overridden here so these tests
# actually exercise an authenticated resident.




@pytest.fixture()
def resident_client(app):
    c = app.test_client()
    reg = c.post('/api/auth/register', json={
        'email': 'resident@test.com', 'password': 'Passw0rd1', 'role': 'resident',
        'name': 'Res Ident', 'phone': '9000000001',
        'tower': 'A', 'floor': 1, 'unit_number': '101', 'flat_number': 'A-101',
    })
    # a resident's FIRST login requires the invite code issued at registration
    invite_code = reg.get_json()['invite_code']
    c.post('/api/auth/login', json={'email': 'resident@test.com', 'password': 'Passw0rd1', 'invite_code': invite_code})
    return c




# ── POST /api/amenities/recommend ────────────────────────────────


def test_recommend_requires_login(app):
    # app.extensions registers a custom unauthorized_handler that returns
    # a 401 JSON body instead of flask-login's default 302 redirect, so
    # unauthenticated requests to any @login_required route get a 401 —
    # same app-wide behavior as every other route, not specific to this
    # endpoint.
    c = app.test_client()
    res = c.post('/api/amenities/recommend', json={'query': 'pool'})
    assert res.status_code == 401




def test_recommend_requires_query(resident_client):
    res = resident_client.post('/api/amenities/recommend', json={'query': ''})
    assert res.status_code == 400




def test_recommend_no_amenities_listed(resident_client):
    """Skips the AI call entirely when there's nothing to recommend from."""
    res = resident_client.post('/api/amenities/recommend', json={'query': 'I want to swim'})
    assert res.status_code == 200
    assert res.get_json() == {
        'recommendation': 'No amenities are currently listed in the society. Please check with the secretary.',
    }




def test_recommend_returns_ai_response_when_amenities_exist(secretary_client, resident_client, monkeypatch):
    secretary_client.post('/api/amenities', json={
        'name': 'Swimming Pool', 'type': 'public', 'description': 'Olympic-size pool, Floor 2',
    })


    monkeypatch.setattr(
        amenities_module, 'recommend_amenity',
        lambda amenities, query: 'The Swimming Pool on Floor 2 would be perfect for you.',
    )


    res = resident_client.post('/api/amenities/recommend', json={'query': 'I want a place to swim'})
    assert res.status_code == 200
    assert res.get_json() == {'recommendation': 'The Swimming Pool on Floor 2 would be perfect for you.'}




def test_recommend_passes_amenity_data_and_query_to_service(secretary_client, resident_client, monkeypatch):
    secretary_client.post('/api/amenities', json={
        'name': 'Swimming Pool', 'type': 'public', 'status': 'available', 'description': 'Floor 2 pool',
    })


    captured = {}


    def fake_recommend(amenities, query):
        captured['amenities'] = amenities
        captured['query'] = query
        return 'ok'


    monkeypatch.setattr(amenities_module, 'recommend_amenity', fake_recommend)


    resident_client.post('/api/amenities/recommend', json={'query': 'somewhere to swim'})


    assert captured['query'] == 'somewhere to swim'
    assert captured['amenities'] == [{
        'name': 'Swimming Pool', 'type': 'public', 'status': 'available', 'description': 'Floor 2 pool',
    }]




def test_recommend_no_api_key_returns_null(secretary_client, resident_client, monkeypatch):
    secretary_client.post('/api/amenities', json={'name': 'Gym', 'type': 'public'})
    monkeypatch.setattr(amenities_module, 'recommend_amenity', lambda amenities, query: None)


    res = resident_client.post('/api/amenities/recommend', json={'query': 'a place to work out'})
    assert res.status_code == 200
    assert res.get_json() == {'recommendation': None}




def test_recommend_works_for_secretary_role_too(secretary_client, monkeypatch):
    secretary_client.post('/api/amenities', json={'name': 'Gym', 'type': 'public'})
    monkeypatch.setattr(amenities_module, 'recommend_amenity', lambda amenities, query: 'The Gym would suit you.')


    res = secretary_client.post('/api/amenities/recommend', json={'query': 'somewhere to work out'})
    assert res.status_code == 200
    assert res.get_json() == {'recommendation': 'The Gym would suit you.'}