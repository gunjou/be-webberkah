from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from datetime import datetime, date
import calendar
from .query import get_rekap_absensi

perhitungan_gaji_bp = Blueprint('perhitungan_gaji', __name__)

@perhitungan_gaji_bp.route('/rekapan_gaji', methods=['GET'])
@jwt_required()
def rekap_gaji():
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

    data = get_rekap_absensi(start, end)

    for row in data:
        gaji_pokok = row.get("gaji_pokok") or 0
        tipe_karyawan = row.get("tipe", "").lower()

        # Komponen Hari
        jumlah_hadir = row.get("jumlah_hadir") or 0
        jumlah_izin = row.get("jumlah_izin") or 0
        jumlah_sakit = row.get("jumlah_sakit") or 0
        dinas_luar = row.get("dinas_luar") or 0

        # Hitung hari yang dibayar
        if tipe_karyawan == 'tetap':
            hari_dibayar = jumlah_hadir + jumlah_izin + jumlah_sakit + dinas_luar
        else:
            hari_dibayar = jumlah_hadir + dinas_luar

        # Gaji per hari dan per menit
        gaji_per_hari = gaji_pokok / 26
        gaji_per_menit = gaji_pokok / 12480

        # Hitung Gaji Kotor
        gaji_kotor = hari_dibayar * gaji_per_hari

        # Potongan keterlambatan dan jam kurang
        total_terlambat = row.get("total_jam_terlambat") or 0
        total_kurang = row.get("total_jam_kurang") or 0
        total_potongan_menit = total_terlambat + total_kurang
        potongan = total_potongan_menit * gaji_per_menit

        # Hitung Gaji Bersih
        gaji_bersih = max(gaji_kotor - potongan, 0)

        # Tambahkan ke hasil
        row['hari_dibayar'] = hari_dibayar
        row['gaji_per_hari'] = round(gaji_per_hari)
        row['gaji_kotor'] = round(gaji_kotor)
        row['potongan'] = round(potongan)
        row['gaji_bersih'] = round(gaji_bersih)

    return {
        'tanggal_start': start.strftime("%d-%m-%Y"),
        'tanggal_end': end.strftime("%d-%m-%Y"),
        'rekap': data
    }, 200
