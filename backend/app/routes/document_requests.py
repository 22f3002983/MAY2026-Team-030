from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models.document_request import DocumentRequest
from app.routes.notifications import create_notification
import base64
import os
import uuid
from datetime import datetime

document_requests_bp = Blueprint('document_requests', __name__)

VALID_TYPES = ('noc', 'payment_receipt', 'other')
ALLOWED_EXTENSIONS = ('pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp')
TYPE_LABELS = {'noc': 'NOC', 'payment_receipt': 'Payment Receipt', 'other': 'Other'}


# ── helper ────────────────────────────────────────────────────

def request_to_dict(r):
    resident = r.resident
    return {
        'id':            r.id,
        'resident_id':   r.resident_id,
        'resident_name': resident.name if resident else '—',
        'flat_number':   resident.flat.flat_number if resident and resident.flat else None,
        'type':          r.type,
        'reason':        r.reason,
        'status':        r.status,
        'file_url':      r.file_url,
        'requested_at':  r.requested_at.isoformat() if r.requested_at else None,
        'ready_at':      r.ready_at.isoformat() if r.ready_at else None,
    }


# ── POST /api/document-requests — resident submits a request ──────────────

@document_requests_bp.route('', methods=['POST'])
@login_required
def create_request():
    if current_user.role != 'resident' or not current_user.resident:
        return jsonify({'error': 'Only residents can submit document requests'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    doc_type = data.get('type', '')
    reason   = data.get('reason', '').strip()

    if doc_type not in VALID_TYPES:
        return jsonify({'error': f'type must be one of {VALID_TYPES}'}), 400

    doc_request = DocumentRequest(
        id=str(uuid.uuid4()),
        resident_id=current_user.resident.id,
        type=doc_type,
        reason=reason,
        status='requested',
    )

    db.session.add(doc_request)
    db.session.commit()

    return jsonify({
        'message': 'Document request submitted',
        'request': request_to_dict(doc_request),
    }), 201


# ── GET /api/document-requests — resident sees own, secretary sees all ────

@document_requests_bp.route('', methods=['GET'])
@login_required
def list_requests():
    status = request.args.get('status')

    if current_user.role == 'resident':
        query = DocumentRequest.query.filter_by(resident_id=current_user.resident.id)
    elif current_user.role == 'secretary':
        query = DocumentRequest.query
    else:
        return jsonify({'error': 'Unauthorized'}), 403

    if status:
        query = query.filter_by(status=status)

    requests_list = query.order_by(DocumentRequest.requested_at.desc()).all()

    return jsonify({
        'requests': [request_to_dict(r) for r in requests_list],
        'total':    len(requests_list),
    }), 200


# ── PATCH /api/document-requests/<id>/upload — secretary uploads the file ──

@document_requests_bp.route('/<request_id>/upload', methods=['PATCH'])
@login_required
def upload_document(request_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can upload documents'}), 403

    doc_request = DocumentRequest.query.get_or_404(request_id)
    data        = request.get_json() or {}

    filename  = data.get('filename', '').strip()
    file_data = data.get('file_data', '')

    if not filename or not file_data:
        return jsonify({'error': 'filename and file_data are required'}), 400

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'File must be a PDF or an image (jpg, jpeg, png, gif, webp)'}), 400

    # allow either a raw base64 string or a data: URL
    if file_data.strip().startswith('data:') and ',' in file_data:
        file_data = file_data.split(',', 1)[1]

    try:
        file_bytes = base64.b64decode(file_data)
    except Exception:
        return jsonify({'error': 'file_data is not valid base64'}), 400

    documents_dir = os.path.join(current_app.instance_path, 'documents')
    os.makedirs(documents_dir, exist_ok=True)

    file_path = os.path.join(documents_dir, f'{doc_request.id}.{ext}')
    with open(file_path, 'wb') as f:
        f.write(file_bytes)

    doc_request.file_url = f'documents/{doc_request.id}.{ext}'
    doc_request.status   = 'ready'
    doc_request.ready_at = datetime.utcnow()

    create_notification(
        user_id=doc_request.resident.user_id,
        message=f'Your document request ({TYPE_LABELS.get(doc_request.type, doc_request.type)}) is ready for download',
        type='document_ready',
    )

    db.session.commit()

    return jsonify({
        'message': 'Document uploaded and marked ready',
        'request': request_to_dict(doc_request),
    }), 200


# ── GET /api/document-requests/<id>/download — download the file ──────────

@document_requests_bp.route('/<request_id>/download', methods=['GET'])
@login_required
def download_document(request_id):
    doc_request = DocumentRequest.query.get_or_404(request_id)

    if current_user.role == 'resident':
        if not current_user.resident or doc_request.resident_id != current_user.resident.id:
            return jsonify({'error': 'Unauthorized'}), 403
    elif current_user.role != 'secretary':
        return jsonify({'error': 'Unauthorized'}), 403

    if not doc_request.file_url:
        return jsonify({'error': 'No file uploaded for this request'}), 404

    file_path = os.path.join(current_app.instance_path, doc_request.file_url)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    ext = doc_request.file_url.rsplit('.', 1)[-1]
    download_name = f'{doc_request.type}_{doc_request.id[:8]}.{ext}'

    return send_file(file_path, as_attachment=True, download_name=download_name)


# ── PATCH /api/document-requests/<id>/deliver — secretary marks delivered ─

@document_requests_bp.route('/<request_id>/deliver', methods=['PATCH'])
@login_required
def deliver_document(request_id):
    if current_user.role != 'secretary':
        return jsonify({'error': 'Only secretary can mark documents delivered'}), 403

    doc_request = DocumentRequest.query.get_or_404(request_id)
    doc_request.status = 'delivered'

    db.session.commit()

    return jsonify({
        'message': 'Document marked delivered',
        'request': request_to_dict(doc_request),
    }), 200
