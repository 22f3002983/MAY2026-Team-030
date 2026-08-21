import time


import pytest


import app.routes.complaints as complaints_module


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




@pytest.fixture()
def resident_client_2(app):
    c = app.test_client()
    reg = c.post('/api/auth/register', json={
        'email': 'resident2@test.com', 'password': 'Passw0rd1', 'role': 'resident',
        'name': 'Res Ident Two', 'phone': '9000000004',
        'tower': 'A', 'floor': 1, 'unit_number': '102', 'flat_number': 'A-102',
    })
    invite_code = reg.get_json()['invite_code']
    c.post('/api/auth/login', json={'email': 'resident2@test.com', 'password': 'Passw0rd1', 'invite_code': invite_code})
    return c




def raise_complaint(client, **overrides):
    payload = {
        'title': 'Leaky tap', 'description': 'Water leaking under the kitchen sink',
        'category': 'plumbing', 'type': 'personal',
    }
    payload.update(overrides)
    return client.post('/api/complaints', json=payload)




def wait_until(predicate, timeout=3.0, interval=0.05):
    """Polls predicate() until it's True or timeout elapses. Exceptions from
    predicate() are swallowed and treated as 'not yet' — the background AI
    thread and this polling loop use separate SQLite connections/sessions,
    and can transiently collide (e.g. 'cannot rollback - no transaction is
    active') right as the background thread's session is being torn down.
    That's a real race in the in-memory-SQLite + threading test setup, not
    a bug in the request/response cycle being tested — retrying rides it out."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if predicate():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False




def _create_issue_directly(app, title='Leaky tap', description='Water leaking under the kitchen sink', category='plumbing'):
    """Builds a CommunityIssue + Complaint straight through the DB layer,
    bypassing POST /api/complaints entirely — so the route's own
    threading.Thread(_run_ai_suggestions, ...) never fires. Used by tests
    that want to call _run_ai_suggestions themselves, deterministically,
    without a second real background thread racing them (see the module
    docstring note on SQLite :memory: + threading below)."""
    import uuid
    from app.extensions import db
    from app.models.community_issue import CommunityIssue
    from app.models.complaint import Complaint
    from app.models.resident import Resident


    with app.app_context():
        resident = Resident.query.first()
        issue = CommunityIssue(
            id=str(uuid.uuid4()), title=title, description=description,
            category=category, priority='medium', type='personal', status='open',
            created_by=resident.id,
        )
        db.session.add(issue)
        db.session.flush()
        db.session.add(Complaint(id=str(uuid.uuid4()), issue_id=issue.id, resident_id=resident.id, description=description))
        db.session.commit()
        return issue.id




# ── POST /api/complaints — background AI wiring ─────────────────
#
# Only one test below (test_create_complaint_returns_before_ai_finishes)
# goes through the REAL HTTP request + threading.Thread path — that's the
# one thing that actually needs a real thread to prove (the response isn't
# blocked on it). Every other test calls _run_ai_suggestions directly, since
# two concurrent SQLite :memory: sessions (this test process's app_context
# and the background thread's own) can occasionally collide — a commit from
# one session can invalidate another session's in-flight multi-row read,
# surfacing as a flaky 'cannot rollback' / 'Cursor needed to be reset'
# error. That's a real limitation of SQLite's :memory: connection sharing
# under concurrent test access, not a bug in _run_ai_suggestions itself —
# calling it directly exercises the exact same production code without
# that infrastructure race.


def test_create_complaint_returns_before_ai_finishes(app, resident_client, monkeypatch):
    def slow_category(text, valid_categories):
        time.sleep(1.0)
        return 'plumbing'


    def slow_priority(title, description, category):
        time.sleep(1.0)
        return 'high'


    monkeypatch.setattr(complaints_module, 'suggest_category', slow_category)
    monkeypatch.setattr(complaints_module, 'suggest_priority', slow_priority)
    monkeypatch.setattr(complaints_module, 'suggest_summary', lambda title, category, descriptions: 'A merged summary')


    start = time.time()
    res = raise_complaint(resident_client)
    elapsed = time.time() - start


    assert res.status_code == 201
    assert elapsed < 0.5  # the mocked AI calls alone would take ~2s if run synchronously
    data = res.get_json()['complaint']
    assert data['ai_suggested_category'] is None
    assert data['ai_suggested_priority'] is None


    issue_id = data['issue_id']
    from app.models.community_issue import CommunityIssue


    def is_populated():
        with app.app_context():
            return CommunityIssue.query.get(issue_id).ai_suggested_category is not None


    assert wait_until(is_populated, timeout=3.0), 'background AI thread never populated ai_suggested_category'


    with app.app_context():
        issue = CommunityIssue.query.get(issue_id)
        assert issue.ai_suggested_category == 'plumbing'
        assert issue.ai_suggested_priority == 'high'
        assert issue.ai_suggested_description == 'A merged summary'




def test_run_ai_suggestions_new_issue_computes_all_three_fields(app, resident_client, monkeypatch):
    monkeypatch.setattr(complaints_module, 'suggest_category', lambda text, valid_categories: 'plumbing')
    monkeypatch.setattr(complaints_module, 'suggest_priority', lambda title, description, category: 'high')
    monkeypatch.setattr(complaints_module, 'suggest_summary', lambda title, category, descriptions: 'A merged summary')


    issue_id = _create_issue_directly(app)


    with app.app_context():
        complaints_module._run_ai_suggestions(app, issue_id, 'Leaky tap', 'Water leaking under the kitchen sink', 'plumbing', True)


        from app.models.community_issue import CommunityIssue
        issue = CommunityIssue.query.get(issue_id)
        assert issue.ai_suggested_category == 'plumbing'
        assert issue.ai_suggested_priority == 'high'
        assert issue.ai_suggested_description == 'A merged summary'




def test_run_ai_suggestions_join_reruns_summary_only(app, resident_client, monkeypatch):
    """Joining an existing issue must re-merge the summary (a second
    reporter's wording matters) but must NOT re-run category/priority —
    those are only meaningful once, at issue creation."""
    category_calls = []
    priority_calls = []
    summary_calls = []
    monkeypatch.setattr(complaints_module, 'suggest_category', lambda t, v: category_calls.append(1) or 'plumbing')
    monkeypatch.setattr(complaints_module, 'suggest_priority', lambda t, d, c: priority_calls.append(1) or 'high')
    monkeypatch.setattr(complaints_module, 'suggest_summary', lambda title, category, descriptions: summary_calls.append(1) or f'Merged {len(descriptions)} report(s)')


    issue_id = _create_issue_directly(app)


    with app.app_context():
        complaints_module._run_ai_suggestions(app, issue_id, 'Leaky tap', 'Water leaking under the kitchen sink', 'plumbing', True)
    assert len(category_calls) == 1
    assert len(priority_calls) == 1
    assert len(summary_calls) == 1


    # a second report lands on the same issue, then the join path runs
    # (compute_category_priority=False) — exactly what create_complaint()
    # does when is_new_issue is False
    import uuid
    from app.extensions import db
    from app.models.complaint import Complaint
    from app.models.resident import Resident
    with app.app_context():
        resident = Resident.query.first()
        db.session.add(Complaint(id=str(uuid.uuid4()), issue_id=issue_id, resident_id=resident.id, description='Same leak here too'))
        db.session.commit()
        complaints_module._run_ai_suggestions(app, issue_id, 'Leaky tap', 'ignored', 'plumbing', False)


    assert len(category_calls) == 1  # unchanged — join path must not recompute it
    assert len(priority_calls) == 1  # unchanged
    assert len(summary_calls) == 2   # summary DOES rerun on join


    with app.app_context():
        from app.models.community_issue import CommunityIssue
        assert CommunityIssue.query.get(issue_id).ai_suggested_description == 'Merged 2 report(s)'




def test_background_ai_failure_does_not_crash(resident_client, monkeypatch):
    def raises(*a, **kw):
        raise RuntimeError('simulated OpenRouter failure')


    monkeypatch.setattr(complaints_module, 'suggest_category', raises)
    monkeypatch.setattr(complaints_module, 'suggest_priority', raises)
    monkeypatch.setattr(complaints_module, 'suggest_summary', raises)


    res = raise_complaint(resident_client)
    assert res.status_code == 201  # the request itself never sees the background exception


    time.sleep(0.3)  # let the background thread run and fail internally


    # the process must still be responsive — a crashed thread shouldn't affect it
    res2 = resident_client.get('/api/complaints')
    assert res2.status_code == 200




# ── POST /api/complaints/suggest ─────────────────────────────────


def test_suggest_category_returns_suggestion(resident_client, monkeypatch):
    monkeypatch.setattr(complaints_module, 'suggest_category', lambda text, valid_categories: 'electrical')


    res = resident_client.post('/api/complaints/suggest', json={'description': 'sparking wires near the meter'})
    assert res.status_code == 200
    assert res.get_json() == {'category': 'electrical', 'confidence': 'medium'}




def test_suggest_category_no_suggestion_available(resident_client, monkeypatch):
    monkeypatch.setattr(complaints_module, 'suggest_category', lambda text, valid_categories: None)


    res = resident_client.post('/api/complaints/suggest', json={'description': 'something odd'})
    assert res.status_code == 200
    assert res.get_json() == {'category': None}




def test_suggest_category_requires_description(resident_client):
    res = resident_client.post('/api/complaints/suggest', json={'description': ''})
    assert res.status_code == 400




def test_suggest_category_resident_only(secretary_client):
    res = secretary_client.post('/api/complaints/suggest', json={'description': 'leaking pipe'})
    assert res.status_code == 403




# ── POST /api/complaints/suggest-priority ────────────────────────


def test_suggest_priority_returns_suggestion(resident_client, monkeypatch):
    monkeypatch.setattr(complaints_module, 'suggest_priority', lambda title, description, category: 'high')


    res = resident_client.post('/api/complaints/suggest-priority', json={
        'description': 'sparking wires', 'category': 'electrical', 'title': 'Sparking wires',
    })
    assert res.status_code == 200
    assert res.get_json() == {'priority': 'high'}




def test_suggest_priority_validates_category(resident_client):
    res = resident_client.post('/api/complaints/suggest-priority', json={
        'description': 'x', 'category': 'not-a-real-category',
    })
    assert res.status_code == 400




def test_suggest_priority_resident_only(secretary_client):
    res = secretary_client.post('/api/complaints/suggest-priority', json={
        'description': 'x', 'category': 'electrical',
    })
    assert res.status_code == 403




# ── POST /api/complaints/check-duplicates ────────────────────────


def test_check_duplicates_returns_matches_for_other_residents(resident_client, resident_client_2, monkeypatch):
    monkeypatch.setattr(complaints_module, 'suggest_category', lambda t, v: None)
    monkeypatch.setattr(complaints_module, 'suggest_priority', lambda t, d, c: None)
    monkeypatch.setattr(complaints_module, 'suggest_summary', lambda t, c, d: None)


    issue_id = raise_complaint(
        resident_client, title='Corridor light flickering', category='electrical', type='common_area',
    ).get_json()['complaint']['issue_id']


    monkeypatch.setattr(complaints_module, 'find_semantic_duplicates', lambda t, d, candidates: [issue_id])


    res = resident_client_2.post('/api/complaints/check-duplicates', json={
        'title': 'Light flickering in hallway', 'description': 'same flickering light problem',
        'category': 'electrical',
    })
    assert res.status_code == 200
    assert res.get_json() == {'matches': [issue_id]}




def test_check_duplicates_excludes_residents_own_issues(resident_client, monkeypatch):
    """Regression test: a resident re-checking duplicates in a category
    where they're the only prior reporter should never see their own issue
    offered back as a 'match' to join — this is the exact confusion a user
    hit in practice (checked for cockroaches, got 'none match' because they'd
    already reported it themselves)."""
    monkeypatch.setattr(complaints_module, 'suggest_category', lambda t, v: None)
    monkeypatch.setattr(complaints_module, 'suggest_priority', lambda t, d, c: None)
    monkeypatch.setattr(complaints_module, 'suggest_summary', lambda t, c, d: None)


    issue_id = raise_complaint(
        resident_client, title='Cockroaches', category='pest_control', description='too many cockroaches in my kitchen',
    ).get_json()['complaint']['issue_id']


    seen_candidates = {}
    def fake_find(t, d, candidates):
        seen_candidates['value'] = candidates
        # mirrors the real service's own contract (find_semantic_duplicates
        # returns [] when given no candidates) — the point of this test is
        # that candidates is already [] by the time the AI would be asked
        return [issue_id] if candidates else []
    monkeypatch.setattr(complaints_module, 'find_semantic_duplicates', fake_find)


    res = resident_client.post('/api/complaints/check-duplicates', json={
        'title': 'Roaches everywhere', 'description': 'more roaches showed up', 'category': 'pest_control',
    })
    assert res.status_code == 200
    assert res.get_json() == {'matches': []}
    assert seen_candidates['value'] == []  # excluded before the AI was even asked




def test_check_duplicates_resident_only(secretary_client):
    res = secretary_client.post('/api/complaints/check-duplicates', json={
        'title': 'x', 'description': 'y', 'category': 'plumbing',
    })
    assert res.status_code == 403



