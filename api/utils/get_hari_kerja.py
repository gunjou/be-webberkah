from datetime import date, timedelta
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from ..utils.config import get_connection

def get_hari_kerja_efektif_bulanan(year: int, month: int):
    """
    Mengembalikan LIST tanggal hari kerja efektif (Senin–Sabtu),
    dikurangi libur nasional/internal,
    dengan aturan:
    - Minggu selalu libur
    - Libur di hari Minggu tidak mengurangi tambahan hari
    """

    # 1. Tentukan range bulan
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    # 2. Ambil tanggal libur AKTIF
    engine = get_connection()
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT tanggal
                    FROM liburnasional
                    WHERE status = 1
                      AND tanggal BETWEEN :start_date AND :end_date
                """),
                {"start_date": start_date, "end_date": end_date}
            ).mappings()

            libur_set = {row["tanggal"] for row in result}
    except SQLAlchemyError as e:
        print(f"Error ambil libur nasional: {e}")
        libur_set = set()

    # 3. Bangun list hari kerja efektif
    hari_kerja_efektif = []

    current = start_date
    while current <= end_date:
        weekday = current.weekday()
        # weekday(): 0=Senin ... 5=Sabtu, 6=Minggu

        if weekday == 6:
            # Minggu → skip
            current += timedelta(days=1)
            continue

        if current in libur_set:
            # Libur nasional/internal (jatuh Senin–Sabtu) → skip
            current += timedelta(days=1)
            continue

        # Valid hari kerja
        hari_kerja_efektif.append(current)
        current += timedelta(days=1)

    return hari_kerja_efektif
