from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from datetime import datetime, date
import calendar

from .query import get_rekap_absensi, get_rekap_absensi_by_id
from .decorator import role_required


perhitungan_gaji_bp = Blueprint('perhitungan_gaji', __name__)

@perhitungan_gaji_bp.route('/rekapan_gaji', methods=['GET'])
@role_required('admin')
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

        # Ambil jam
        total_terlambat = row.get("total_jam_terlambat") or 0
        total_jam_bolos = row.get("total_jam_kurang") or 0  # ini rename field lama
        total_jam_kurang = total_terlambat + total_jam_bolos

        # Potongan
        potongan = total_jam_kurang * gaji_per_menit
        gaji_kotor = hari_dibayar * gaji_per_hari
        gaji_bersih = max(gaji_kotor - potongan, 0)

        # Tambahkan ke hasil
        row['hari_dibayar'] = hari_dibayar
        row['gaji_per_hari'] = round(gaji_per_hari)
        row['gaji_kotor'] = round(gaji_kotor)
        row['potongan'] = round(potongan)
        row['gaji_bersih'] = round(gaji_bersih)
        row['total_jam_bolos'] = total_jam_bolos
        row['total_jam_kurang'] = total_jam_kurang  # hasil dari jam bolos + telat

    return {
        'tanggal_start': start.strftime("%d-%m-%Y"),
        'tanggal_end': end.strftime("%d-%m-%Y"),
        'rekap': data
    }, 200


@perhitungan_gaji_bp.route('/rekapan-person', methods=['GET'])
@role_required('karyawan')
def rekap_gaji_perorang():
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

    data = get_rekap_absensi_by_id(start, end, id_karyawan)

    if not data:
        return {'status': 'Data tidak ditemukan untuk karyawan ini'}, 404

    gaji_pokok = data.get("gaji_pokok") or 0
    tipe_karyawan = data.get("tipe", "").lower()

    jumlah_hadir = data.get("jumlah_hadir") or 0
    jumlah_izin = data.get("jumlah_izin") or 0
    jumlah_sakit = data.get("jumlah_sakit") or 0
    dinas_luar = data.get("dinas_luar") or 0

    if tipe_karyawan == 'tetap':
        hari_dibayar = jumlah_hadir + jumlah_izin + jumlah_sakit + dinas_luar
    else:
        hari_dibayar = jumlah_hadir + dinas_luar

    gaji_per_hari = gaji_pokok / 26
    gaji_per_menit = gaji_pokok / 12480

    gaji_kotor = hari_dibayar * gaji_per_hari

    total_terlambat = data.get("total_jam_terlambat") or 0
    total_kurang = data.get("total_jam_kurang") or 0
    total_potongan_menit = total_terlambat + total_kurang
    potongan = total_potongan_menit * gaji_per_menit

    gaji_bersih = max(gaji_kotor - potongan, 0)

    data['hari_dibayar'] = hari_dibayar
    data['gaji_per_hari'] = round(gaji_per_hari)
    data['gaji_kotor'] = round(gaji_kotor)
    data['potongan'] = round(potongan)
    data['gaji_bersih'] = round(gaji_bersih)

    return {
        'tanggal_start': start.strftime("%d-%m-%Y"),
        'tanggal_end': end.strftime("%d-%m-%Y"),
        'data_karyawan': data
    }, 200
