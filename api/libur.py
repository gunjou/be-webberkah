from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from .query.q_libur import *


libur_ns = Namespace('libur', description='Manajemen Hari Libur')

@libur_ns.route('/')
class DaftarHariLiburResource(Resource):
    @jwt_required()
    @libur_ns.doc(security='Bearer Auth', description='Menampilkan semua hari libur (Hari Minggu & Libur Nasional)')
    def get(self):
        """Akses: (admin/karyawan), Mengambil daftar semua hari libur"""
        hasil = get_hari_libur()
        if hasil is None:
            return {"status": "Gagal mengambil hari libur"}, 500

        return {"data": hasil}, 200
    

@libur_ns.route('/cek')
class CekHariLiburResource(Resource):
    @jwt_required()
    @libur_ns.doc(security='Bearer Auth', params={'tanggal': 'Format: YYYY-MM-DD'},
                  description='Cek apakah tanggal tertentu adalah hari libur')
    def get(self):
        """Akses: (admin/karyawan), Cek apakah tanggal adalah hari libur"""
        from flask import request

        tanggal = request.args.get('tanggal')
        if not tanggal:
            return {"status": "Tanggal tidak diberikan"}, 400

        hasil = is_libur(tanggal)
        return {"tanggal": tanggal, "libur": hasil}, 200