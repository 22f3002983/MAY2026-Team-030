from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.ai_navigation import get_navigation_reply

ai_assistant_bp = Blueprint('ai_assistant', __name__)


# ── POST /api/ai-assistant/chat — navigation help chatbot ─────

@ai_assistant_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json() or {}
    message = (data.get('message') or '').strip()

    if not message:
        return jsonify({'error': 'message is required'}), 400

    # role is accepted for parity with the spec, but current_user.role is
    # what actually builds the prompt — a client-supplied role isn't trusted
    reply = get_navigation_reply(current_user.role, message)

    return jsonify({'reply': reply}), 200
