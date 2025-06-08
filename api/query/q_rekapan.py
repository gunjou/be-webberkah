from datetime import time
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection

connection = get_connection().connect()

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

def get_rekap_absensi(start_date, end_date):
    try:
        query = text("""
            SELECT 
                k.id_karyawan,
                k.nama,
                k.gaji_pokok,
                k.id_jenis,
                jk.jenis,
                k.id_tipe,
                tk.tipe,
                SUM(a.jam_terlambat) AS total_jam_terlambat,
                SUM(a.jam_kurang) AS total_jam_kurang,
                12480 AS total_jam_kerja_normal,
                SUM(a.total_jam_kerja) AS total_jam_kerja,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Hadir') AS jumlah_hadir,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Tidak Hadir') AS jumlah_alpha,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Setengah Hari') AS jumlah_setengah_hari,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Izin') AS jumlah_izin,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Sakit') AS jumlah_sakit,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Dinas Luar') AS dinas_luar
            FROM absensi a
            JOIN karyawan k ON a.id_karyawan = k.id_karyawan
            LEFT JOIN statuspresensi sp ON a.id_status = sp.id_status
            LEFT JOIN jeniskaryawan jk ON k.id_jenis = jk.id_jenis
            LEFT JOIN tipekaryawan tk ON k.id_tipe = tk.id_tipe
            WHERE a.tanggal BETWEEN :start_date AND :end_date
            GROUP BY 
                k.id_karyawan, k.nama, k.gaji_pokok, 
                k.id_jenis, jk.jenis, 
                k.id_tipe, tk.tipe
            ORDER BY k.nama;
        """)
        result = connection.execute(query, {'start_date': start_date, 'end_date': end_date})
        return [dict(row) for row in result.mappings()]
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []

def get_list_rekapan_person(start_date, end_date, id_karyawan):
    try:
        query = text("""
            SELECT 
                k.nama,
                s.nama_status,
                t.tipe,
                a.tanggal,
                a.jam_masuk,
                a.jam_keluar,
                a.jam_terlambat,
                a.jam_kurang,
                a.total_jam_kerja,
                a.lokasi_masuk,
                a.lokasi_keluar
            FROM absensi a
            INNER JOIN karyawan k ON k.id_karyawan = a.id_karyawan
            INNER JOIN jeniskaryawan j ON k.id_jenis = j.id_jenis
            INNER JOIN statuspresensi s ON a.id_status = s.id_status
            INNER JOIN tipekaryawan t ON k.id_tipe = t.id_tipe
            WHERE a.id_karyawan = :id_karyawan
            AND a.status = 1
            AND a.tanggal BETWEEN :start_date AND :end_date
        """)
        result = connection.execute(query, {
            'start_date': start_date,
            'end_date': end_date,
            'id_karyawan': id_karyawan
        })
        rows = result.mappings().fetchall()

        for row in rows:
            for field in ['jam_masuk', 'jam_keluar']:
                if isinstance(row[field], time):
                    row[field] = row[field].strftime('%H:%M:%S')

            for field in ['jam_terlambat', 'jam_kurang', 'total_jam_kerja']:
                val = row[field]
                if isinstance(val, int):
                    row[field] = format_jam_menit(val)

        return [dict(row) for row in rows] if rows else []
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
