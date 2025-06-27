from datetime import date, timedelta
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection


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

def get_rekap_gaji(start_date: date, end_date: date, id_karyawan=None):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            libur_set = get_libur_nasional(start_date, end_date)

            # Hitung hari kerja optimal
            hari_optimal = sum(
                1 for i in range((end_date - start_date).days + 1)
                if (d := start_date + timedelta(days=i)).weekday() != 6 and d not in libur_set
            )

            # Build query dinamis
            query = """
                SELECT 
                    k.id_karyawan, k.nama, k.gaji_pokok, 
                    jk.id_jenis, jk.jenis, 
                    tk.id_tipe, tk.tipe,
                    SUM(a.jam_terlambat) AS total_jam_terlambat,
                    SUM(a.jam_kurang) AS total_jam_kurang,
                    SUM(a.total_jam_kerja) AS total_jam_kerja,
                    COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Hadir') AS jumlah_hadir,
                    COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Izin') AS jumlah_izin,
                    COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Sakit') AS jumlah_sakit
                FROM absensi a
                JOIN karyawan k ON a.id_karyawan = k.id_karyawan
                LEFT JOIN statuspresensi sp ON a.id_status = sp.id_status
                LEFT JOIN jeniskaryawan jk ON k.id_jenis = jk.id_jenis
                LEFT JOIN tipekaryawan tk ON k.id_tipe = tk.id_tipe
                WHERE a.tanggal BETWEEN :start_date AND :end_date
            """
            params = {'start_date': start_date, 'end_date': end_date}

            if id_karyawan:
                query += " AND a.id_karyawan = :id_karyawan"
                params['id_karyawan'] = id_karyawan

            query += """
                GROUP BY k.id_karyawan, k.nama, k.gaji_pokok, jk.id_jenis, jk.jenis, tk.id_tipe, tk.tipe
            """
            rows = connection.execute(text(query), params).mappings().fetchall()

            # Ambil total_bayaran lembur approved
            lembur_query = text("""
                SELECT id_karyawan, SUM(total_bayaran) AS total_bayaran
                FROM lembur
                WHERE tanggal BETWEEN :start_date AND :end_date
                  AND status_lembur = 'approved' AND status = 1
                GROUP BY id_karyawan
            """)
            lembur_map = {
                row['id_karyawan']: row['total_bayaran']
                for row in connection.execute(lembur_query, {'start_date': start_date, 'end_date': end_date}).mappings()
            }

            # Ambil tunjangan kehadiran (checkout sebelum 07:46)
            tunjangan_query = text("""
                SELECT id_karyawan, COUNT(*) AS jumlah
                FROM absensi
                WHERE tanggal BETWEEN :start_date AND :end_date
                  AND jam_masuk < '07:46:00'
                  AND status = 1
                GROUP BY id_karyawan
            """)
            tunjangan_map = {
                row['id_karyawan']: row['jumlah']
                for row in connection.execute(tunjangan_query, {'start_date': start_date, 'end_date': end_date}).mappings()
            }

            result = []
            for row in rows:
                id_karyawan = row['id_karyawan']
                gaji_pokok = row['gaji_pokok']
                gaji_perhari = gaji_pokok / hari_optimal if hari_optimal else 0
                gaji_perjam = gaji_perhari / 8
                gaji_permenit = gaji_perjam / 60

                jumlah_hari_dibayar = min(
                    sum([row['jumlah_hadir'], row['jumlah_izin'], row['jumlah_sakit']]),
                    hari_optimal
                )
                total_upah = round(gaji_perhari * jumlah_hari_dibayar, 2)
                terlambat = row['total_jam_terlambat'] or 0 # helper
                jam_kurang = row['total_jam_kurang'] or 0 # helper
                total_potongan = round(gaji_permenit * (terlambat + jam_kurang), 2)
                total_bayaran_lembur = lembur_map.get(id_karyawan) or 0.0
                tunjangan_kehadiran = (tunjangan_map.get(id_karyawan) or 0) * 10000

                gaji_bersih = total_upah - total_potongan + (total_bayaran_lembur or 0) + (tunjangan_kehadiran or 0)

                result.append({
                    **row,
                    'hari_optimal': hari_optimal,
                    'gaji_perhari': round(gaji_perhari, 2),
                    'gaji_perjam': round(gaji_perjam, 2),
                    'gaji_permenit': round(gaji_permenit, 4),
                    'total_upah': total_upah,
                    'total_potongan': total_potongan,
                    'total_bayaran_lembur': total_bayaran_lembur,
                    'tunjangan_kehadiran': tunjangan_kehadiran,
                    'gaji_bersih': round(gaji_bersih, 2)
                })
            return result
    except SQLAlchemyError as e:
        print(f"DB Error: {str(e)}")
        return []
