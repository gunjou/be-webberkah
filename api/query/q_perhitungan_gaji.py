from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection


def process_rekap_absensi(data):
    for row in data:
        gaji_pokok = row.get("gaji_pokok") or 0
        tipe_karyawan = row.get("tipe", "").lower()

        jumlah_hadir = row.get("jumlah_hadir") or 0
        jumlah_izin = row.get("jumlah_izin") or 0
        jumlah_sakit = row.get("jumlah_sakit") or 0
        dinas_luar = row.get("dinas_luar") or 0

        if tipe_karyawan == 'tetap':
            hari_dibayar = jumlah_hadir + jumlah_izin + jumlah_sakit + dinas_luar
        else:
            hari_dibayar = jumlah_hadir + dinas_luar

        gaji_per_hari = gaji_pokok / 26
        gaji_per_menit = gaji_pokok / 12480

        total_terlambat = row.get("total_jam_terlambat") or 0
        total_jam_bolos = row.get("total_jam_kurang") or 0
        total_jam_kurang = total_terlambat + total_jam_bolos

        potongan = total_jam_kurang * gaji_per_menit
        gaji_kotor = hari_dibayar * gaji_per_hari
        gaji_bersih = max(gaji_kotor - potongan, 0)

        row['hari_dibayar'] = hari_dibayar
        row['gaji_per_hari'] = round(gaji_per_hari)
        row['gaji_kotor'] = round(gaji_kotor)
        row['potongan'] = round(potongan)
        row['gaji_bersih'] = round(gaji_bersih)
        row['total_jam_bolos'] = total_jam_bolos
        row['total_jam_kurang'] = total_jam_kurang

    return data


def process_rekap_absensi_by_id(data):
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

    return data


def get_rekap_absensi(start_date, end_date):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT 
                    k.id_karyawan,
                    k.nama_lengkap,
                    k.gaji_pokok,
                    k.tipe,
                    COUNT(CASE WHEN a.status = 'hadir' THEN 1 END) AS jumlah_hadir,
                    COUNT(CASE WHEN a.status = 'izin' THEN 1 END) AS jumlah_izin,
                    COUNT(CASE WHEN a.status = 'sakit' THEN 1 END) AS jumlah_sakit,
                    COUNT(CASE WHEN a.status = 'dinas_luar' THEN 1 END) AS dinas_luar,
                    SUM(a.keterlambatan) AS total_jam_terlambat,
                    SUM(a.kurang_jam) AS total_jam_kurang
                FROM absensi a
                JOIN karyawan k ON a.id_karyawan = k.id_karyawan
                WHERE a.tanggal BETWEEN :start_date AND :end_date
                GROUP BY k.id_karyawan, k.nama_lengkap, k.gaji_pokok, k.tipe
            """)
            result = connection.execute(query, {'start_date': start_date, 'end_date': end_date})
            data = [dict(row) for row in result.mappings()]
            return process_rekap_absensi(data)
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []


def get_rekap_absensi_by_id(start_date, end_date, id_karyawan):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT 
                    k.id_karyawan,
                    k.nama_lengkap,
                    k.gaji_pokok,
                    k.tipe,
                    COUNT(CASE WHEN a.status = 'hadir' THEN 1 END) AS jumlah_hadir,
                    COUNT(CASE WHEN a.status = 'izin' THEN 1 END) AS jumlah_izin,
                    COUNT(CASE WHEN a.status = 'sakit' THEN 1 END) AS jumlah_sakit,
                    COUNT(CASE WHEN a.status = 'dinas_luar' THEN 1 END) AS dinas_luar,
                    SUM(a.keterlambatan) AS total_jam_terlambat,
                    SUM(a.kurang_jam) AS total_jam_kurang
                FROM absensi a
                JOIN karyawan k ON a.id_karyawan = k.id_karyawan
                WHERE a.tanggal BETWEEN :start_date AND :end_date
                AND a.id_karyawan = :id_karyawan
                GROUP BY k.id_karyawan, k.nama_lengkap, k.gaji_pokok, k.tipe
            """)
            result = connection.execute(query, {
                'start_date': start_date,
                'end_date': end_date,
                'id_karyawan': id_karyawan
            })
            row = result.mappings().fetchone()
            return process_rekap_absensi_by_id(dict(row)) if row else None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
