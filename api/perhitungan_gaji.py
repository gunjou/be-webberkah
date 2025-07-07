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

@perhitungan_gaji_ns.route('/rekapan')
class RekapGajiResource(Resource):
    @jwt_required()
    @perhitungan_gaji_ns.doc(params={
        'start': 'Tanggal awal (format: DD-MM-YYYY)',
        'end': 'Tanggal akhir (format: DD-MM-YYYY)',
        'tanggal': 'Format tunggal tanggal DD-MM-YYYY (tidak bisa digunakan bersamaan dengan start/end)',
        'id_karyawan': 'Opsional, hanya untuk admin: ID karyawan spesifik'
    })
    def get(self):
        """Akses: (admin/karyawan), Rekap absensi berdasarkan tanggal yang diberikan"""
        id_user = get_jwt_identity()
        role = get_jwt().get("role")

        id_karyawan = request.args.get('id_karyawan') if role == 'admin' else id_user
        if role == 'admin' and id_karyawan:
            id_karyawan = int(id_karyawan)

        start_param = request.args.get('start')
        end_param = request.args.get('end')
        tanggal_param = request.args.get('tanggal')

        try:
            if tanggal_param:
                if start_param or end_param:
                    return {'status': 'Gunakan salah satu: tanggal atau start+end'}, 400
                tanggal = datetime.strptime(tanggal_param, "%d-%m-%Y").date()

                today = date.today()
                if tanggal.month == today.month and tanggal.year == today.year:
                    # Jika tanggal dalam bulan ini → gunakan range bulan ini
                    start = date(today.year, today.month, 1)
                    end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
                else:
                    # Jika tanggal di bulan sebelumnya → gunakan range bulan tersebut
                    start = date(tanggal.year, tanggal.month, 1)
                    end = date(tanggal.year, tanggal.month, calendar.monthrange(tanggal.year, tanggal.month)[1])

            elif start_param and end_param:
                start = datetime.strptime(start_param, "%d-%m-%Y").date()
                end = datetime.strptime(end_param, "%d-%m-%Y").date()
            else:
                # Default ke bulan ini full (1 - 31/30/28)
                today = date.today()
                start = date(today.year, today.month, 1)
                end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        except ValueError:
            return {'status': 'Format tanggal tidak valid. Gunakan format DD-MM-YYYY'}, 400

        hasil = get_rekap_gaji(start, end, id_karyawan=id_karyawan)
        return {'data': hasil}, 200
    

@perhitungan_gaji_ns.route('/harian')
class GajiHarianResource(Resource):
    @role_required('karyawan')
    @perhitungan_gaji_ns.doc(params={
        'tanggal': 'Tanggal yang ingin dihitung (format: DD-MM-YYYY)',
    })
    def get(self):
        """Akses: (karyawan), Rekap penghasilan harian pegawai"""
        id_karyawan = get_jwt_identity()

        tanggal_param = request.args.get('tanggal')

        if tanggal_param:
            try:
                tanggal = datetime.strptime(tanggal_param, "%d-%m-%Y").date()
            except ValueError:
                return {'status': 'Format tanggal tidak valid. Gunakan format DD-MM-YYYY'}, 400
        else:
            tanggal = date.today()  # default ke hari ini

        result = get_gaji_harian(tanggal, id_karyawan)
        if result is None:
            return {'status': 'Data tidak ditemukan'}, 404

        return {'data': result}, 200
