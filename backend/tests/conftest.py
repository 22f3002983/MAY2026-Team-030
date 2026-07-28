import os
import sys

# use an isolated in-memory database for every test run — must be set
# before app.config (and therefore app.config.Config) is imported
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import create_app


@pytest.fixture()
def app():
    """A fresh Flask app (and fresh in-memory SQLite DB) for every test."""
    application = create_app()
    application.config['TESTING'] = True
    yield application


@pytest.fixture()
def client(app):
    """An unauthenticated test client."""
    return app.test_client()


def register(test_client, email, password, role, name, phone='9000000000', **extra):
    """Register a user via the real /api/auth/register endpoint."""
    payload = {
        'email': email, 'password': password, 'role': role,
        'name': name, 'phone': phone, **extra,
    }
    return test_client.post('/api/auth/register', json=payload)


def login(test_client, email, password):
    return test_client.post('/api/auth/login', json={'email': email, 'password': password})


@pytest.fixture()
def resident_client(app):
    """An authenticated client logged in as a resident."""
    c = app.test_client()
    register(c, 'resident@test.com', 'Passw0rd1', 'resident', 'Res Ident', phone='9000000001')
    login(c, 'resident@test.com', 'Passw0rd1')
    return c


@pytest.fixture()
def resident_client_2(app):
    """A second, distinct resident — for multi-reporter scenarios."""
    c = app.test_client()
    register(c, 'resident2@test.com', 'Passw0rd1', 'resident', 'Res Ident Two', phone='9000000004')
    login(c, 'resident2@test.com', 'Passw0rd1')
    return c


@pytest.fixture()
def secretary_client(app):
    """An authenticated client logged in as a secretary."""
    c = app.test_client()
    register(c, 'secretary@test.com', 'Passw0rd1', 'secretary', 'Sec Retary', phone='9000000002')
    login(c, 'secretary@test.com', 'Passw0rd1')
    return c


@pytest.fixture()
def security_client(app):
    """An authenticated client logged in as a security guard."""
    c = app.test_client()
    register(c, 'security@test.com', 'Passw0rd1', 'security', 'Sec Urity', phone='9000000003')
    login(c, 'security@test.com', 'Passw0rd1')
    return c
