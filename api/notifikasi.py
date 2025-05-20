from flask import Blueprint

from .query import count_pending_notif

from .decorator import role_required


notifikasi_bp = Blueprint('api', __name__)

"""<-- Admin Side -->"""
@notifikasi_bp.route('/notifikasi-admin', methods=['GET'])
@role_required('admin')
def semua_notifikasi_admin():
    try:
        jumlah = count_pending_notif()
        return {'status': 'success', 'count': jumlah}, 200
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500