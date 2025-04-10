from datetime import date, datetime, time
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


'''<--- Query untuk Table  Karyawan --->'''
def get_list_karyawan():
    try:
        # Menjalankan query untuk mendapatkan daftar karyawan
        result = connection.execute(
            text("""SELECT k.id_karyawan, k.id_jenis, j.jenis, k.nama, k.gaji_pokok, k.username, k.password 
                     FROM Karyawan k 
                     INNER JOIN JenisKaryawan j ON k.id_jenis = j.id_jenis 
                     WHERE k.status = 1;""")
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
            text("SELECT * FROM Karyawan WHERE id_karyawan = :id"),
            {"id": id}
        ).mappings().fetchone()  # Mengambil satu record sebagai dictionary

        if result is None:
            return None  # Mengembalikan None jika karyawan tidak ditemukan

        return dict(result)  # Mengembalikan hasil sebagai dictionary
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return None  # Mengembalikan None jika terjadi kesalahan

def add_karyawan(jenis, nama, gaji_pokok, username, password):
    # Kedepannya akan menggunakan Hash password sebelum menyimpannya
    # hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        # Menggunakan parameter binding untuk keamanan
        result = connection.execute(
            text("""INSERT INTO Karyawan (id_jenis, nama, gaji_pokok, username, password, status) 
                     VALUES (:jenis, :nama, :gaji_pokok, :username, :password, 1)"""),
            {
                "jenis": jenis,
                "nama": nama,
                "gaji_pokok": gaji_pokok,
                "username": username,
                "password": password
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

def update_karyawan(id_emp, jenis, nama, gaji_pokok, username, password):
    try:
        # Menyiapkan query untuk update
        result = connection.execute(
            text("""
                UPDATE Karyawan 
                SET id_jenis = :jenis, 
                    nama = :nama, 
                    gaji_pokok = :gaji_pokok, 
                    username = :username, 
                    password = :password, 
                    updated_at = CURRENT_TIMESTAMP 
                WHERE id_karyawan = :id_emp
            """),
            {
                "jenis": jenis,
                "nama": nama,
                "gaji_pokok": gaji_pokok,
                "username": username,
                "password": password,  # Menggunakan password yang diberikan
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
def add_checkin(id_karyawan, tanggal, jam_masuk, lokasi_absensi, jam_terlambat):
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

def update_checkout(id_karyawan, tanggal, jam_keluar, lokasi_absensi, total_jam_kerja):
    datetime_now = get_datetime_now()
    try:
        result = connection.execute(
            text("""UPDATE Absensi 
                    SET jam_keluar = :jam_keluar,
                    lokasi_keluar = :lokasi_keluar,
                    total_jam_kerja = :total_jam_kerja,
                    updated_at = :updated_at
                    WHERE id_karyawan = :id_karyawan AND tanggal = :tanggal AND jam_keluar IS NULL"""),
            {
                "jam_keluar": jam_keluar,
                "lokasi_keluar": lokasi_absensi,
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
    
def get_list_absensi():
    today, _ = get_timezone()  # Mendapatkan tanggal hari ini
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
                    a.lokasi_masuk, 
                    a.lokasi_keluar, 
                    a.jam_terlambat, 
                    a.total_jam_kerja, 
                    s.id_status AS id_presensi, 
                    s.nama_status AS status_presensi  
                FROM Absensi a 
                INNER JOIN Karyawan k ON k.id_karyawan = a.id_karyawan 
                INNER JOIN Jeniskaryawan j ON k.id_jenis = j.id_jenis 
                INNER JOIN StatusPresensi s ON a.id_status = s.id_status 
                WHERE a.status = 1 AND a.tanggal = :today;
            """),
            {"today": today}  # Menggunakan parameter binding untuk mencegah SQL injection
        )
        
        # Mengonversi hasil menjadi daftar dictionary
        absensi_list = [dict(row) for row in result.mappings()]  # Mengonversi hasil ke dalam format dictionary
        return absensi_list
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return []  # Mengembalikan daftar kosong jika terjadi kesalahan
    
def get_list_tidak_hadir():
    today, _ = get_timezone()  # Mendapatkan tanggal hari ini
    try:
        result = connection.execute(
            text("""
                SELECT 
                    k.id_karyawan,
                    k.nama,
                    k.id_jenis,
                    j.jenis,
                    :today AS tanggal
                FROM Karyawan k
                JOIN JenisKaryawan j ON k.id_jenis = j.id_jenis
                LEFT JOIN Absensi a ON k.id_karyawan = a.id_karyawan AND a.tanggal = :today
                WHERE a.id_absensi IS NULL
            """),
            {"today": today}  # Menggunakan parameter binding untuk mencegah SQL injection
        )
        
        # Mengonversi hasil menjadi daftar dictionary
        absensi_list = [dict(row) for row in result.mappings()]  # Mengonversi hasil ke dalam format dictionary
        return absensi_list
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return []  # Mengembalikan daftar kosong jika terjadi kesalahan


'''<--- Query untuk Login --->'''
def get_login_karyawan(username, password):
    try:
        # Menggunakan query untuk memverifikasi username dan password
        result = connection.execute(
            text("""
                SELECT k.id_karyawan, k.username, k.password, j.jenis, k.nama, k.status
                FROM Karyawan k INNER JOIN jeniskaryawan j
                ON k.id_jenis = j.id_jenis
                WHERE username = :username
                AND password = :password
                AND k.status = 1;
            """),
            {
                "username": username,
                "password": password
            }
        ).mappings().fetchone()

        if not result:
            return None
            
        access_token = create_access_token(identity=str(result['id_karyawan']))
        return {
            'access_token': access_token,
            'message': 'login success',
            'id_karyawan': result['id_karyawan'],
            'jenis': result['jenis'],
            'nama': result['nama']}
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return {'msg': 'Internal server error'}
    
def get_login_admin(username, password):
    try:
        # Menggunakan query untuk memverifikasi username dan password
        result = connection.execute(
            text("""
                SELECT id_admin, nama, username, password, status
                FROM Admin
                WHERE username = :username
                AND password = :password
                AND status = 1;
            """),
            {
                "username": username,
                "password": password
            }
        ).mappings().fetchone()

        if not result:
            return None
            
        access_token = create_access_token(identity=str(result['id_admin']))
        return {
            'access_token': access_token,
            'message': 'login success',
            'id_admin': result['id_admin'],
            'nama': result['nama']}
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")  # Log kesalahan (atau gunakan logging)
        return {'msg': 'Internal server error'}
    

'''<--- Query Check Status Presensi --->'''
def get_check_presensi(id_karyawan):
    today, _ = get_timezone()  # Mendapatkan tanggal hari ini
    # print(today)
    try:
        result = connection.execute(
            text("""
                SELECT tanggal, jam_masuk, jam_keluar, lokasi_masuk, lokasi_keluar, jam_terlambat
                FROM Absensi 
                WHERE id_karyawan = :id_karyawan
                AND tanggal = :today
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