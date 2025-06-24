from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from datetime import date, datetime, timedelta

from ..utils.config import get_connection


def get_hari_libur():
    engine = get_connection()
    try:
        with engine.connect() as connection:
            # Ambil semua tanggal dari tabel libur nasional
            result = connection.execute(text("""
                SELECT tanggal, keterangan
                FROM liburnasional
                WHERE status = 1
            """)).mappings().fetchall()

            libur_nasional = {row['tanggal']: row['keterangan'] for row in result}

            # Tambahkan hari minggu (dari tahun ini)
            tahun_ini = date.today().year
            tgl = date(tahun_ini, 1, 1)
            akhir_tahun = date(tahun_ini, 12, 31)

            while tgl <= akhir_tahun:
                if tgl.weekday() == 6:  # Minggu = 6
                    libur_nasional.setdefault(tgl, 'Hari Minggu')
                tgl += timedelta(days=1)

            # Urutkan dan ubah ke list of dict
            libur_list = [
                {"tanggal": tgl.isoformat(), "keterangan": keterangan}
                for tgl, keterangan in sorted(libur_nasional.items())
            ]

            return libur_list
    except SQLAlchemyError as e:
        print(f"DB Error: {str(e)}")
        return None

def is_libur(tanggal: str) -> bool:
    try:
        cek_tanggal = datetime.strptime(tanggal, '%Y-%m-%d').date()

        # Cek hari minggu
        if cek_tanggal.weekday() == 6:
            return True

        engine = get_connection()
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT 1 FROM liburnasional
                WHERE tanggal = :tanggal AND status = 1
                LIMIT 1
            """), {"tanggal": cek_tanggal}).scalar()

            return bool(result)
    except ValueError:
        return False
    except SQLAlchemyError as e:
        print(f"DB Error: {str(e)}")
        return False
