from datetime import date, datetime, timedelta
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection, get_wita


def daterange(start_date, end_date):
    """Utility untuk iterasi tanggal"""
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def get_daftar_izin(status_izin=None, id_karyawan=None):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = """
                SELECT i.id_izin, i.id_karyawan, k.nama AS nama_karyawan, j.nama_status, 
                    i.keterangan, i.tgl_mulai, i.tgl_selesai, 
                    i.path_lampiran, i.status_izin, i.alasan_penolakan,
                    i.created_at, i.updated_at
                FROM izin i
                JOIN karyawan k ON i.id_karyawan = k.id_karyawan
                JOIN statuspresensi j ON i.id_jenis = j.id_status
                WHERE i.status = 1
            """
            params = {}

            if status_izin:
                query += " AND i.status_izin = :status_izin"
                params['status_izin'] = status_izin
            if id_karyawan:
                query += " AND i.id_karyawan = :id_karyawan"
                params['id_karyawan'] = int(id_karyawan)

            query += " ORDER BY i.created_at DESC"

            result = connection.execute(text(query), params).mappings().fetchall()

            data = []
            for row in result:
                row_dict = {}
                for key, value in row.items():
                    if isinstance(value, (date, datetime)):
                        row_dict[key] = value.isoformat()
                    else:
                        row_dict[key] = value
                data.append(row_dict)

            return data

    except SQLAlchemyError as e:
        print(f"DB Error: {str(e)}")
        return None

def insert_pengajuan_izin(data):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            query = text("""
                INSERT INTO izin (
                    id_karyawan, id_jenis, keterangan,
                    tgl_mulai, tgl_selesai, path_lampiran,
                    status_izin, status, created_at, updated_at
                ) VALUES (
                    :id_karyawan, :id_jenis, :keterangan,
                    :tgl_mulai, :tgl_selesai, :path_lampiran,
                    'pending', 1, :timestamp_wita, :timestamp_wita
                )
            """)

            connection.execute(query, {
                "id_karyawan": data["id_karyawan"],
                "id_jenis": data["id_jenis"],
                "keterangan": data["keterangan"],
                "tgl_mulai": data["tgl_mulai"],
                "tgl_selesai": data["tgl_selesai"],
                "path_lampiran": data.get("path_lampiran"),  # optional
                "timestamp_wita": get_wita()
            })
            return 1
    except SQLAlchemyError as e:
        print(f"DB Error: {str(e)}")
        return None

def setujui_izin_dan_insert_absensi(id_izin):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # Ambil data izin
            izin_result = connection.execute(text("""
                SELECT * FROM izin WHERE id_izin = :id AND status = 1
            """), {"id": id_izin}).mappings().fetchone()

            if not izin_result:
                return 0

            # Update status izin
            connection.execute(text("""
                UPDATE izin 
                SET status_izin = 'approved', updated_at = :timestamp_wita
                WHERE id_izin = :id
            """), {"id": id_izin, "timestamp_wita": get_wita()})

            # Data untuk absensi
            id_karyawan = izin_result["id_karyawan"]
            id_status = izin_result["id_jenis"]  # 3 = Izin, 4 = Sakit
            tgl_mulai = izin_result["tgl_mulai"]
            tgl_selesai = izin_result["tgl_selesai"]

            # tanggal_mulai = datetime.strptime(tgl_mulai, "%Y-%m-%d").date()
            # tanggal_selesai = datetime.strptime(tgl_selesai, "%Y-%m-%d").date()

            for tanggal in daterange(tgl_mulai, tgl_selesai):
                connection.execute(text("""
                    INSERT INTO absensi (
                        id_karyawan, tanggal, id_status, status,
                        created_at, updated_at
                    ) VALUES (
                        :id_karyawan, :tanggal, :id_status, 1,
                        :timestamp_wita, :timestamp_wita
                    )
                """), {
                    "id_karyawan": id_karyawan,
                    "tanggal": tanggal,
                    "id_status": id_status,
                    "timestamp_wita": get_wita()
                })
            connection.commit()
            return 1
    except SQLAlchemyError as e:
        connection.rollback()
        print(f"DB Error: {str(e)}")
        return None
    
def tolak_izin(id_izin, alasan_penolakan):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            izin = connection.execute(text("""
                SELECT * FROM izin WHERE id_izin = :id AND status = 1
            """), {"id": id_izin}).mappings().fetchone()

            if not izin:
                return 0

            connection.execute(text("""
                UPDATE izin 
                SET status_izin = 'rejected', alasan_penolakan = :alasan, updated_at = :timestamp_wita
                WHERE id_izin = :id
            """), {
                "id": id_izin,
                "alasan": alasan_penolakan,
                "timestamp_wita": get_wita()
            })
            return 1
    except SQLAlchemyError as e:
        print(f"DB Error: {str(e)}")
        return None
