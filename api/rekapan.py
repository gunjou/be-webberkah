from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from datetime import datetime, date, timedelta
import calendar

from .query import get_list_rekapan_person, get_rekap_absensi
from .decorator import role_required


rekapan_bp = Blueprint('rekapan', __name__)

@rekapan_bp.route('/rekapan/absensi', methods=['GET'])
@role_required('admin')
def rekap_absensi():
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

    today = date.today()
    end = min(end_input, today)

    data = get_rekap_absensi(start, end)

    # Hitung total hari valid TANPA Minggu (weekday() == 6)
    current_date = start
    hari_valid = 0
    while current_date <= end:
        if current_date.weekday() != 6:  # 6 = Minggu
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


from datetime import time

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


@rekapan_bp.route('/list-rekapan-person', methods=['GET'])
@role_required('karyawan')
def rekap_absensi_person():
    from flask_jwt_extended import get_jwt_identity
    id_karyawan = get_jwt_identity()

    start_param = request.args.get('start')
    end_param = request.args.get('end')

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

    for row in absensi_data:
    # Format jam masuk & keluar
        for field in ['jam_masuk', 'jam_keluar']:
            if isinstance(row.get(field), time):
                row[field] = row[field].strftime('%H:%M:%S')

        # Format integer menit jadi "x jam y menit"
        for field in ['jam_terlambat', 'jam_kurang', 'total_jam_kerja']:
            val = row.get(field)
            if isinstance(val, int):
                row[field] = format_jam_menit(val)


    return {
        'tanggal_start': start.strftime("%d-%m-%Y"),
        'tanggal_end': end.strftime("%d-%m-%Y"),
        'data_absensi': absensi_data
    }, 200
