import os
import yaml
from flask import Flask, jsonify
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from app.config import Config
from app.extensions import db, login_manager

SWAGGER_URL = '/api/docs'
SWAGGER_SPEC_URL = '/api/swagger.json'
SWAGGER_YAML_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'swagger.yaml')

def create_app():
    flask_app = Flask(__name__, instance_relative_config=True)
    flask_app.config.from_object(Config)
    # run.py always starts the dev server with debug=True; set it here too so
    # code that runs during create_app() (e.g. the scheduler's reloader guard)
    # can rely on flask_app.debug before .run() would otherwise set it.
    flask_app.debug = True

    db.init_app(flask_app)
    login_manager.init_app(flask_app)
    CORS(flask_app, supports_credentials=True, origins=['http://localhost:5173'])

    from app.routes.auth import auth_bp
    flask_app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from app.routes.complaints import complaints_bp
    flask_app.register_blueprint(complaints_bp, url_prefix='/api/complaints')

    from app.routes.vendors import vendors_bp
    flask_app.register_blueprint(vendors_bp, url_prefix='/api/vendors')

    from app.routes.notices import notices_bp
    flask_app.register_blueprint(notices_bp, url_prefix='/api/notices')
   

    from app.routes.dues import dues_bp
    flask_app.register_blueprint(dues_bp, url_prefix='/api/dues')

    from app.routes.emergency import emergency_bp
    flask_app.register_blueprint(emergency_bp, url_prefix='/api/emergency')

    from app.routes.visitors import visitors_bp
    flask_app.register_blueprint(visitors_bp, url_prefix='/api/visitors')

    from app.routes.amenities import amenities_bp
    flask_app.register_blueprint(amenities_bp, url_prefix='/api/amenities')

    from app.routes.summary import summary_bp
    flask_app.register_blueprint(summary_bp, url_prefix='/api/summary')

    from app.routes.profile_requests import profile_requests_bp
    flask_app.register_blueprint(profile_requests_bp, url_prefix='/api/profile-requests')

    from app.routes.profile import profile_bp
    flask_app.register_blueprint(profile_bp, url_prefix='/api/profile')

    from app.routes.document_requests import document_requests_bp
    flask_app.register_blueprint(document_requests_bp, url_prefix='/api/document-requests')

    from app.routes.notifications import notifications_bp
    flask_app.register_blueprint(notifications_bp, url_prefix='/api/notifications')

    from app.routes.service_requests import service_requests_bp
    flask_app.register_blueprint(service_requests_bp, url_prefix='/api/service-requests')

    from app.routes.electricity_bills import electricity_bills_bp
    flask_app.register_blueprint(electricity_bills_bp, url_prefix='/api/electricity-bills')

    from app.routes.funds import funds_bp
    flask_app.register_blueprint(funds_bp, url_prefix='/api/funds')

    from app.routes.flats import flats_bp
    flask_app.register_blueprint(flats_bp, url_prefix='/api/flats')

    from app.routes.ai_assistant import ai_assistant_bp
    flask_app.register_blueprint(ai_assistant_bp, url_prefix='/api/ai-assistant')

    # ── Swagger / OpenAPI docs ──────────────────────────────────
    @flask_app.route(SWAGGER_SPEC_URL)
    def swagger_spec():
        with open(SWAGGER_YAML_PATH, encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        return jsonify(spec)

    swagger_ui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        SWAGGER_SPEC_URL,
        config={'app_name': 'Niwaas RWA Management API'},
    )
    flask_app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

    with flask_app.app_context():
        from app import models
        db.create_all()
        _ensure_telegram_columns(db.engine)

    from app.scheduler import start_scheduler
    start_scheduler(flask_app)

    from app.telegram_bot import start_telegram_bot
    start_telegram_bot(flask_app)

    return flask_app


def _ensure_telegram_columns(engine):
    """Non-destructive ALTER TABLE for telegram_chat_id — db.create_all()
    only creates missing tables, it never alters existing ones, so an
    existing niwaas.db needs this to pick up the new column."""
    from sqlalchemy import inspect, text

    for table in ('residents', 'secretary', 'security', 'vendors'):
        columns = [c['name'] for c in inspect(engine).get_columns(table)]
        if 'telegram_chat_id' not in columns:
            with engine.connect() as conn:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN telegram_chat_id VARCHAR(64)'))
                conn.commit()