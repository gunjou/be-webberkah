from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from ..utils.config import get_connection, get_wita, get_timezone


def is_wfh_allowed(id_karyawan):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT status FROM wfh_karyawan WHERE id_karyawan = :id_karyawan AND status = 1"),
                {"id_karyawan": id_karyawan}
            ).fetchone()
            return result is not None  # True jika ada data aktif
    except SQLAlchemyError as e:
        print(f"Error checking WFH status: {str(e)}")
        return False
    
def get_jenis_karyawan(id_karyawan):
    engine = get_connection()
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT id_jenis FROM karyawan WHERE id_karyawan = :id_karyawan AND status = 1"),
            {"id_karyawan": id_karyawan}
        ).fetchone()
        return result[0] if result else None
    
def add_checkin(id_karyawan, tanggal, jam_masuk, lokasi_absensi, jam_terlambat_input):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # Cek apakah hari libur nasional
            result_libur = connection.execute(
                text("""
                    SELECT 1 FROM liburnasional 
                    WHERE tanggal = :tanggal AND status = 1
                    LIMIT 1
                """),
                {'tanggal': tanggal}
            ).scalar()

            # Cek apakah hari minggu atau tanggal libur
            is_libur = tanggal.weekday() == 6 or result_libur is not None

            jam_terlambat = None if is_libur else jam_terlambat_input

            # Masukkan absensi
            result = connection.execute(
                text("""
                    INSERT INTO Absensi (
                        id_karyawan, tanggal, jam_masuk, jam_keluar, 
                        lokasi_masuk, lokasi_keluar, jam_terlambat, 
                        created_at, updated_at, status, id_status
                    ) 
                    VALUES (
                        :id_karyawan, :tanggal, :jam_masuk, NULL, 
                        :lokasi_masuk, NULL, :jam_terlambat, 
                        :timestamp_wita, :timestamp_wita, 1, 1
                    )
                    RETURNING id_absensi
                """),
                {
                    "id_karyawan": id_karyawan,
                    "tanggal": tanggal,
                    "jam_masuk": jam_masuk,
                    "lokasi_masuk": lokasi_absensi,
                    "jam_terlambat": jam_terlambat,
                    "timestamp_wita": get_wita()
                }
            )
            return result.scalar()
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def update_checkout(id_karyawan, tanggal, jam_keluar, lokasi_absensi, jam_kurang_input, total_jam_kerja):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # Cek apakah hari libur nasional
            result_libur = connection.execute(
                text("""
                    SELECT 1 FROM liburnasional 
                    WHERE tanggal = :tanggal AND status = 1
                    LIMIT 1
                """),
                {'tanggal': tanggal}
            ).scalar()

            # Cek apakah hari minggu atau tanggal libur
            is_libur = tanggal.weekday() == 6 or result_libur is not None

            jam_kurang = None if is_libur else jam_kurang_input

            # Masukkan absensi
            result = connection.execute(
                text("""
                    UPDATE Absensi 
                    SET jam_keluar = :jam_keluar, 
                        lokasi_keluar = :lokasi_keluar, 
                        jam_kurang = :jam_kurang, 
                        total_jam_kerja = :total_jam_kerja, 
                        updated_at = :timestamp_wita
                    WHERE id_karyawan = :id_karyawan 
                        AND tanggal = :tanggal 
                        AND jam_keluar IS NULL
                """),
                {
                    "jam_keluar": jam_keluar,
                    "lokasi_keluar": lokasi_absensi,
                    "jam_kurang": jam_kurang,
                    "total_jam_kerja": total_jam_kerja,
                    "timestamp_wita": get_wita(),
                    "id_karyawan": id_karyawan,
                    "tanggal": tanggal
                }
            )
            return result.rowcount  # jumlah baris yang ter-update
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def add_absensi(id_karyawan, tanggal, jam_masuk, jam_keluar, lokasi_masuk, lokasi_keluar, jam_terlambat, jam_kurang, total_jam_kerja):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # Cek apakah hari libur nasional
            result_libur = connection.execute(
                text("""
                    SELECT 1 FROM liburnasional 
                    WHERE tanggal = :tanggal AND status = 1
                    LIMIT 1
                """),
                {'tanggal': tanggal}
            ).scalar()

            # Cek apakah hari minggu atau tanggal libur
            is_libur = datetime.strptime(tanggal, "%Y-%m-%d").weekday() == 6 or result_libur is not None

            jam_terlambat = None if is_libur else jam_terlambat
            jam_kurang = None if is_libur else jam_kurang

            # Masukkan absensi
            connection.execute(
                text("""
                    INSERT INTO Absensi (
                        id_karyawan, tanggal, jam_masuk, jam_keluar, 
                        lokasi_masuk, lokasi_keluar, jam_terlambat,
                        jam_kurang, total_jam_kerja,
                        created_at, updated_at, status, id_status
                    ) 
                    VALUES (
                        :id_karyawan, :tanggal, :jam_masuk, :jam_keluar, 
                        :lokasi_masuk, :lokasi_keluar, :jam_terlambat,
                        :jam_kurang, :total_jam_kerja,
                        :timestamp_wita, :timestamp_wita, 1, 1
                    )
                """),
                {
                    "id_karyawan": id_karyawan,
                    "tanggal": tanggal,
                    "jam_masuk": jam_masuk,
                    "jam_keluar": jam_keluar,
                    "lokasi_masuk": lokasi_masuk,
                    "lokasi_keluar": lokasi_keluar,
                    "jam_terlambat": jam_terlambat,
                    "jam_kurang": jam_kurang,
                    "total_jam_kerja": total_jam_kerja,
                    "timestamp_wita": get_wita()
                }
            )
            return 1
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def delete_checkout(id_absensi):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    UPDATE Absensi
                    SET jam_keluar = NULL, jam_kurang = NULL, lokasi_keluar = NULL, total_jam_kerja = NULL, updated_at = :timestamp_wita
                    WHERE id_absensi = :id_absensi
                    AND jam_keluar IS NOT NULL
                    AND status = 1
                """),
                {'id_absensi': id_absensi, 'timestamp_wita': get_wita()}
            )
            return result.rowcount > 0  # True jika ada baris yang diupdate
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def get_check_presensi(id_karyawan):
    engine = get_connection()
    today, _ = get_timezone()  # Mendapatkan tanggal hari ini
    # print(today)
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT id_absensi, tanggal, jam_masuk, jam_keluar, lokasi_masuk, lokasi_keluar, jam_terlambat
                    FROM Absensi 
                    WHERE id_karyawan = :id_karyawan
                    AND tanggal = :today
                    AND status = 1
                    ORDER BY jam_masuk DESC
                    LIMIT 1;
                """),
                {
                    "id_karyawan": id_karyawan,
                    "today": today
                }
            ).mappings().fetchone()  # Mengambil satu record sebagai dictionary

            if result is None:
                return None

            return dict(result)

    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None jika terjadi kesalahan
    
# query/absensi.py
def get_history_absensi_harian(id_karyawan, tanggal):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query_result = connection.execute(
                text("""
                    SELECT a.id_karyawan, k.nama, s.id_status, t.id_tipe, t.tipe,
                           a.jam_masuk, a.jam_keluar, a.lokasi_masuk, a.lokasi_keluar,
                           a.jam_terlambat, a.jam_kurang AS jam_bolos, a.total_jam_kerja
                    FROM Absensi a 
                    INNER JOIN Karyawan k ON k.id_karyawan = a.id_karyawan 
                    INNER JOIN StatusPresensi s ON a.id_status = s.id_status 
                    INNER JOIN TipeKaryawan t ON k.id_tipe = t.id_tipe 
                    WHERE a.id_karyawan = :id_karyawan AND a.status = 1 AND a.tanggal = :tanggal;
                """),
                {"tanggal": tanggal, "id_karyawan": id_karyawan}
            )

            data = [dict(row) for row in query_result.mappings()]
            result = []

            for row in data:
                result.append({
                    'id_karyawan': row['id_karyawan'],
                    'nama': row['nama'],
                    'id_status': row['id_status'],
                    'id_tipe': row['id_tipe'],
                    'tipe': row['tipe'],
                    'jam_masuk': row['jam_masuk'].strftime('%H:%M') if row['jam_masuk'] else None,
                    'jam_keluar': row['jam_keluar'].strftime('%H:%M') if row['jam_keluar'] else None,
                    'lokasi_masuk': row['lokasi_masuk'],
                    'lokasi_keluar': row['lokasi_keluar'],
                    'jam_terlambat': row['jam_terlambat'] or None,
                    'jam_bolos': row['jam_bolos'] or None,
                    'total_jam_kerja': row['total_jam_kerja'] or 0,
                })
            return result
    except SQLAlchemyError as e:
        print(f"[ERROR] Gagal ambil absensi harian: {str(e)}")
        return []

def query_absensi_harian_admin(tanggal):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT a.id_absensi, a.id_karyawan, k.nama, k.id_jenis, j.jenis, a.tanggal, a.jam_masuk, a.jam_keluar, 
                    a.jam_terlambat, a.jam_kurang, a.total_jam_kerja, a.lokasi_masuk, a.lokasi_keluar, s.id_status AS id_presensi, 
                    s.nama_status AS status_presensi  
                    FROM Absensi a 
                    INNER JOIN Karyawan k ON k.id_karyawan = a.id_karyawan 
                    INNER JOIN Jeniskaryawan j ON k.id_jenis = j.id_jenis 
                    INNER JOIN StatusPresensi s ON a.id_status = s.id_status 
                    WHERE a.status = 1 AND a.id_status = 1 AND a.tanggal = :tanggal;
                """),
                {"tanggal": tanggal}
            )
            absensi_list = [dict(row) for row in result.mappings()]
            return [{
                'id': index + 1,
                'id_absensi': row['id_absensi'],
                'id_karyawan': row['id_karyawan'],
                'nama': row['nama'],
                'id_jenis': row['id_jenis'],
                'jenis': row['jenis'],
                'tanggal': row['tanggal'].strftime("%d-%m-%Y"),
                'jam_masuk': row['jam_masuk'].strftime('%H:%M') if row['jam_masuk'] else None,
                'jam_keluar': row['jam_keluar'].strftime('%H:%M') if row['jam_keluar'] else None,
                'jam_terlambat': row['jam_terlambat'],
                'jam_kurang': row['jam_kurang'],
                'total_jam_kerja': row['total_jam_kerja'],
                'lokasi_masuk': row['lokasi_masuk'],
                'lokasi_keluar': row['lokasi_keluar'],
                'id_presensi': row['id_presensi'],
                'status_presensi': row['status_presensi'],
                'status_absen': (
                    'Belum Check-in' if row['jam_masuk'] is None else
                    'Belum Check-out' if row['jam_keluar'] is None else
                    'Selesai bekerja'
                )
            } for index, row in enumerate(absensi_list)]
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
    
def query_absensi_tidak_hadir(tanggal):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT k.id_karyawan, k.nama, k.id_jenis, j.jenis, :tanggal AS tanggal
                    FROM Karyawan k
                    JOIN JenisKaryawan j ON k.id_jenis = j.id_jenis
                    LEFT JOIN Absensi a ON k.id_karyawan = a.id_karyawan AND a.tanggal = :tanggal
                    WHERE k.status = 1 AND a.id_absensi IS NULL
                """),
                {"tanggal": tanggal}
            )

            absensi_list = [dict(row) for row in result.mappings()]

            return [{
                "id": index + 1,
                "id_karyawan": row["id_karyawan"],
                "nama": row["nama"],
                "id_jenis": row["id_jenis"],
                "jenis": row["jenis"],
                "tanggal": row["tanggal"].strftime("%d-%m-%Y"),
                "status_absen": "Tanpa Keterangan"
            } for index, row in enumerate(absensi_list)]

    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
    
def query_absensi_izin_sakit(tanggal, id_karyawan=None):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = """
                SELECT k.id_karyawan, k.nama, k.id_jenis, j.jenis, a.id_status, sp.nama_status, :tanggal AS tanggal
                FROM absensi a
                INNER JOIN statuspresensi sp ON a.id_status = sp.id_status
                LEFT JOIN karyawan k ON a.id_karyawan = k.id_karyawan AND a.tanggal = :tanggal
                INNER JOIN JenisKaryawan j ON k.id_jenis = j.id_jenis
                WHERE k.status = 1 AND a.id_status IN (3, 4)
            """

            params = {"tanggal": tanggal}

            if id_karyawan:
                query += " AND k.id_karyawan = :id_karyawan"
                params["id_karyawan"] = id_karyawan

            result = connection.execute(text(query), params)
            absensi_list = [dict(row) for row in result.mappings()]

            return [{
                "id": index + 1,
                "id_karyawan": row["id_karyawan"],
                "nama": row["nama"],
                "id_status": row["id_status"],
                "status_absen": row["nama_status"],
                "id_jenis": row["id_jenis"],
                "jenis": row["jenis"],
                "tanggal": row["tanggal"].strftime("%d-%m-%Y"),
            } for index, row in enumerate(absensi_list)]

    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []

def update_absensi_by_id(id_absensi, jam_masuk, jam_keluar, jam_terlambat, jam_kurang, total_jam_kerja, lokasi_masuk, lokasi_keluar):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            # Ambil tanggal dari absensi
            absensi_data = connection.execute(
                text("""
                    SELECT tanggal FROM absensi
                    WHERE id_absensi = :id_absensi AND status = 1
                    LIMIT 1
                """),
                {'id_absensi': id_absensi}
            ).mappings().fetchone()

            if not absensi_data:
                print(f"Tanggal tidak ditemukan untuk id_absensi {id_absensi}")
                return None

            tanggal = absensi_data['tanggal']

            # Cek apakah hari libur nasional
            result_libur = connection.execute(
                text("""
                    SELECT 1 FROM liburnasional 
                    WHERE tanggal = :tanggal AND status = 1
                    LIMIT 1
                """),
                {'tanggal': tanggal}
            ).scalar()

            # Cek apakah hari Minggu atau libur nasional
            is_libur = tanggal.weekday() == 6 or result_libur is not None

            # Jika hari libur, tidak dihitung jam terlambat
            jam_terlambat = None if is_libur else jam_terlambat

            if jam_keluar:
                query = text("""
                    UPDATE absensi
                    SET jam_masuk = :jam_masuk,
                        jam_keluar = :jam_keluar,
                        jam_terlambat = :jam_terlambat,
                        total_jam_kerja = :total_jam_kerja,
                        jam_kurang = :jam_kurang,
                        lokasi_masuk = :lokasi_masuk,
                        lokasi_keluar = :lokasi_keluar,
                        updated_at = :timestamp_wita
                    WHERE id_absensi = :id_absensi AND status = 1
                """)
                params = {
                    'id_absensi': id_absensi,
                    'jam_masuk': jam_masuk,
                    'jam_keluar': jam_keluar,
                    'jam_terlambat': jam_terlambat,
                    'total_jam_kerja': total_jam_kerja,
                    'jam_kurang': jam_kurang,
                    'lokasi_masuk': lokasi_masuk,
                    'lokasi_keluar': lokasi_keluar,
                    'timestamp_wita': get_wita()
                }
            else:
                query = text("""
                    UPDATE absensi
                    SET jam_masuk = :jam_masuk,
                        jam_terlambat = :jam_terlambat,
                        jam_keluar = NULL,
                        jam_kurang = NULL,
                        total_jam_kerja = NULL,
                        lokasi_keluar = NULL,
                        lokasi_masuk = :lokasi_masuk,
                        updated_at = :timestamp_wita
                    WHERE id_absensi = :id_absensi AND status = 1
                """)
                params = {
                    'id_absensi': id_absensi,
                    'jam_masuk': jam_masuk,
                    'jam_terlambat': jam_terlambat,
                    'lokasi_masuk': lokasi_masuk,
                    'timestamp_wita': get_wita()
                }

            result = connection.execute(query, params)
            return result.rowcount
    except SQLAlchemyError as e:
        print(f"Update Absensi Error: {str(e)}")
        return None

def remove_absensi(id_absensi):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("UPDATE Absensi SET status = 0, updated_at = :timestamp_wita WHERE id_absensi = :id_absensi AND status = 1"),
                {"id_absensi": id_absensi, "timestamp_wita": get_wita()}
            )
            return result.rowcount
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
