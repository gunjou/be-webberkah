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
        "jam_masuk": cek_presensi["jam_masuk"],
        "jam_keluar": cek_presensi["jam_keluar"],
        "lokasi_masuk": cek_presensi["lokasi_masuk"],
        "lokasi_keluar": cek_presensi["lokasi_keluar"]
    }
    
    return result, 200
