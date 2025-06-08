from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
import calendar

from .utils.decorator import role_required
from .query.q_perhitungan_gaji import get_rekap_absensi, get_rekap_absensi_by_id

perhitungan_ns = Namespace('perhitungan', description='Perhitungan Gaji')

date_parser = reqparse.RequestParser()
date_parser.add_argument('start', type=str, required=False, help='Tanggal mulai (DD-MM-YYYY)')
date_parser.add_argument('end', type=str, required=False, help='Tanggal akhir (DD-MM-YYYY)')


@perhitungan_ns.route('/')
class RekapanGaji(Resource):
    @jwt_required()
    @role_required('admin')
    @perhitungan_ns.expect(date_parser)
    def get(self):
        """Akses: (admin), Mengambil rekapan gaji semua pegawai periode tertentu"""
        args = date_parser.parse_args()
        start_param = args.get('start')
        end_param = args.get('end')

        try:
            if start_param and end_param:
                start = datetime.strptime(start_param, "%d-%m-%Y").date()
                end = datetime.strptime(end_param, "%d-%m-%Y").date()
            else:
                today = date.today()
                start = date(today.year, today.month, 1)
                last_day = calendar.monthrange(today.year, today.month)[1]
                end = min(today, date(today.year, today.month, last_day))
        except ValueError:
            return {'status': 'Format tanggal tidak valid. Gunakan format DD-MM-YYYY'}, 400

        data = get_rekap_absensi(start, end)

        return {
            'tanggal_start': start.strftime("%d-%m-%Y"),
            'tanggal_end': end.strftime("%d-%m-%Y"),
            'rekap': data
        }, 200


@perhitungan_ns.route('/person')
class RekapanGajiPerorang(Resource):
    @jwt_required()
    @role_required('karyawan')
    @perhitungan_ns.expect(date_parser)
    def get(self):
        """Akses: (karyawan), Mengambil rekapan gaji pegawai periode tertentu"""
        args = date_parser.parse_args()
        start_param = args.get('start')
        end_param = args.get('end')

        try:
            if start_param and end_param:
                start = datetime.strptime(start_param, "%d-%m-%Y").date()
                end = datetime.strptime(end_param, "%d-%m-%Y").date()
            else:
                today = date.today()
                start = date(today.year, today.month, 1)
                last_day = calendar.monthrange(today.year, today.month)[1]
                end = min(today, date(today.year, today.month, last_day))
        except ValueError:
            return {'status': 'Format tanggal tidak valid. Gunakan format DD-MM-YYYY'}, 400

        id_karyawan = get_jwt_identity()
        data = get_rekap_absensi_by_id(start, end, id_karyawan)

        if not data:
            return {'status': 'Data tidak ditemukan untuk karyawan ini'}, 404

        return {
            'tanggal_start': start.strftime("%d-%m-%Y"),
            'tanggal_end': end.strftime("%d-%m-%Y"),
            'data_karyawan': data
        }, 200
