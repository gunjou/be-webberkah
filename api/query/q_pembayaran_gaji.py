from datetime import date
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection
from .q_perhitungan_gaji import get_rekap_gaji


def cek_detail_sudah_ada(id_karyawan, bulan, tahun, komponen):
    """
    Cek apakah komponen tertentu sudah pernah dibayarkan untuk pegawai pada bulan & tahun tertentu.
    """
    engine = get_connection()
    with engine.connect() as connection:
        query = text("""
            SELECT 1
            FROM pembayaran_gaji pg
            JOIN detail_pembayaran_gaji dpg
              ON pg.id_pembayaran = dpg.id_pembayaran
            WHERE pg.id_karyawan = :id_karyawan
              AND pg.bulan = :bulan
              AND pg.tahun = :tahun
              AND dpg.komponen = :komponen
              AND pg.status = 1
              AND dpg.status = 1
            LIMIT 1
        """)
        result = connection.execute(query, {
            "id_karyawan": id_karyawan,
            "bulan": bulan,
            "tahun": tahun,
            "komponen": komponen
        }).first()
        return True if result else False

def hitung_pembayaran_gaji(start: date, end: date, id_karyawan: int):
    """
    Ambil hasil perhitungan gaji dari q_perhitungan_gaji,
    lalu ekstrak hanya field yang dibutuhkan untuk insert pembayaran_gaji.
    """
    try:
        hasil = get_rekap_gaji(start, end, id_karyawan=id_karyawan)
        if not hasil:
            return None

        data = hasil[0]  # karena id_karyawan spesifik → hanya satu row
        return {
            "id_karyawan": id_karyawan,
            "nama": data["nama"],
            "gaji_bersih": data["gaji_bersih_tanpa_lembur"],
            "tunjangan": data["tunjangan_kehadiran"],
            "lembur": data["total_bayaran_lembur"],
            "total_dibayar": data["gaji_bersih"]
        }
    except SQLAlchemyError as e:
        print(f"Error (hitung_pembayaran_gaji): {str(e)}")
        return None

def insert_detail_pembayaran(id_karyawan, payload):
    """
    Insert detail pembayaran tambahan untuk id_pembayaran yang sudah ada.
    """
    engine = get_connection()
    try:
        with engine.begin() as connection:
            cek_query = text("""
                SELECT id_pembayaran FROM pembayaran_gaji
                WHERE id_karyawan = :id_karyawan AND bulan = :bulan AND tahun = :tahun AND status = 1
                LIMIT 1
            """)
            result = connection.execute(
                cek_query,
                {"id_karyawan": id_karyawan, "bulan": payload["bulan"], "tahun": payload["tahun"]}
            ).mappings().first()
            id_pembayaran = result["id_pembayaran"] if result else None

            if not id_pembayaran:
                # Insert pembayaran_gaji
                query_pembayaran = text("""
                    INSERT INTO pembayaran_gaji (id_karyawan, bulan, tahun, gaji_pokok, tunjangan, lembur, total_dibayar, status_pembayaran)
                    VALUES (:id_karyawan, :bulan, :tahun, :gaji_bersih, :tunjangan, :lembur, :total_dibayar, 'sebagian')
                    RETURNING id_pembayaran
                """)
                result = connection.execute(query_pembayaran, payload).mappings().first()
                id_pembayaran = result["id_pembayaran"]

                # Insert detail pembayaran pertama
                query = text("""
                    INSERT INTO detail_pembayaran_gaji (id_pembayaran, komponen, jumlah, metode, keterangan)
                    VALUES (:id_pembayaran, :komponen, :jumlah, :metode, :keterangan)
                    RETURNING id_detail
                """)
                result = connection.execute(query, {
                    "id_pembayaran": id_pembayaran,
                    "komponen": payload["komponen"],
                    "jumlah": payload["jumlah"],
                    "metode": payload["metode"],
                    "keterangan": payload["keterangan"]
                })
                id_detail = result.scalar()

                return id_detail
            else:
                query = text("""
                    INSERT INTO detail_pembayaran_gaji (id_pembayaran, komponen, jumlah, metode, keterangan)
                    VALUES (:id_pembayaran, :komponen, :jumlah, :metode, :keterangan)
                    RETURNING id_detail
                """)
                result = connection.execute(query, {
                    "id_pembayaran": id_pembayaran,
                    "komponen": payload["komponen"],
                    "jumlah": payload["jumlah"],
                    "metode": payload["metode"],
                    "keterangan": payload["keterangan"]
                })
                id_detail = result.scalar()

                # Update status pembayaran setelah tambah detail
                update_status_pembayaran(connection, id_pembayaran)

                return id_detail
    except SQLAlchemyError as e:
        print(f"Error (insert_detail_pembayaran): {str(e)}")
        return None


def update_status_pembayaran(connection, id_pembayaran):
    """
    Hitung ulang total sudah dibayar dari detail, update status di pembayaran_gaji.
    """
    # Total sudah dibayar
    total_query = text("""
        SELECT SUM(jumlah) as total_terbayar
        FROM detail_pembayaran_gaji
        WHERE id_pembayaran = :id_pembayaran
    """)
    result = connection.execute(total_query, {"id_pembayaran": id_pembayaran}).mappings().first()
    total_terbayar = result["total_terbayar"] or 0

    # Ambil total yang seharusnya dibayar
    pembayaran_query = text("""
        SELECT total_dibayar FROM pembayaran_gaji WHERE id_pembayaran = :id_pembayaran
    """)
    result = connection.execute(pembayaran_query, {"id_pembayaran": id_pembayaran}).mappings().first()
    total_dibayar = result["total_dibayar"]

    # Tentukan status
    status = "lunas" if total_terbayar >= total_dibayar else "sebagian" if total_terbayar > 0 else "belum_dibayar"

    # Update status pembayaran
    update_query = text("""
        UPDATE pembayaran_gaji
        SET status_pembayaran = :status, updated_at = NOW()
        WHERE id_pembayaran = :id_pembayaran
    """)
    connection.execute(update_query, {"status": status, "id_pembayaran": id_pembayaran})


def get_pembayaran_gaji(bulan: int, tahun: int, id_karyawan: int = None):
    """
    Ambil data gabungan pembayaran_gaji + detail_pembayaran_gaji
    dengan filter bulan, tahun, status=1.
    """
    engine = get_connection()
    with engine.connect() as connection:
        query = text("""
            SELECT 
                pg.id_pembayaran,
                pg.id_karyawan,
                pg.bulan,
                pg.tahun,
                pg.gaji_pokok,
                pg.tunjangan,
                pg.lembur,
                pg.total_dibayar,
                pg.status_pembayaran,
                dpg.id_detail,
                dpg.komponen,
                dpg.jumlah,
                dpg.tanggal_bayar,
                dpg.metode,
                dpg.keterangan
            FROM pembayaran_gaji pg
            LEFT JOIN detail_pembayaran_gaji dpg 
                ON pg.id_pembayaran = dpg.id_pembayaran
            WHERE pg.bulan = :bulan
              AND pg.tahun = :tahun
              AND pg.status = 1
              AND dpg.status = 1
              {id_karyawan_filter}
            ORDER BY pg.id_pembayaran, dpg.id_detail
        """.format(
            id_karyawan_filter="AND pg.id_karyawan = :id_karyawan" if id_karyawan else ""
        ))

        params = {"bulan": bulan, "tahun": tahun}
        if id_karyawan:
            params["id_karyawan"] = id_karyawan

        result = connection.execute(query, params).mappings().all()
        return result