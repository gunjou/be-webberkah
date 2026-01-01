from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required

from .query.q_potongan import *

potongan_ns = Namespace('potongan', description='Endpoint Potongan Gaji')

potongan_harian_parser = reqparse.RequestParser()
potongan_harian_parser.add_argument('id_karyawan', type=int, required=True, location='args', help='ID karyawan')
potongan_harian_parser.add_argument('bulan', type=int, required=True, location='args', help='Bulan (1-12)')
potongan_harian_parser.add_argument('tahun', type=int, required=True, location='args', help='Tahun (YYYY)')

potongan_bulanan_parser = reqparse.RequestParser()
potongan_bulanan_parser.add_argument('id_karyawan', type=int, required=True, location='args', help='ID karyawan')
potongan_bulanan_parser.add_argument('bulan', type=int, required=True, location='args', help='Bulan (1-12)')
potongan_bulanan_parser.add_argument('tahun', type=int, required=True, location='args', help='Tahun (YYYY)')


@potongan_ns.route('/harian/preview')
class PreviewPotonganHarianResource(Resource):
    @jwt_required()
    @potongan_ns.expect(potongan_harian_parser)
    def get(self):
        args = potongan_harian_parser.parse_args()

        id_karyawan = args['id_karyawan']
        bulan = args['bulan']
        tahun = args['tahun']

        hasil = hitung_potongan_harian(id_karyawan, bulan, tahun)

        if hasil is None:
            return {
                "status": "error",
                "message": "Gagal menghitung potongan"
            }, 500

        return {
            "id_karyawan": id_karyawan,
            "jenis_pegawai": hasil["jenis_pegawai"],
            "bulan": bulan,
            "tahun": tahun,
            "total_menit_terlambat": hasil["total_menit_terlambat"],
            "total_alpha": hasil["total_alpha"],
            "total_izin": hasil["total_izin"],
            "total_sakit": hasil["total_sakit"],
            "total_potongan": hasil["total_potongan"],
            "ringkasan_potongan": hasil["ringkasan_potongan"],
            "data": hasil["data"]
        }, 200


@potongan_ns.route('/bulanan/preview')
class PreviewPotonganBulananResource(Resource):
    @jwt_required()
    @potongan_ns.expect(potongan_bulanan_parser)
    def get(self):
        args = potongan_bulanan_parser.parse_args()

        id_karyawan = args['id_karyawan']
        bulan = args['bulan']
        tahun = args['tahun']

        # 1️⃣ Ambil hasil potongan harian (sebagai sumber kebenaran)
        harian = hitung_potongan_harian(id_karyawan, bulan, tahun)

        if harian is None:
            return {
                "status": "error",
                "message": "Gagal mengambil data potongan harian"
            }, 500

        # 2️⃣ Hitung potongan bulanan
        bulanan = hitung_potongan_bulanan(
            id_karyawan=id_karyawan,
            bulan=bulan,
            tahun=tahun,
            jenis_pegawai=harian["jenis_pegawai"],
            total_alpha=harian["total_alpha"],
            total_izin=harian["total_izin"],
            total_sakit=harian["total_sakit"],
            potongan_makan_harian=harian["ringkasan_potongan"]["tunjangan_makan"]
        )

        if bulanan is None:
            return {
                "status": "error",
                "message": "Gagal menghitung potongan bulanan"
            }, 500

        return {
            "id_karyawan": id_karyawan,
            "bulan": bulan,
            "tahun": tahun,
            "jenis_pegawai": harian["jenis_pegawai"],
            "rekap_disiplin": {
                "total_alpha": harian["total_alpha"],
                "total_izin": harian["total_izin"],
                "total_sakit": harian["total_sakit"]
            },
            "potongan_bulanan": bulanan
        }, 200