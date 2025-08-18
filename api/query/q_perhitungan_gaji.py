from datetime import date, time, timedelta
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection


def get_libur_nasional(start_date: date, end_date: date):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT tanggal FROM liburnasional
                WHERE status = 1 AND tanggal BETWEEN :start_date AND :end_date
            """)
            result = connection.execute(query, {'start_date': start_date, 'end_date': end_date}).mappings()
            return set(row['tanggal'] for row in result)
    except SQLAlchemyError as e:
        print(f"Error: {str(e)}")
        return set()
    
def get_hari_kerja_optimal(bulan, tahun):
    from calendar import monthrange

    start_date = date(tahun, bulan, 1)
    end_date = date(tahun, bulan, monthrange(tahun, bulan)[1])

    # Ambil semua libur nasional dari DB
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT tanggal FROM liburnasional
                WHERE status = 1 AND tanggal BETWEEN :start AND :end
            """)
            libur_rows = connection.execute(query, {'start': start_date, 'end': end_date}).fetchall()
            libur_set = {row[0] for row in libur_rows}
    except SQLAlchemyError as e:
        print(f"Error: {str(e)}")
        return set()
    
    hari_kerja = 0
    for i in range((end_date - start_date).days + 1):
        current_day = start_date + timedelta(days=i)
        if current_day.weekday() != 6 and current_day not in libur_set:
            hari_kerja += 1
    return hari_kerja

def get_rekap_gaji(start_date: date = None, end_date: date = None, tanggal: date = None, id_karyawan=None):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            # Validasi penggunaan argumen
            if tanggal and (start_date or end_date):
                raise ValueError("Gunakan salah satu dari 'tanggal' atau 'start_date' & 'end_date'")

            today = date.today()

            if tanggal:
                start_date = end_date = tanggal
            elif not start_date or not end_date:
                start_date = date(today.year, today.month, 1)
                end_date = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

            libur_set = get_libur_nasional(start_date, end_date)

            # hitung sisa hari kerja optimal dari hari ini s.d. akhir bulan
            sisa_hari_kerja = 0
            for i in range((end_date - today).days + 1):
                current_day = today + timedelta(days=i)
                if current_day.weekday() != 6 and current_day not in libur_set:  # exclude minggu + libur nasional
                    sisa_hari_kerja += 1

            # Hitung hari kerja optimal
            hari_optimal = sum(
                1 for i in range((end_date - start_date).days + 1)
                if (d := start_date + timedelta(days=i)).weekday() != 6 and d not in libur_set
            )

            query = """
                SELECT 
                    k.id_karyawan, k.nip, k.nama, k.gaji_pokok, k.bank, k.no_rekening,
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
                LEFT JOIN liburnasional ln ON a.tanggal = ln.tanggal
                WHERE a.tanggal BETWEEN :start_date AND :end_date AND a.status = 1 AND k.status = 1 AND EXTRACT(DOW FROM a.tanggal) != 0 AND ln.tanggal IS NULL
            """
            params = {'start_date': start_date, 'end_date': end_date}

            if id_karyawan:
                query += " AND a.id_karyawan = :id_karyawan"
                params['id_karyawan'] = id_karyawan

            query += """
                GROUP BY k.id_karyawan, k.nama, k.gaji_pokok, jk.id_jenis, jk.jenis, tk.id_tipe, tk.tipe
            """

            rows = connection.execute(text(query), params).mappings().fetchall()

            # Data lembur
            lembur_query = text("""
                SELECT id_karyawan,
                       COUNT(*) AS total_lembur,
                       SUM(menit_lembur) AS total_menit,
                       SUM(total_bayaran) AS total_bayaran
                FROM lembur
                WHERE tanggal BETWEEN :start_date AND :end_date
                  AND status_lembur = 'approved' AND status = 1
                GROUP BY id_karyawan
            """)
            lembur_map = {
                row['id_karyawan']: row
                for row in connection.execute(lembur_query, params).mappings()
            }

            # Tunjangan kehadiran (masuk sebelum 07:46)
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
                for row in connection.execute(tunjangan_query, params).mappings()
            }

            result = []
            for row in rows:
                id_karyawan = row['id_karyawan']
                gaji_pokok = row['gaji_pokok']
                tipe_id = row['id_tipe']

                hadir = row['jumlah_hadir'] or 0
                izin = row['jumlah_izin'] or 0
                sakit = row['jumlah_sakit'] or 0

                if tipe_id == 1:  # Pegawai Tetap
                    # Tetap: gaji pokok dibagi hari optimal
                    gaji_perhari = gaji_pokok / hari_optimal if hari_optimal else 0
                    jumlah_hari_dibayar = min(hadir + izin + sakit, hari_optimal)
                else:  # Pegawai Tidak Tetap
                    # Tidak tetap: gaji pokok = gaji per hari langsung dari DB
                    gaji_perhari = gaji_pokok
                    jumlah_hari_dibayar = hadir  # hanya hadir yang dihitung

                gaji_kotor = round(gaji_perhari * jumlah_hari_dibayar)

                gaji_perjam = gaji_perhari / 8
                gaji_permenit = gaji_perjam / 60

                terlambat = row['total_jam_terlambat'] or 0
                jam_kurang = row['total_jam_kurang'] or 0
                total_potongan = round(gaji_permenit * (terlambat + jam_kurang))

                lembur_data = lembur_map.get(id_karyawan, {})
                total_lembur = lembur_data.get('total_lembur') or 0
                total_menit_lembur = lembur_data.get('total_menit') or 0
                total_bayaran_lembur = lembur_data.get('total_bayaran') or 0.0

                tunjangan_kehadiran = (tunjangan_map.get(id_karyawan) or 0) * 10000

                total_jam_kerja = row['total_jam_kerja'] or 0
                total_jam_kerja -= 60 * hadir

                gaji_bersih_tanpa_lembur = 0
                gaji_bersih = 0

                if total_jam_kerja > 0:
                    # Ada jam kerja (normal case)
                    gaji_bersih_tanpa_lembur = round(gaji_kotor - total_potongan + tunjangan_kehadiran)
                    gaji_bersih = round(gaji_bersih_tanpa_lembur + total_bayaran_lembur)

                elif total_lembur > 0:
                    # Tidak ada jam kerja tapi ada lembur
                    gaji_bersih = round(gaji_kotor - total_potongan + tunjangan_kehadiran + total_bayaran_lembur)


                result.append({
                    'id_karyawan': id_karyawan,
                    'nip': row['nip'],
                    'nama': row['nama'],
                    'id_tipe': tipe_id,
                    'tipe': row['tipe'],
                    'bank': row['bank'],
                    'no_rekening': row['no_rekening'],
                    'periode_awal': start_date.strftime('%d %b %Y'),
                    'periode_akhir': end_date.strftime('%d %b %Y'),
                    'jumlah_hadir': hadir,
                    'jumlah_izin': izin,
                    'jumlah_sakit': sakit,
                    'jumlah_alpha': max(0, hari_optimal - (sisa_hari_kerja + hadir + izin + sakit)),
                    'total_jam_kerja': total_jam_kerja,
                    'jam_normal': hari_optimal * 480,
                    'jam_terlambat': terlambat,
                    'jam_kurang': jam_kurang,
                    'gaji_pokok': round(gaji_pokok),
                    'potongan': total_potongan,
                    'tunjangan_kehadiran': tunjangan_kehadiran,
                    'total_lembur': total_lembur,
                    'total_menit_lembur': total_menit_lembur,
                    'gaji_kotor': gaji_kotor,
                    'gaji_bersih_tanpa_lembur': gaji_bersih_tanpa_lembur,
                    'total_bayaran_lembur': round(total_bayaran_lembur),
                    'gaji_bersih': gaji_bersih
                })
            return result
    except SQLAlchemyError as e:
        print(f"DB Error: {str(e)}")
        return []

# query/q_perhitungan_gaji.py
def get_gaji_harian(tanggal: date, id_karyawan: int):
    engine = get_connection()
    try:
        with engine.connect() as conn:
            # Ambil data absensi dan info karyawan
            result = conn.execute(text("""
                SELECT 
                    a.id_karyawan, k.nama, tk.id_tipe, tk.tipe AS tipe_karyawan,
                    k.gaji_pokok,
                    a.jam_masuk, a.jam_keluar,
                    a.jam_terlambat, a.jam_kurang,
                    a.total_jam_kerja
                FROM absensi a
                JOIN karyawan k ON a.id_karyawan = k.id_karyawan
                LEFT JOIN tipekaryawan tk ON k.id_tipe = tk.id_tipe
                WHERE a.tanggal = :tanggal AND a.status = 1 AND a.id_karyawan = :id_karyawan
                LIMIT 1
            """), {'tanggal': tanggal, 'id_karyawan': id_karyawan}).mappings().fetchone()

            if not result:
                return None  # Tidak ada data

            gaji_pokok = result['gaji_pokok']
            jam_terlambat = result['jam_terlambat'] or 0
            jam_kurang = result['jam_kurang'] or 0
            total_jam_kerja = result['total_jam_kerja'] or 0
            if total_jam_kerja >= 300:
                total_jam_kerja -= 60
            id_tipe = result['id_tipe']

            # Hitung gaji harian berdasarkan tipe pegawai
            if id_tipe == 1:  # Pegawai Tetap
                hari_optimal = get_hari_kerja_optimal(tanggal.month, tanggal.year)
                if hari_optimal == 0:
                    return {'status': 'Tidak ada hari kerja di bulan ini'}, 400
                gaji_perhari = gaji_pokok / hari_optimal
            else:  # Pegawai Tidak Tetap
                gaji_perhari = gaji_pokok  # Pegawai Tidak Tetap langsung gaji harian

            # Hitung gaji per menit
            gaji_permenit = gaji_perhari / 8 / 60
            potongan = round(gaji_permenit * (jam_terlambat + jam_kurang), 2)

            # Tunjangan kehadiran jika masuk sebelum 07:46
            tunjangan_kehadiran = 0
            if result['jam_masuk'] and result['jam_masuk'] < time(7, 46):
                tunjangan_kehadiran = 10000

            # Upah bersih jika sudah check out (total jam kerja > 0)
            upah_bersih = None
            if total_jam_kerja > 0:
                upah_bersih = round(gaji_perhari - potongan + tunjangan_kehadiran, 2)

            return {
                'id_karyawan': result['id_karyawan'],
                'nama': result['nama'],
                'id_tipe': id_tipe,
                'tipe_karyawan': result['tipe_karyawan'],
                'jam_masuk': result['jam_masuk'].strftime('%H:%M') if result['jam_masuk'] else None,
                'jam_keluar': result['jam_keluar'].strftime('%H:%M') if result['jam_keluar'] else None,
                'jam_terlambat': jam_terlambat,
                'jam_kurang': jam_kurang,
                'total_jam_kerja': total_jam_kerja,
                'gaji_permenit': round(gaji_permenit, 4),
                'gaji_harian': round(gaji_perhari, 2),  # <<-- Tambahan field yang diminta
                'potongan': potongan,
                'tunjangan_kehadiran': tunjangan_kehadiran,
                'upah_bersih': upah_bersih
            }

    except SQLAlchemyError as e:
        print(f"DB Error (gaji harian): {str(e)}")
        return None
