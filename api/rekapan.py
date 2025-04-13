from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from datetime import datetime, date
import calendar
from .query import get_rekap_absensi

rekapan_bp = Blueprint('rekapan', __name__)

@rekapan_bp.route('/rekapan/absensi', methods=['GET'])
@jwt_required()
def rekap_absensi():
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
            end = date(today.year, today.month, last_day)
    except ValueError:
        return {'status': 'Format tanggal tidak valid. Gunakan format DD-MM-YYYY'}, 400

    data = get_rekap_absensi(start, end)

    total_hari = (end - start).days + 1  # Jumlah total hari termasuk hari pertama dan terakhir

    # Hitung alpha berdasarkan pengurangan dari jumlah status valid
    for row in data:
        jumlah_status_valid = (
            row.get('jumlah_hadir', 0) +
            row.get('jumlah_sakit', 0) +
            row.get('jumlah_izin', 0) +
            row.get('jumlah_setengah_hari', 0) +
            row.get('dinas_luar', 0)
        )
        row['jumlah_alpha'] = total_hari - jumlah_status_valid

    return {
        'tanggal_start': start.strftime("%d-%m-%Y"),
        'tanggal_end': end.strftime("%d-%m-%Y"),
        'rekap': data
    }, 200
