from datetime import datetime
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from calendar import monthrange

from ..utils.config import get_connection

def decimal_to_float(row):
    return {
        key: float(value) if isinstance(value, Decimal) else value
        for key, value in row.items()
    }

def get_leaderboard_kerajinan(start_date=None, end_date=None):
    engine = get_connection()
    today = datetime.today().date()

    # Konversi dari string ke date (jika perlu)
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    # Logika fallback tanggal
    if start_date is None and end_date is None:
        # Kasus 1: Default ke tanggal 1 bulan ini s.d hari ini
        start_date = today.replace(day=1)
        end_date = today
    elif start_date is not None and end_date is None:
        # Kasus 2: start_date diberikan, end_date = hari ini
        end_date = today
    elif end_date is not None and start_date is None:
        # Kasus 3: end_date diberikan, start_date = tanggal 1 di bulan end_date
        start_date = end_date.replace(day=1)
    # Kasus 4: keduanya sudah diisi → tidak perlu diubah

    print('start_date: ', start_date)
    print('end_date: ', end_date)
    try:
        with engine.connect() as connection:
            query = text("""
                WITH tanggal_kerja AS (
                    SELECT generate_series(:start_date, :end_date, interval '1 day')::date AS tanggal
                ),
                semua_karyawan AS (
                    SELECT id_karyawan, nama, jk.jenis
                    FROM karyawan k
                    LEFT JOIN jeniskaryawan jk ON k.id_jenis = jk.id_jenis
                    WHERE k.status = 1
                ),
                presensi AS (
                    SELECT
                        a.id_karyawan,
                        a.tanggal,
                        a.id_status,
                        a.jam_masuk,
                        a.jam_terlambat,
                        a.jam_kurang,
                        a.total_jam_kerja,
                        CASE 
                            WHEN a.id_status = 1 AND a.jam_masuk < TIME '07:45'
                            THEN GREATEST(0, EXTRACT(MINUTE FROM (TIME '07:45' - a.jam_masuk)))
                            ELSE 0
                        END AS poin_hari_ini
                    FROM absensi a
                    WHERE a.tanggal BETWEEN :start_date AND :end_date
                ),
                rekap AS (
                    SELECT
                        s.id_karyawan,
                        s.nama,
                        s.jenis,
                        t.tanggal,
                        COALESCE(p.id_status, 0) AS id_status,
                        COALESCE(p.total_jam_kerja, 0) AS total_jam_kerja,
                        COALESCE(p.jam_terlambat, 0) AS jam_terlambat,
                        COALESCE(p.jam_kurang, 0) AS jam_kurang,
                        COALESCE(p.poin_hari_ini, 0) AS poin_hari_ini
                    FROM semua_karyawan s
                    CROSS JOIN tanggal_kerja t
                    LEFT JOIN presensi p ON s.id_karyawan = p.id_karyawan AND t.tanggal = p.tanggal
                )
                SELECT
                    id_karyawan,
                    nama,
                    jenis,
                    COUNT(*) FILTER (WHERE id_status = 1) AS jumlah_hadir,
                    COUNT(*) FILTER (WHERE id_status = 3) AS jumlah_izin,
                    COUNT(*) FILTER (WHERE id_status = 4) AS jumlah_sakit,
                    COUNT(*) FILTER (
                        WHERE id_status = 0
                    ) AS jumlah_alpha,
                    208 AS jam_kerja_normal,
                    SUM(total_jam_kerja/60) AS total_jam_kerja,
                    SUM(jam_terlambat) AS jam_terlambat,
                    SUM(jam_kurang) AS jam_kurang,
                    SUM(poin_hari_ini) AS waktu_lebih,
                    ROUND(
                        CASE 
                            WHEN COUNT(*) FILTER (WHERE id_status = 1) > 0 
                            THEN SUM(poin_hari_ini) / COUNT(*) FILTER (WHERE id_status = 1) 
                            ELSE 0 
                        END, 2
                    ) AS poin
                FROM rekap
                GROUP BY id_karyawan, nama, jenis
                ORDER BY poin DESC;
            """)
            result = connection.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            })
            return [decimal_to_float(dict(row)) for row in result.mappings()]
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
