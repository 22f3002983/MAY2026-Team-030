from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask import jsonify

db            = SQLAlchemy()
login_manager = LoginManager()

login_manager.login_view      = 'auth.login'
login_manager.session_protection = 'strong'


# Without this, Flask-Login's default behaviour on an unauthenticated
# request to a @login_required route is to 302-redirect to login_view.
# That's meant for server-rendered apps; for this JSON API it makes axios
# silently follow the redirect to GET /api/auth/login (a POST-only route),
# producing a 405 and leaving the frontend with no usable error to react to.
# Returning 401 JSON here lets the frontend detect "session expired" and
# react (e.g. clear local auth state, redirect to /login).
@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'Authentication required'}), 401