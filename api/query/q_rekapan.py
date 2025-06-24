from datetime import time, date
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection
from ..utils.helpers import daterange, time_to_str, format_jam_menit


def get_libur_nasional(start_date: date, end_date: date):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT tanggal FROM liburnasional
                WHERE tanggal BETWEEN :start_date AND :end_date
            """)
            result = connection.execute(query, {'start_date': start_date, 'end_date': end_date}).mappings()
            return set(row['tanggal'] for row in result)
    except SQLAlchemyError as e:
        print(f"Error: {str(e)}")
        return set()

def get_rekap_absensi(start_date, end_date, libur_nasional):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            # Query utama rekap
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

            # Ambil data absensi hari Minggu dan libur nasional untuk hitung lembur
            lembur_query = text("""
                SELECT 
                    a.id_karyawan,
                    a.tanggal
                FROM absensi a
                WHERE a.tanggal BETWEEN :start_date AND :end_date
            """)
            result_lembur = connection.execute(lembur_query, {
                'start_date': start_date,
                'end_date': end_date
            }).mappings()

            lembur_map = {}
            for row in result_lembur:
                tanggal = row['tanggal']
                if tanggal.weekday() == 6 or tanggal in libur_nasional:
                    id_karyawan = row['id_karyawan']
                    lembur_map[id_karyawan] = lembur_map.get(id_karyawan, 0) + 1

            # Gabungkan hasil
            final_result = []
            for row in result.mappings():
                id_karyawan = row['id_karyawan']
                row_dict = dict(row)
                row_dict['jumlah_lembur'] = lembur_map.get(id_karyawan, 0)
                final_result.append(row_dict)

            return final_result

    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []

def get_detail_absensi_by_karyawan(id_karyawan, start, end):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            # Ambil data absensi
            query = text("""
                SELECT 
                    a.tanggal, a.jam_masuk, a.jam_keluar, a.jam_terlambat, a.jam_kurang,
                    a.total_jam_kerja AS total_jam_masuk, a.lokasi_masuk, a.lokasi_keluar,
                    s.id_status, s.nama_status,
                    k.nama AS nama_karyawan,
                    j.jenis AS jenis_pegawai,
                    t.tipe AS tipe_pegawai
                FROM absensi a
                JOIN karyawan k ON k.id_karyawan = a.id_karyawan
                JOIN statuspresensi s ON s.id_status = a.id_status
                JOIN jeniskaryawan j ON j.id_jenis = k.id_jenis
                JOIN tipekaryawan t ON t.id_tipe = k.id_tipe
                WHERE a.id_karyawan = :id_karyawan
                AND a.tanggal BETWEEN :start AND :end
            """)
            absensi_result = connection.execute(query, {
                'id_karyawan': id_karyawan,
                'start': start,
                'end': end
            }).fetchall()

            absensi_dict = {}
            for row in absensi_result:
                data = dict(row._mapping)
                absensi_dict[row.tanggal] = {
                    'tanggal': row.tanggal.strftime('%Y-%m-%d'),
                    'jam_masuk': time_to_str(data.get('jam_masuk')),
                    'jam_keluar': time_to_str(data.get('jam_keluar')),
                    'jam_terlambat': time_to_str(data.get('jam_terlambat')),
                    'jam_kurang': time_to_str(data.get('jam_kurang')),
                    'total_jam_masuk': time_to_str(data.get('total_jam_masuk')),
                    'lokasi_masuk': data.get('lokasi_masuk'),
                    'lokasi_keluar': data.get('lokasi_keluar'),
                    'id_status': data.get('id_status'),
                    'nama_status': data.get('nama_status'),
                    'nama_karyawan': data.get('nama_karyawan'),
                    'jenis_pegawai': data.get('jenis_pegawai'),
                    'tipe_pegawai': data.get('tipe_pegawai'),
                }
            # Ambil hari libur
            libur_result = connection.execute(text("""
                SELECT tanggal FROM liburnasional WHERE tanggal BETWEEN :start AND :end
            """), {'start': start, 'end': end}).fetchall()
            libur_set = {r.tanggal for r in libur_result}

            # Ambil info karyawan
            karyawan_result = connection.execute(text("""
                SELECT k.nama, j.jenis AS jenis_pegawai, t.tipe AS tipe_pegawai
                FROM karyawan k
                JOIN jeniskaryawan j ON k.id_jenis = j.id_jenis
                JOIN tipekaryawan t ON k.id_tipe = t.id_tipe
                WHERE k.id_karyawan = :id_karyawan
            """), {'id_karyawan': id_karyawan}).fetchone()

            if not karyawan_result:
                return []

            nama_karyawan = karyawan_result.nama
            jenis_pegawai = karyawan_result.jenis_pegawai
            tipe_pegawai = karyawan_result.tipe_pegawai

            hasil = []
            for tanggal in daterange(start, end):
                tanggal_str = tanggal.strftime('%Y-%m-%d')

                if tanggal in libur_set:
                    status_hari = 'libur nasional'
                elif tanggal.weekday() == 6:
                    status_hari = 'minggu'
                else:
                    status_hari = 'regular'

                if tanggal in absensi_dict:
                    item = absensi_dict[tanggal]
                    item['status_hari'] = status_hari
                    hasil.append(item)
                else:
                    hasil.append({
                        'nama_karyawan': nama_karyawan,
                        'tanggal': tanggal_str,
                        'status_hari': status_hari,
                        'id_status': 0,
                        'nama_status': 'Tidak Hadir',
                        'jenis_pegawai': jenis_pegawai,
                        'tipe_pegawai': tipe_pegawai,
                        'jam_masuk': None,
                        'jam_keluar': None,
                        'jam_terlambat': None,
                        'jam_kurang': None,
                        'total_jam_masuk': None,
                        'lokasi_masuk': None,
                        'lokasi_keluar': None,
                    })
            return {
                'start_date': start.strftime('%Y-%m-%d'),
                'end_date': end.strftime('%Y-%m-%d'),
                'data': hasil
            }
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
    
def get_rekap_person(start_date, end_date, id_karyawan):
    engine = get_connection()
    try:
        with engine.connect() as connection:
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
                AND a.id_karyawan = :id_karyawan
                GROUP BY 
                    k.id_karyawan, k.nama, k.gaji_pokok, 
                    k.id_jenis, jk.jenis, 
                    k.id_tipe, tk.tipe
                ORDER BY k.nama;
            """)
            result = connection.execute(query, {
                'start_date': start_date,
                'end_date': end_date,
                'id_karyawan': id_karyawan
            })
            return [dict(row) for row in result.mappings()]
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []

def get_list_rekapan_person(start_date, end_date, id_karyawan):
    engine = get_connection()
    try:
        with engine.connect() as connection:
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

            data = []
            for row in rows:
                row_dict = dict(row)

                # Konversi jam
                for field in ['jam_masuk', 'jam_keluar']:
                    if isinstance(row_dict[field], time):
                        row_dict[field] = row_dict[field].strftime('%H:%M:%S')

                # Konversi menit ke format jam:menit
                for field in ['jam_terlambat', 'jam_kurang', 'total_jam_kerja']:
                    val = row_dict[field]
                    if isinstance(val, int):
                        row_dict[field] = format_jam_menit(val)

                # Konversi tanggal
                if isinstance(row_dict['tanggal'], date):
                    row_dict['tanggal'] = row_dict['tanggal'].strftime('%d-%m-%Y')
                data.append(row_dict)
            return data
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
