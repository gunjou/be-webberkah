from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from .utils.decorator import role_required
from .query.q_cuti import get_kuota_cuti_pegawai, get_kuota_cuti_semua


cuti_ns = Namespace('cuti', description='Manajemen Cuti')

@cuti_ns.route('/kuota-cuti/<int:id_karyawan>')
class KuotaCutiResource(Resource):
    @cuti_ns.doc('get_kuota_cuti', params={'id_karyawan': 'ID Karyawan'})
    @jwt_required()
    def get(self, id_karyawan):
        """
        Mendapatkan sisa kuota cuti tahunan pegawai.
        """
        try:
            data = get_kuota_cuti_pegawai(id_karyawan)
            return {'status': 'success', 'data': data}, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
        

@cuti_ns.route('/kuota-cuti')
class KuotaCutiSemuaResource(Resource):
    @cuti_ns.doc('get_kuota_cuti_semua')
    @jwt_required()
    def get(self):
        """
        Mendapatkan sisa kuota cuti tahunan untuk semua karyawan.
        """
        try:
            data = get_kuota_cuti_semua()
            if data is None:
                return {'status': 'error', 'message': 'Gagal mengambil data'}, 500
            
            return {'status': 'success', 'data': data}, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
