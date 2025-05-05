from flask_jwt_extended import create_access_token
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import get_connection, get_timezone, get_datetime_now


connection = get_connection().connect()


'''<--- Query untuk Table Admin --->'''
def get_list_admin():
    try:
        # Menjalankan query untuk mendapatkan daftar admin
        result = connection.execute(text("SELECT * FROM Admin WHERE status = 1;"))
        
        # Mengonversi hasil menjadi daftar dictionary
        admin_list = [dict(row) for row in result.mappings()]  # Mengonversi hasil ke dalam format dictionary
        return admin_list
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return []  # Mengembalikan daftar kosong jika terjadi kesalahan

def add_admin(nama, username, password):
    try:
        # Menggunakan parameter binding untuk keamanan
        result = connection.execute(
            text("""INSERT INTO Admin (nama, username, password, status) VALUES (:nama, :username, :password, 1)"""),
            {
                "nama": nama,
                "username": username,
                "password": password  # Menggunakan password yang diberikan
            }
        )
        
        # Commit perubahan
        connection.commit()
        
        # Mengembalikan ID admin yang baru ditambahkan
        return result.lastrowid  # Mengembalikan ID dari baris yang baru ditambahkan
    except SQLAlchemyError as e:
        connection.rollback()  # Rollback jika terjadi kesalahan
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None atau bisa juga mengangkat exception


'''<--- Query untuk Table Jenis Karyawan --->'''
def get_list_jenis():
    try:
        # Menjalankan query untuk mendapatkan daftar jenis karyawan
        result = connection.execute(
            text("""SELECT * FROM JenisKaryawan WHERE status = 1;""")
        )
        
        # Mengonversi hasil menjadi daftar dictionary
        jenis_list = [dict(row) for row in result.mappings()]  # Mengonversi hasil ke dalam format dictionary
        return jenis_list
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return []  # Mengembalikan daftar kosong jika terjadi kesalahan

def add_jenis(jenis):
    try:
        # Menggunakan parameter binding untuk keamanan
        result = connection.execute(
            text("""INSERT INTO JenisKaryawan (jenis, status) VALUES (:jenis, 1)"""),
            {"jenis": jenis}  # Menggunakan parameter untuk mencegah SQL injection
        )

        # Commit perubahan
        connection.commit()
        
        # Mengembalikan ID jenis yang baru ditambahkan
        return result.lastrowid  # Mengembalikan ID dari baris yang baru ditambahkan
    except SQLAlchemyError as e:
        connection.rollback()  # Rollback jika terjadi kesalahan
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None atau bisa juga mengangkat exception

'''<--- Query untuk Table Tipe Karyawan --->'''
def get_list_tipe():
    try:
        # Menjalankan query untuk mendapatkan daftar tipe karyawan
        result = connection.execute(
            text("""SELECT * FROM TipeKaryawan WHERE status = 1;""")
        )
        
        # Mengonversi hasil menjadi daftar dictionary
        tipe_list = [dict(row) for row in result.mappings()]  # Mengonversi hasil ke dalam format dictionary
        return tipe_list
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return []  # Mengembalikan daftar kosong jika terjadi kesalahan

'''<--- Query untuk Table  Karyawan --->'''
def get_list_karyawan():
    try:
        # Menjalankan query untuk mendapatkan daftar karyawan
        result = connection.execute(
            text("""SELECT k.id_karyawan, k.id_jenis, j.jenis, k.id_tipe, t.tipe, k.nama, k.gaji_pokok, k.username, k.kode_pemulihan 
                FROM Karyawan k 
                INNER JOIN JenisKaryawan j ON k.id_jenis = j.id_jenis
                INNER JOIN TipeKaryawan t on k.id_tipe = t.id_tipe
                WHERE k.status = 1 AND j.jenis != 'direktur';""")
        )
        
        # Mengonversi hasil menjadi daftar dictionary
        karyawan_list = [dict(row) for row in result.mappings()]  # Mengonversi hasil ke dalam format dictionary
        return karyawan_list
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return []  # Mengembalikan daftar kosong jika terjadi kesalahan

def get_karyawan(id):
    try:
        # Mencari karyawan berdasarkan ID
        result = connection.execute(
            text("SELECT * FROM Karyawan WHERE id_karyawan = :id AND status = 1"),
            {"id": id}
        ).mappings().fetchone()  # Mengambil satu record sebagai dictionary

        if result is None:
            return None  # Mengembalikan None jika karyawan tidak ditemukan

        return dict(result)  # Mengembalikan hasil sebagai dictionary
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None jika terjadi kesalahan

def add_karyawan(jenis, tipe, nama, gaji_pokok, username, kode_pemulihan):
    # Kedepannya akan menggunakan Hash password sebelum menyimpannya
    # hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        # Menggunakan parameter binding untuk keamanan
        result = connection.execute(
            text("""INSERT INTO Karyawan (id_jenis, id_tipe, nama, gaji_pokok, username, kode_pemulihan, status) 
                     VALUES (:jenis, :tipe, :nama, :gaji_pokok, :username, :kode_pemulihan, 1)"""),
            {
                "jenis": jenis,
                "tipe": tipe,
                "nama": nama,
                "gaji_pokok": gaji_pokok,
                "username": username,
                "kode_pemulihan": kode_pemulihan
            }
        )
        
        # Commit perubahan
        connection.commit()
        
        # Mengembalikan ID karyawan yang baru ditambahkan
        return result.lastrowid  # Mengembalikan ID dari baris yang baru ditambahkan
    except SQLAlchemyError as e:
        connection.rollback()  # Rollback jika terjadi kesalahan
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None atau bisa juga mengangkat exception

def update_karyawan(id_emp, jenis, tipe, nama, gaji_pokok, username, kode_pemulihan):
    try:
        # Menyiapkan query untuk update
        result = connection.execute(
            text("""
                UPDATE Karyawan 
                SET id_jenis = :jenis, 
                    tipe = :tipe,
                    nama = :nama,
                    gaji_pokok = :gaji_pokok, 
                    username = :username, 
                    kode_pemulihan = :kode_pemulihan, 
                    updated_at = CURRENT_TIMESTAMP 
                WHERE id_karyawan = :id_emp
            """),
            {
                "jenis": jenis,
                "tipe": tipe,
                "nama": nama,
                "gaji_pokok": gaji_pokok,
                "username": username,
                "kode_pemulihan": kode_pemulihan,  # Menggunakan password yang diberikan
                "id_emp": id_emp
            }
        )
        
        # Commit perubahan
        connection.commit()
        
        # Mengembalikan jumlah baris yang terpengaruh
        return result.rowcount  # Mengembalikan jumlah baris yang diupdate
    except SQLAlchemyError as e:
        connection.rollback()  # Rollback jika terjadi kesalahan
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None atau bisa juga mengangkat exception

def remove_karyawan(id_emp):
    try:
        # Menggunakan parameter binding untuk keamanan
        result = connection.execute(
            text("""UPDATE Karyawan SET status = 0, updated_at = CURRENT_TIMESTAMP WHERE id_karyawan = :id_emp"""),
            {"id_emp": id_emp}  # Menggunakan parameter untuk mencegah SQL injection
        )
        
        # Commit perubahan
        connection.commit()
        
        # Mengembalikan jumlah baris yang terpengaruh
        return result.rowcount  # Mengembalikan jumlah baris yang diupdate
    except SQLAlchemyError as e:
        connection.rollback()  # Rollback jika terjadi kesalahan
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None atau bisa juga mengangkat exception


'''<--- Query untuk Table Absensi --->'''
def add_checkin(id_karyawan, tanggal, jam_masuk, lokasi_absensi, jam_terlambat): # /absen karyawan
    datetime_now = get_datetime_now()
    try:
        result = connection.execute(
            text("""INSERT INTO Absensi (
                 id_karyawan, 
                 tanggal, 
                 jam_masuk, 
                 jam_keluar, 
                 lokasi_masuk, 
                 lokasi_keluar, 
                 jam_terlambat, 
                 created_at, 
                 updated_at, 
                 status,
                 id_status
                 ) 
                     VALUES (:id_karyawan, :tanggal, :jam_masuk, NULL, :lokasi_masuk, NULL, :jam_terlambat, :created_at, :updated_at, 1, 1)"""),
            {
                "id_karyawan": id_karyawan,
                "tanggal": tanggal,
                "jam_masuk": jam_masuk,
                "lokasi_masuk": lokasi_absensi,
                "jam_terlambat": jam_terlambat,
                "created_at": datetime_now,
                "updated_at": datetime_now
            }
        )
        
        # Commit perubahan
        connection.commit()
        
        return result.lastrowid  # Mengembalikan ID dari baris yang baru ditambahkan
    except SQLAlchemyError as e:
        connection.rollback()  # Rollback jika terjadi kesalahan
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None jika terjadi kesalahan

def update_checkout(id_karyawan, tanggal, jam_keluar, lokasi_absensi, jam_kurang, total_jam_kerja): # /absen karyawan
    datetime_now = get_datetime_now()
    try:
        result = connection.execute(
            text("""UPDATE Absensi 
                    SET jam_keluar = :jam_keluar,
                    lokasi_keluar = :lokasi_keluar,
                    jam_kurang = :jam_kurang,
                    total_jam_kerja = :total_jam_kerja,
                    updated_at = :updated_at
                    WHERE id_karyawan = :id_karyawan AND tanggal = :tanggal AND jam_keluar IS NULL"""),
            {
                "jam_keluar": jam_keluar,
                "lokasi_keluar": lokasi_absensi,
                "jam_kurang": jam_kurang,
                "id_karyawan": id_karyawan,
                "tanggal": tanggal,
                "total_jam_kerja": total_jam_kerja,
                "updated_at": datetime_now
            }
        )
        
        # Commit perubahan
        connection.commit()
        
        # Mengembalikan jumlah baris yang terpengaruh
        return result.rowcount  # Mengembalikan jumlah baris yang diupdate
    except SQLAlchemyError as e:
        connection.rollback()  # Rollback jika terjadi kesalahan
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None jika terjadi kesalahan

def is_wfh_allowed(id_karyawan):
    try:
        result = connection.execute(
            text("SELECT status FROM wfh_karyawan WHERE id_karyawan = :id_karyawan AND status = 1"),
            {"id_karyawan": id_karyawan}
        ).fetchone()
        return result is not None  # True jika ada data aktif
    except SQLAlchemyError as e:
        print(f"Error checking WFH status: {str(e)}")
        return False

def hapus_absen_keluar(id_absensi): # /absen karyawan
    try:
        query = text("""
            UPDATE Absensi
            SET jam_keluar = NULL,
                jam_kurang = NULL,
                lokasi_keluar = NULL,
                total_jam_kerja = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_absensi = :id_absensi AND status = 1
        """)
        params = {
            'id_absensi': id_absensi
        }

        result = connection.execute(query, params)
        connection.commit()

        return result.rowcount  # Kembalikan jumlah baris yang diubah
    except SQLAlchemyError as e:
        print(f"Update Absensi Error: {str(e)}")
        return None
    
def get_absensi_harian(id_karyawan, tanggal):
    try:
        result = connection.execute(
            text("""
                SELECT a.id_karyawan,
                    k.nama,
                    s.id_status,
                    s.nama_status,
                    t.id_tipe,
                    t.tipe,
                    a.tanggal,
                    a.jam_masuk,
                    a.jam_keluar,
                    a.jam_terlambat,
                    a.jam_kurang,
                    a.total_jam_kerja,
                    a.lokasi_masuk,
                    a.lokasi_keluar,
                    k.gaji_pokok
                FROM Absensi a 
                INNER JOIN Karyawan k ON k.id_karyawan = a.id_karyawan 
                INNER JOIN Jeniskaryawan j ON k.id_jenis = j.id_jenis 
                INNER JOIN StatusPresensi s ON a.id_status = s.id_status 
                INNER JOIN TipeKaryawan t ON k.id_tipe = t.id_tipe 
                WHERE a.id_karyawan = :id_karyawan AND a.status = 1 AND a.tanggal = :tanggal;
            """),
            {"tanggal": tanggal, "id_karyawan": id_karyawan}
        )

        absensi_harian_list = [dict(row) for row in result.mappings()]
        return absensi_harian_list
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []

def get_list_absensi(tanggal):
    try:
        result = connection.execute(
            text("""
                SELECT a.id_absensi, 
                    a.id_karyawan, 
                    k.nama, 
                    k.id_jenis, 
                    j.jenis, 
                    a.tanggal, 
                    a.jam_masuk, 
                    a.jam_keluar, 
                    a.jam_terlambat, 
                    a.jam_kurang, 
                    a.total_jam_kerja, 
                    a.lokasi_masuk, 
                    a.lokasi_keluar, 
                    s.id_status AS id_presensi, 
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
        return absensi_list
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
    
def get_list_tidak_hadir(tanggal):
    try:
        result = connection.execute(
            text("""
                SELECT 
                    k.id_karyawan,
                    k.nama,
                    k.id_jenis,
                    j.jenis,
                    :tanggal AS tanggal
                FROM Karyawan k
                JOIN JenisKaryawan j ON k.id_jenis = j.id_jenis
                LEFT JOIN Absensi a ON k.id_karyawan = a.id_karyawan AND a.tanggal = :tanggal
                WHERE k.status = 1 AND a.id_absensi IS NULL
            """),
            {"tanggal": tanggal}
        )
        
        absensi_list = [dict(row) for row in result.mappings()]
        return absensi_list
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []

'''<--- Query untuk Login --->'''
def get_login_karyawan(username, password):
    try:
        # Cek login berdasarkan username dan password
        result = connection.execute(
            text("""
                SELECT k.id_karyawan, k.username, k.password, j.jenis, k.nama, k.status
                FROM Karyawan k
                INNER JOIN JenisKaryawan j ON k.id_jenis = j.id_jenis
                WHERE k.username = :username
                AND k.password = :password
                AND k.status = 1;
            """),
            {"username": username, "password": password}
        ).mappings().fetchone()

        # Jika tidak ditemukan, coba cek dengan token sebagai fallback
        if not result:
            result = connection.execute(
                text("""
                    SELECT k.id_karyawan, k.username, k.kode_pemulihan, j.jenis, k.nama, k.status
                    FROM Karyawan k
                    INNER JOIN JenisKaryawan j ON k.id_jenis = j.id_jenis
                    WHERE k.username = :username
                    AND k.kode_pemulihan = :kode_pemulihan
                    AND k.status = 1;
                """),
                {"username": username, "kode_pemulihan": password}  # pakai 'password' sebagai input untuk token juga
            ).mappings().fetchone()

        if not result:
            return None
        
        access_token = create_access_token(identity=str(result['id_karyawan']), additional_claims={"role": 'karyawan'})
        return {
            'access_token': access_token,
            'message': 'login success',
            'id_karyawan': result['id_karyawan'],
            'jenis': result['jenis'],
            'nama': result['nama']
        }
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan
        return {'msg': 'Internal server error'}
    
def get_login_admin(username, password):
    try:
        # Cek login berdasarkan username dan password
        result = connection.execute(
            text("""
                SELECT id_admin, nama, username, password, status
                FROM Admin
                WHERE username = :username
                AND password = :password
                AND status = 1;
            """),
            {"username": username, "password": password}
        ).mappings().fetchone()

        # Jika tidak ditemukan, coba cek dengan kode_pemulihan
        if not result:
            result = connection.execute(
                text("""
                    SELECT id_admin, nama, username, kode_pemulihan, status
                    FROM Admin
                    WHERE username = :username
                    AND kode_pemulihan = :kode_pemulihan
                    AND status = 1;
                """),
                {"username": username, "kode_pemulihan": password}
            ).mappings().fetchone()

        if not result:
            return None

        access_token = create_access_token(identity=str(result['id_admin']), additional_claims={"role": 'admin'})
        return {
            'access_token': access_token,
            'message': 'login success',
            'id_admin': result['id_admin'],
            'nama': result['nama']
        }

    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan
        return {'msg': 'Internal server error'}
    

'''<--- Query Check Status Presensi --->'''
def get_check_presensi(id_karyawan):
    today, _ = get_timezone()  # Mendapatkan tanggal hari ini
    # print(today)
    try:
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
    
def update_absensi_times(id_absensi, jam_masuk, jam_keluar, jam_terlambat, jam_kurang, total_jam_kerja):
    try:
        if jam_keluar:  # Jika jam_keluar diisi
            query = text("""
                UPDATE Absensi
                SET jam_masuk = :jam_masuk,
                    jam_keluar = :jam_keluar,
                    jam_terlambat = :jam_terlambat,
                    total_jam_kerja = :total_jam_kerja,
                    jam_kurang = :jam_kurang,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id_absensi = :id_absensi AND status = 1
            """)
            params = {
                'id_absensi': id_absensi,
                'jam_masuk': jam_masuk,
                'jam_keluar': jam_keluar,
                'jam_terlambat': jam_terlambat,
                'total_jam_kerja': total_jam_kerja,
                'jam_kurang': jam_kurang
            }
        else:  # Jika jam_keluar kosong
            query = text("""
                UPDATE Absensi
                SET jam_masuk = :jam_masuk,
                    jam_terlambat = :jam_terlambat,
                    jam_keluar = NULL,
                    jam_kurang = NULL,
                    lokasi_keluar = NULL,
                    total_jam_kerja = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id_absensi = :id_absensi AND status = 1
            """)
            params = {
                'jam_masuk': jam_masuk,
                'jam_terlambat': jam_terlambat,
                'id_absensi': id_absensi
            }

        result = connection.execute(query, params)
        connection.commit()

        return result.rowcount  # Kembalikan jumlah baris yang diubah
    except SQLAlchemyError as e:
        print(f"Update Absensi Error: {str(e)}")
        return None
    
def remove_abseni(id_abseni):
    try:
        # Menggunakan parameter binding untuk keamanan
        result = connection.execute(
            text("""DELETE FROM Absensi WHERE id_absensi = :id_abseni"""),
            {"id_abseni": id_abseni}  # Menggunakan parameter untuk mencegah SQL injection
        )
        
        # Commit perubahan
        connection.commit()
        
        # Mengembalikan jumlah baris yang terpengaruh
        return result.rowcount  # Mengembalikan jumlah baris yang diupdate
    except SQLAlchemyError as e:
        connection.rollback()  # Rollback jika terjadi kesalahan
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None atau bisa juga mengangkat exception
    

"""<-- Query Rekapan.py -->"""
def get_rekap_absensi(start_date, end_date):
    try:
        query = text("""
            SELECT 
                k.id_karyawan,
                k.nama,
                k.gaji_pokok,
                k.id_jenis,
                jk.jenis,
                k.id_tipe,
                tk.tipe,
                SUM(a.jam_terlambat) AS total_jam_terlambat,
                SUM(a.jam_kurang) AS total_jam_kurang,
                12480 AS total_jam_kerja_normal,
                SUM(a.total_jam_kerja) AS total_jam_kerja,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Hadir') AS jumlah_hadir,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Tidak Hadir') AS jumlah_alpha,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Setengah Hari') AS jumlah_setengah_hari,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Izin') AS jumlah_izin,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Sakit') AS jumlah_sakit,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Dinas Luar') AS dinas_luar
            FROM absensi a
            JOIN karyawan k ON a.id_karyawan = k.id_karyawan
            LEFT JOIN statuspresensi sp ON a.id_status = sp.id_status
            LEFT JOIN jeniskaryawan jk ON k.id_jenis = jk.id_jenis
            LEFT JOIN tipekaryawan tk ON k.id_tipe = tk.id_tipe
            WHERE a.tanggal BETWEEN :start_date AND :end_date
            GROUP BY 
                k.id_karyawan, k.nama, k.gaji_pokok, 
                k.id_jenis, jk.jenis, 
                k.id_tipe, tk.tipe
            ORDER BY k.nama;
        """)
        result = connection.execute(query, {'start_date': start_date, 'end_date': end_date})
        return [dict(row) for row in result.mappings()]
    except Exception as e:
        print(f"Query Error: {str(e)}")
        return []

def get_rekap_absensi_by_id(start_date, end_date, id_karyawan):
    try:
        query = text("""
            SELECT 
                k.id_karyawan,
                k.nama,
                k.gaji_pokok,
                k.id_jenis,
                jk.jenis,
                k.id_tipe,
                tk.tipe,
                SUM(a.jam_terlambat) AS total_jam_terlambat,
                SUM(a.jam_kurang) AS total_jam_kurang,
                12480 AS total_jam_kerja_normal,
                SUM(a.total_jam_kerja) AS total_jam_kerja,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Hadir') AS jumlah_hadir,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Tidak Hadir') AS jumlah_alpha,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Setengah Hari') AS jumlah_setengah_hari,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Izin') AS jumlah_izin,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Sakit') AS jumlah_sakit,
                COUNT(sp.nama_status) FILTER (WHERE sp.nama_status = 'Dinas Luar') AS dinas_luar
            FROM absensi a
            JOIN karyawan k ON a.id_karyawan = k.id_karyawan
            LEFT JOIN statuspresensi sp ON a.id_status = sp.id_status
            LEFT JOIN jeniskaryawan jk ON k.id_jenis = jk.id_jenis
            LEFT JOIN tipekaryawan tk ON k.id_tipe = tk.id_tipe
            WHERE a.tanggal BETWEEN :start_date AND :end_date
              AND k.id_karyawan = :id_karyawan
            GROUP BY 
                k.id_karyawan, k.nama, k.gaji_pokok, 
                k.id_jenis, jk.jenis, 
                k.id_tipe, tk.tipe
            ORDER BY k.nama;
        """)
        result = connection.execute(query, {
            'start_date': start_date,
            'end_date': end_date,
            'id_karyawan': id_karyawan
        })
        row = result.mappings().fetchone()
        return dict(row) if row else None
    except Exception as e:
        print(f"Query Error: {str(e)}")
        return None

def get_list_rekapan_person(start_date, end_date, id_karyawan):
    try:
        query = text("""
            SELECT 
                k.nama,
                s.nama_status,
                t.tipe,
                a.tanggal,
                a.jam_masuk,
                a.jam_keluar,
                a.jam_terlambat,
                a.jam_kurang,
                a.total_jam_kerja,
                a.lokasi_masuk,
                a.lokasi_keluar
            FROM absensi a
            INNER JOIN karyawan k ON k.id_karyawan = a.id_karyawan
            INNER JOIN jeniskaryawan j ON k.id_jenis = j.id_jenis
            INNER JOIN statuspresensi s ON a.id_status = s.id_status
            INNER JOIN tipekaryawan t ON k.id_tipe = t.id_tipe
            WHERE a.id_karyawan = :id_karyawan
            AND a.status = 1
            AND a.tanggal BETWEEN :start_date AND :end_date
        """)
        result = connection.execute(query, {
            'start_date': start_date,
            'end_date': end_date,
            'id_karyawan': id_karyawan
        })
        rows = result.mappings().fetchall()
        return [dict(row) for row in rows] if rows else []
    except Exception as e:
        print(f"Query Error: {str(e)}")
        return []
