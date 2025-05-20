from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from .query import get_unread_notifikasi, set_notifikasi_dibaca


notifikasi_bp = Blueprint('api', __name__)

@notifikasi_bp.route('/notifikasi', methods=['GET'])
@jwt_required()
def get_notifikasi():
    role = request.args.get('role')
    id_karyawan = get_jwt_identity()

    if not role or role not in ['admin', 'karyawan']:
        return {'status': 'error', 'message': 'Role tidak valid'}, 400

    if role == 'karyawan' and not id_karyawan:
        return {'status': 'error', 'message': 'ID karyawan wajib diisi untuk role karyawan'}, 400

    try:
        notifikasi = get_unread_notifikasi(role, id_karyawan)
        return {'status': 'success', 'data': notifikasi, 'count':len(notifikasi)}, 200
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500
    
@notifikasi_bp.route('/notifikasi/<int:id_notifikasi>/read', methods=['PUT'])
@jwt_required()
def mark_notifikasi_as_read(id_notifikasi):
    try:
        updated = set_notifikasi_dibaca(id_notifikasi)
        if updated:
            return {'status': 'success', 'message': 'Notifikasi ditandai sudah dibaca'}
        else:
            return {'status': 'error', 'message': 'Notifikasi tidak ditemukan atau gagal diperbarui'}, 404
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

