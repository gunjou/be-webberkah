from datetime import date, time, timedelta, datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection, get_wita


def insert_pengajuan_perizinan(data):
    """
    Insert pengajuan izin/sakit/izin setengah hari baru.
    """
    engine = get_connection()
    try:
        with engine.begin() as connection:
            query = text("""
                INSERT INTO izin (
                    id_karyawan, id_jenis, keterangan,tgl_mulai, tgl_selesai, path_lampiran, status_izin,
                    status, created_at, updated_at, potong_cuti
                )
                VALUES (
                    :id_karyawan, :id_jenis, :keterangan, :tgl_mulai, :tgl_selesai, :path_lampiran, 'pending', 
                    1, :timestamp_wita, :timestamp_wita, :potong_cuti
                )
            """)
            connection.execute(query, {
                "id_karyawan": data["id_karyawan"],
                "id_jenis": data["id_jenis"],
                "keterangan": data["keterangan"],
                "tgl_mulai": data["tgl_mulai"],
                "tgl_selesai": data["tgl_selesai"],
                "path_lampiran": data.get("path_lampiran"),
                "potong_cuti": data.get("potong_cuti", 0),   # default 0
                "timestamp_wita": get_wita(),
            })
            return True
    except SQLAlchemyError as e:
        print("DB ERROR (insert_pengajuan_perizinan):", str(e))
        return None
    
def get_daftar_perizinan(status_izin=None, id_karyawan=None, tanggal=None,
                         start_date=None, end_date=None):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = """
                SELECT 
                    i.id_izin, i.id_karyawan, k.nama AS nama_karyawan, i.id_jenis, i.keterangan,
                    i.tgl_mulai, i.tgl_selesai, i.path_lampiran, i.status_izin, i.alasan_penolakan, i.potong_cuti,
                    i.created_at, i.updated_at
                FROM izin i
                JOIN karyawan k ON i.id_karyawan = k.id_karyawan
                WHERE i.status = 1 AND k.status = 1
            """

            params = {}

            if status_izin:
                query += " AND i.status_izin = :status_izin"
                params["status_izin"] = status_izin

            if id_karyawan:
                query += " AND i.id_karyawan = :id_karyawan"
                params["id_karyawan"] = int(id_karyawan)

            # === FILTER: tanggal tunggal ===
            if tanggal:
                query += " AND :tanggal BETWEEN i.tgl_mulai AND i.tgl_selesai"
                params["tanggal"] = tanggal

            # === FILTER: rentang tanggal ===
            if start_date and end_date:
                query += " AND i.tgl_mulai BETWEEN :start_date AND :end_date"
                params["start_date"] = start_date
                params["end_date"] = end_date

            query += " ORDER BY i.created_at DESC"

            rows = connection.execute(text(query), params).mappings().fetchall()

            data = []
            for row in rows:
                record = {}
                for key, value in row.items():
                    record[key] = value.isoformat() if isinstance(value, (date, datetime)) else value
                data.append(record)

            return data

    except SQLAlchemyError as e:
        print("DB ERROR (get_daftar_perizinan):", e)
        return None
    
def get_izin_by_karyawan(id_karyawan, tanggal=None):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = """
                SELECT 
                    i.id_izin, i.id_karyawan, k.nama AS nama_karyawan, i.id_jenis, i.keterangan,
                    i.tgl_mulai, i.tgl_selesai, i.path_lampiran, i.status_izin, i.alasan_penolakan, i.potong_cuti, 
                    i.created_at, i.updated_at
                FROM izin i
                JOIN karyawan k ON i.id_karyawan = k.id_karyawan
                WHERE i.status = 1 AND k.status = 1
                AND i.id_karyawan = :id_karyawan
            """

            params = {"id_karyawan": id_karyawan}

            # Filter per hari (tanggal harus berada pada rentang izin)
            if tanggal:
                query += " AND :tanggal BETWEEN i.tgl_mulai AND i.tgl_selesai"
                params["tanggal"] = tanggal

            query += " ORDER BY i.created_at DESC"

            rows = connection.execute(text(query), params).mappings().fetchall()

            data = []
            for row in rows:
                item = {}
                for key, value in row.items():
                    if isinstance(value, (datetime, date)):
                        item[key] = value.isoformat()
                    else:
                        item[key] = value
                data.append(item)

            return data

    except SQLAlchemyError as e:
        print("DB ERROR (get_izin_by_karyawan):", e)
        return None

def approve_izin(id_izin):
    """
    Update status perizinan menjadi approved.
    """
    engine = get_connection()
    try:
        with engine.begin() as connection:
            query = text("""
                UPDATE izin
                SET 
                    status_izin = 'approved',
                    alasan_penolakan = NULL,
                    updated_at = :updated_at
                WHERE id_izin = :id_izin
                  AND status = 1
            """)

            result = connection.execute(query, {
                "id_izin": id_izin,
                "updated_at": get_wita()
            })

            return result.rowcount  # 1 jika berhasil, 0 jika tidak ada record

    except SQLAlchemyError as e:
        print("DB ERROR (approve_izin):", e)
        return None
    
def reject_izin(id_izin, alasan_penolakan):
    """
    Menolak permohonan izin + menyimpan alasan.
    """
    engine = get_connection()
    try:
        with engine.begin() as connection:
            query = text("""
                UPDATE izin
                SET 
                    status_izin = 'rejected',
                    alasan_penolakan = :alasan_penolakan,
                    updated_at = :updated_at
                WHERE id_izin = :id_izin
                  AND status = 1
            """)

            result = connection.execute(query, {
                "id_izin": id_izin,
                "alasan_penolakan": alasan_penolakan,
                "updated_at": get_wita()
            })

            return result.rowcount  # 1 = success, 0 = not found

    except SQLAlchemyError as e:
        print("DB ERROR (reject_izin):", e)
        return None

def check_izin_owner(id_izin):
    """
    Mengambil id_karyawan pemilik izin tertentu.
    """
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT id_karyawan 
                FROM izin
                WHERE id_izin = :id_izin AND status = 1
            """)

            row = connection.execute(query, {"id_izin": id_izin}).fetchone()
            return row[0] if row else None

    except SQLAlchemyError as e:
        print("DB ERROR (check_izin_owner):", e)
        return None

def soft_delete_izin(id_izin):
    """
    Soft delete izin (status = 0).
    """
    engine = get_connection()
    try:
        with engine.begin() as connection:
            query = text("""
                UPDATE izin
                SET 
                    status = 0,
                    updated_at = :updated_at
                WHERE id_izin = :id_izin
            """)

            result = connection.execute(query, {
                "id_izin": id_izin,
                "updated_at": get_wita()
            })

            return result.rowcount  # 1 jika berhasil, 0 jika tidak ada record

    except SQLAlchemyError as e:
        print("DB ERROR (soft_delete_izin):", e)
        return None
