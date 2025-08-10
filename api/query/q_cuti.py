from datetime import date, datetime, timedelta
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection, get_wita


def get_kuota_cuti_pegawai(id_karyawan):
    """
    Menghitung sisa kuota cuti tahunan pegawai.
    """
    engine = get_connection()
    tahun_sekarang = datetime.now().year
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COALESCE(SUM(potong_cuti), 0) AS total_cuti_terpakai
                FROM izin
                WHERE id_karyawan = :id_karyawan
                  AND EXTRACT(YEAR FROM tgl_mulai) = :tahun
                  AND status = 1 -- aktif
                  AND status_izin = 'approved (-cuti)'
            """), {"id_karyawan": id_karyawan, "tahun": tahun_sekarang}).fetchone()

            total_cuti_terpakai = result.total_cuti_terpakai if result else 0
            kuota_tahunan = 12
            sisa_kuota = kuota_tahunan - total_cuti_terpakai

            return {
                "id_karyawan": id_karyawan,
                "tahun": tahun_sekarang,
                "kuota_tahunan": kuota_tahunan,
                "cuti_terpakai": total_cuti_terpakai,
                "sisa_kuota": sisa_kuota if sisa_kuota >= 0 else 0
            }
        
    except SQLAlchemyError as e:
        print(f"[ERROR] get_kuota_cuti_pegawai: {e}")
        return None
    
def get_kuota_cuti_semua():
    """
    Menghitung sisa kuota cuti tahunan untuk semua karyawan.
    """
    engine = get_connection()
    tahun_sekarang = datetime.now().year
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT k.id_karyawan, k.nama,
                       COALESCE(SUM(i.potong_cuti), 0) AS cuti_terpakai,
                       12 AS kuota_tahunan,
                       (12 - COALESCE(SUM(i.potong_cuti), 0)) AS sisa_kuota
                FROM karyawan k
                LEFT JOIN izin i
                  ON k.id_karyawan = i.id_karyawan
                  AND EXTRACT(YEAR FROM i.tgl_mulai) = :tahun
                  AND i.status = 1
                  AND i.status_izin = 'approved (-cuti)'
                WHERE k.status = 1
                GROUP BY k.id_karyawan, k.nama
                ORDER BY k.nama
            """), {"tahun": tahun_sekarang}).mappings().all()

            return [dict(row) for row in result]
        
    except SQLAlchemyError as e:
        print(f"[ERROR] get_kuota_cuti_semua: {e}")
        return None
