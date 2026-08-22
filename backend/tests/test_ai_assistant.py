import pytest


import app.routes.ai_assistant as ai_assistant_module
from app.services import ai_navigation


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




# ── POST /api/ai-assistant/chat ──────────────────────────────────


def test_chat_requires_login(app):
    # app.extensions registers a custom unauthorized_handler that returns
    # a 401 JSON body instead of flask-login's default 302 redirect, so
    # unauthenticated requests to any @login_required route get a 401 —
    # same app-wide behavior as every other route, not specific to this
    # endpoint.
    c = app.test_client()
    res = c.post('/api/ai-assistant/chat', json={'message': 'hello'})
    assert res.status_code == 401




def test_chat_requires_message(resident_client):
    res = resident_client.post('/api/ai-assistant/chat', json={'message': ''})
    assert res.status_code == 400




def test_chat_returns_reply(resident_client, monkeypatch):
    monkeypatch.setattr(ai_assistant_module, 'get_navigation_reply', lambda role, message: 'Go to Complaints in the sidebar.')
    res = resident_client.post('/api/ai-assistant/chat', json={'message': 'how do I raise a complaint', 'role': 'resident'})
    assert res.status_code == 200
    assert res.get_json() == {'reply': 'Go to Complaints in the sidebar.'}




def test_chat_uses_server_side_role_not_client_supplied(resident_client, monkeypatch):
    """A resident claiming role='secretary' in the request body must not
    change which system prompt gets built — the server trusts
    current_user.role, never the client-supplied value."""
    seen_roles = []


    def fake_reply(role, message):
        seen_roles.append(role)
        return 'reply'


    monkeypatch.setattr(ai_assistant_module, 'get_navigation_reply', fake_reply)


    resident_client.post('/api/ai-assistant/chat', json={'message': 'hi', 'role': 'secretary'})
    assert seen_roles == ['resident']




def test_chat_works_for_secretary_role(secretary_client, monkeypatch):
    seen_roles = []


    def fake_reply(role, message):
        seen_roles.append(role)
        return 'reply'


    monkeypatch.setattr(ai_assistant_module, 'get_navigation_reply', fake_reply)


    res = secretary_client.post('/api/ai-assistant/chat', json={'message': 'how do I add a vendor'})
    assert res.status_code == 200
    assert seen_roles == ['secretary']




def test_chat_fallback_reply_is_returned_as_is(resident_client, monkeypatch):
    monkeypatch.setattr(ai_assistant_module, 'get_navigation_reply', lambda role, message: ai_navigation.FALLBACK_REPLY)
    res = resident_client.post('/api/ai-assistant/chat', json={'message': 'hello'})
    assert res.status_code == 200
    assert res.get_json() == {'reply': ai_navigation.FALLBACK_REPLY}




# ── app/services/ai_navigation.py — unit-level, no HTTP ──────────


def test_get_navigation_reply_falls_back_without_api_key(app):
    with app.app_context():
        app.config['OPENROUTER_API_KEY'] = None
        reply = ai_navigation.get_navigation_reply('resident', 'how do I pay dues')
        assert reply == ai_navigation.FALLBACK_REPLY




def test_secretary_system_prompt_includes_complaints_and_electricity_bills(app):
    """Regression test: the secretary prompt used to omit enough detail that
    the model would claim complaint management wasn't available, even though
    it's the first item in the secretary's feature list."""
    with app.app_context():
        prompt = ai_navigation.build_system_prompt('secretary')
        assert '/sec/complaints' in prompt
        assert '/sec/electricity' in prompt
        assert 'vendor' in prompt.lower()




def test_resident_system_prompt_differs_from_secretary(app):
    with app.app_context():
        resident_prompt = ai_navigation.build_system_prompt('resident')
        secretary_prompt = ai_navigation.build_system_prompt('secretary')
        assert '/sec/electricity' not in resident_prompt
        assert '/services' in resident_prompt