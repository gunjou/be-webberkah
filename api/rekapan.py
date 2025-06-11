from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
import calendar
from .utils.decorator import role_required
from .query.q_rekapan import get_list_rekapan_person, get_rekap_absensi, get_rekap_person

rekapan_ns = Namespace('rekapan', description='Rekap Absensi')

rekap_absensi_parser = reqparse.RequestParser()
rekap_absensi_parser.add_argument('start', type=str, required=False, help='Tanggal awal (DD-MM-YYYY)')
rekap_absensi_parser.add_argument('end', type=str, required=False, help='Tanggal akhir (DD-MM-YYYY)')

def format_jam_menit(menit):
    if menit is None:
        return ""
    jam = menit // 60
    menit_sisa = menit % 60
    parts = []
    if jam > 0:
        parts.append(f"{jam} jam")
    if menit_sisa > 0:
        parts.append(f"{menit_sisa} menit")
    return " ".join(parts) if parts else "0 menit"


@rekapan_ns.route('/absensi')
class RekapAbsensi(Resource):
    @rekapan_ns.expect(rekap_absensi_parser)
    @role_required('admin')
    def get(self):
        """Akses: (admin), Mengambil rekapan absensi semua pegawai berdasarkan periode tertentu"""
        args = rekap_absensi_parser.parse_args()
        start_param = args.get('start')
        end_param = args.get('end')

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

        today = date.today()
        end = min(end_input, today)

        data = get_rekap_absensi(start, end)

        current_date = start
        hari_valid = 0
        while current_date <= end:
            if current_date.weekday() != 6:
                hari_valid += 1
            current_date += timedelta(days=1)

        for row in data:
            jumlah_status_valid = (
                row.get('jumlah_hadir', 0) +
                row.get('jumlah_sakit', 0) +
                row.get('jumlah_izin', 0) +
                row.get('jumlah_setengah_hari', 0) +
                row.get('dinas_luar', 0)
            )
            jumlah_alpha = hari_valid - jumlah_status_valid
            row['jumlah_alpha'] = max(jumlah_alpha, 0)

        return {
            'tanggal_start': start.strftime("%d-%m-%Y"),
            'tanggal_end': end.strftime("%d-%m-%Y"),
            'rekap': data
        }, 200


@rekapan_ns.route('/rekap')
class RekapBulananPerson(Resource):
    @rekapan_ns.expect(rekap_absensi_parser)  # pastikan parser hanya ambil `tanggal`
    @role_required('karyawan')
    def get(self):
        """Akses: (karyawan), Rekap absensi 1 bulan berdasarkan tanggal yang diberikan"""
        args = rekap_absensi_parser.parse_args()
        tanggal_param = args.get('tanggal')  # contoh: '10-06-2025'
        id_karyawan = get_jwt_identity()

        try:
            if tanggal_param:
                tanggal = datetime.strptime(tanggal_param, "%d-%m-%Y").date()
            else:
                tanggal = date.today()
        except ValueError:
            return {'status': 'Format tanggal tidak valid. Gunakan format DD-MM-YYYY'}, 400

        # Dapatkan range awal & akhir bulan dari tanggal yang diberikan
        start = date(tanggal.year, tanggal.month, 1)
        end_hari = calendar.monthrange(tanggal.year, tanggal.month)[1]
        end = min(date(tanggal.year, tanggal.month, end_hari), date.today())  # maksimal hari ini

        data = get_rekap_person(start, end, id_karyawan)

        # Hitung hari kerja valid (Senin - Sabtu)
        hari_valid = sum(1 for i in range((end - start).days + 1)
                         if (start + timedelta(days=i)).weekday() != 6)  # exclude Sunday

        # Ambil hanya 1 data (untuk 1 karyawan)
        if data:
            row = data[0]

            jumlah_status_valid = (
                row.get('jumlah_hadir', 0) +
                row.get('jumlah_sakit', 0) +
                row.get('jumlah_izin', 0) +
                row.get('jumlah_setengah_hari', 0) +
                row.get('dinas_luar', 0)
            )
            jumlah_alpha = hari_valid - jumlah_status_valid
            row['jumlah_alpha'] = max(jumlah_alpha, 0)

            return {
                'tanggal_start': start.strftime("%d-%m-%Y"),
                'tanggal_end': end.strftime("%d-%m-%Y"),
                'rekap': row  # bukan lagi list
            }, 200
        else:
            return {
                "message": "Data tidak ditemukan",
                "data": None
            }, 404

    
@rekapan_ns.route('/list')
class RekapAbsensiList(Resource):
    @rekapan_ns.expect(rekap_absensi_parser)
    @jwt_required()
    def get(self):
        """Akses: (admin, karyawan), Mengambil rekapan absensi pegawai periode tertentu"""
        id_karyawan = get_jwt_identity()
        args = rekap_absensi_parser.parse_args()
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

        absensi_data = get_list_rekapan_person(start, end, id_karyawan)

        if not absensi_data:
            return {'status': 'Data absensi tidak ditemukan untuk karyawan ini'}, 404

        from datetime import time
        for row in absensi_data:
            for field in ['jam_masuk', 'jam_keluar']:
                if isinstance(row.get(field), time):
                    row[field] = row[field].strftime('%H:%M:%S')

            for field in ['jam_terlambat', 'jam_kurang', 'total_jam_kerja']:
                val = row.get(field)
                if isinstance(val, int):
                    row[field] = format_jam_menit(val)

        return {
            'tanggal_start': start.strftime("%d-%m-%Y"),
            'tanggal_end': end.strftime("%d-%m-%Y"),
            'data_absensi': absensi_data
        }, 200
