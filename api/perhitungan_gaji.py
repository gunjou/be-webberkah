from flask import request
from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, date
import calendar

from .utils.decorator import role_required
from .query.q_perhitungan_gaji import *


perhitungan_gaji_ns = Namespace('perhitungan-gaji', description='Perhitungan Gaji')

rekap_gaji_parser = reqparse.RequestParser()
rekap_gaji_parser.add_argument('start', type=str, required=False, help='Tanggal awal (DD-MM-YYYY)')
rekap_gaji_parser.add_argument('end', type=str, required=False, help='Tanggal akhir (DD-MM-YYYY)')

detail_gaji_parser = reqparse.RequestParser()
detail_gaji_parser.add_argument('id_karyawan', type=int, required=True, help='ID karyawan')
detail_gaji_parser.add_argument('start_date', type=str, required=False, help='Tanggal awal (DD-MM-YYYY)')
detail_gaji_parser.add_argument('end_date', type=str, required=False, help='Tanggal akhir (DD-MM-YYYY)')

@perhitungan_gaji_ns.route('/')
class RekapGajiResource(Resource):
    @jwt_required()
    @perhitungan_gaji_ns.doc(params={
        'start': 'Tanggal awal (format: DD-MM-YYYY)',
        'end': 'Tanggal akhir (format: DD-MM-YYYY)',
        'id_karyawan': 'Opsional, hanya untuk admin: ID karyawan spesifik'
    })
    def get(self):
        """Akses: (admin/karyawan), Rekap absensi 1 bulan berdasarkan tanggal yang diberikan"""
        id_user = get_jwt_identity()
        role = get_jwt().get("role")

        id_karyawan = request.args.get('id_karyawan') if role == 'admin' else id_user
        if role == 'admin' and id_karyawan:
            id_karyawan = int(id_karyawan)

        start_param = request.args.get('start')
        end_param = request.args.get('end')

        try:
            if start_param and end_param:
                start = datetime.strptime(start_param, "%d-%m-%Y").date()
                end_input = datetime.strptime(end_param, "%d-%m-%Y").date()
            else:
                today = date.today()
                start = date(today.year, today.month, 1)
                end_input = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        except ValueError:
            return {'status': 'Format tanggal tidak valid. Gunakan format DD-MM-YYYY'}, 400

        end = min(end_input, date.today())

        hasil = get_rekap_gaji(start, end, id_karyawan=id_karyawan)

        return {'data': hasil}, 200
    