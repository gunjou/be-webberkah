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
    
def add_checkin(id_karyawan, tanggal, jam_masuk, lokasi_absensi, jam_terlambat):
    engine = get_connection()
    try:
        with engine.begin() as connection:  # otomatis commit/rollback
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
            return result.scalar()  # ambil id_absensi yang dikembalikan
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None

def update_checkout(id_karyawan, tanggal, jam_keluar, lokasi_absensi, jam_kurang, total_jam_kerja):
    engine = get_connection()
    try:
        with engine.begin() as connection:  # ⬅️ commit & rollback otomatis
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
    
def get_history_absensi_harian(id_karyawan, tanggal):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query_result = connection.execute(
                text("""
                    SELECT a.id_karyawan, k.nama, s.id_status, s.nama_status, t.id_tipe, t.tipe, a.tanggal, a.jam_masuk, 
                    a.jam_keluar, a.jam_terlambat, a.jam_kurang, a.total_jam_kerja, a.lokasi_masuk, a.lokasi_keluar, k.gaji_pokok
                    FROM Absensi a 
                    INNER JOIN Karyawan k ON k.id_karyawan = a.id_karyawan 
                    INNER JOIN Jeniskaryawan j ON k.id_jenis = j.id_jenis 
                    INNER JOIN StatusPresensi s ON a.id_status = s.id_status 
                    INNER JOIN TipeKaryawan t ON k.id_tipe = t.id_tipe 
                    WHERE a.id_karyawan = :id_karyawan AND a.status = 1 AND a.tanggal = :tanggal;
                """),
                {"tanggal": tanggal, "id_karyawan": id_karyawan}
            )

            data = [dict(row) for row in query_result.mappings()]

            result = []
            JAM_ISTIRAHAT = 60
            BATAS_MAKS_MENIT_PER_HARI = 480

            for row in data:
                jam_terlambat = row['jam_terlambat'] or 0
                jam_kurang_db = row['jam_kurang'] or 0
                jam_kurang_total = jam_terlambat + jam_kurang_db
                gaji_pokok = row['gaji_pokok']

                tarif_per_menit = gaji_pokok / 12480
                gaji_maks_harian = tarif_per_menit * BATAS_MAKS_MENIT_PER_HARI
                potongan = tarif_per_menit * jam_kurang_total

                total_jam_kerja = row['total_jam_kerja'] or 0
                # waktu_kerja_efektif = max(0, total_jam_kerja - JAM_ISTIRAHAT)

                if row['jam_keluar']:
                    # total_gaji_harian = max(0, min(waktu_kerja_efektif, BATAS_MAKS_MENIT_PER_HARI) * tarif_per_menit - potongan)
                    total_gaji_harian = max(0, gaji_maks_harian - potongan)
                else:
                    total_gaji_harian = 0

                result.append({
                    'id_karyawan': row['id_karyawan'],
                    'nama': row['nama'],
                    'status_presensi': row.get('nama_status'),
                    'id_tipe': row['id_tipe'],
                    'tipe': row['tipe'],
                    'tanggal': row['tanggal'].strftime("%d-%m-%Y"),
                    'jam_masuk': row['jam_masuk'].strftime('%H:%M') if row['jam_masuk'] else None,
                    'jam_keluar': row['jam_keluar'].strftime('%H:%M') if row['jam_keluar'] else None,
                    'jam_terlambat': jam_terlambat,
                    'jam_bolos': jam_kurang_db,
                    'jam_kurang': jam_kurang_total,
                    'total_jam_kerja': total_jam_kerja,
                    'lokasi_masuk': row['lokasi_masuk'],
                    'lokasi_keluar': row['lokasi_keluar'],
                    'gaji_pokok': round(gaji_pokok),
                    'tarif_per_menit': round(tarif_per_menit),
                    'gaji_maks_harian': round(gaji_maks_harian),
                    'potongan': round(potongan),
                    'total_gaji_harian': round(total_gaji_harian),
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
                    WHERE a.status = 1 AND a.tanggal = :tanggal;
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

def update_absensi_by_id(id_absensi, jam_masuk, jam_keluar, jam_terlambat, jam_kurang, total_jam_kerja, lokasi_masuk, lokasi_keluar):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            if jam_keluar:
                query = text("""
                    UPDATE Absensi
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
                    UPDATE Absensi
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
