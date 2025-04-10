from flask import Blueprint
from flask_jwt_extended import jwt_required

from .query import get_check_presensi


cek_presensi_bp = Blueprint('api', __name__)

@cek_presensi_bp.route('/cek_presensi/<int:id_karyawan>', methods=['GET'])
@jwt_required()
def absensi(id_karyawan):
    cek_presensi = get_check_presensi(id_karyawan)
        
    if not cek_presensi:
        return {"message": "Belum ada presensi"}, 200

    result = {
        "tanggal": cek_presensi["tanggal"],
        "jam_masuk": cek_presensi["jam_masuk"].strftime('%H:%M') if cek_presensi['jam_masuk'] else None,
        "jam_keluar": cek_presensi["jam_keluar"].strftime('%H:%M') if cek_presensi['jam_keluar'] else None,
        "lokasi_masuk": cek_presensi["lokasi_masuk"] if cek_presensi["lokasi_masuk"] else None,
        "lokasi_keluar": cek_presensi["lokasi_keluar"] if cek_presensi["lokasi_keluar"] else None,
        "jam_terlambat": cek_presensi["jam_terlambat"] if cek_presensi["jam_terlambat"] else None
    }
    
    return result, 200
