from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import get_connection


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
def get_list_absensi():
    result = connection.execute(
        text(f"""SELECT a.id_absensi, a.id_karyawan, k.nama, k.id_jenis, j.jenis, k.nama, a.tanggal, a.jam_masuk, a.jam_keluar FROM Absensi a INNER JOIN Karyawan k ON k.id_karyawan = a.id_karyawan INNER JOIN Jeniskaryawan j ON k.id_jenis = j.id_jenis WHERE a.status = 1;""")
    )
    return result

def add_checkin(id_karyawan, tanggal, jam_masuk):
    result = connection.execute(
        text(f"""INSERT INTO Absensi (id_karyawan, tanggal, jam_masuk, jam_keluar, status) VALUES('{id_karyawan}', '{tanggal}', '{jam_masuk}', '{jam_masuk}', 1);""")
    )
    connection.commit()
    return result

def add_checkout(id_karyawan, tanggal, jam_keluar):
    result = connection.execute(
        text(f"""UPDATE Absensi SET jam_keluar = '{jam_keluar}', updated_at = CURRENT_TIMESTAMP WHERE id_karyawan = {id_karyawan} AND tanggal = '{tanggal}';""")
    )
    connection.commit()
    return result