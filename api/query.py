from sqlalchemy import text

from .config import get_connection


connection = get_connection().connect()


'''Query untuk Table Admin'''
def get_list_admin():
    result = connection.execute(text(f"""SELECT * FROM Admin WHERE status = 1;"""))
    return result

def add_admin(nama, username, password):
    result = connection.execute(
        text(f"""INSERT INTO Admin (nama, username, password, status) VALUES('{nama}', '{username}', '{password}', 1);""")
    )
    connection.commit()
    return result


'''Query untuk Table Jenis Karyawan'''
def get_list_jenis():
    result = connection.execute(
        text(f"""SELECT * FROM JenisKaryawan WHERE status = 1;""")
    )
    return result

def add_jenis(jenis):
    result = connection.execute(
        text(f"""INSERT INTO JenisKaryawan (jenis, status) VALUES('{jenis}', 1);""")
    )
    connection.commit()
    return result


'''Query untuk Table  Karyawan'''
def get_list_karyawan():
    result = connection.execute(
        text(f"""SELECT k.id_karyawan, k.id_jenis, j.jenis, k.nama, k.gaji_pokok, k.username, k.password FROM Karyawan k INNER JOIN JenisKaryawan j ON k.id_jenis = j.id_jenis WHERE k.status = 1;""")
    )
    return result

def add_karyawan(jenis, nama, gaji_pokok, username, password):
    result = connection.execute(
        text(f"""INSERT INTO Karyawan (id_jenis, nama, gaji_pokok, username, password, status) VALUES('{jenis}', '{nama}', '{gaji_pokok}', '{username}', '{password}', 1);""")
    )
    connection.commit()
    return result

def update_karyawan(id_emp, jenis, nama, gaji_pokok, username, password):
    result = connection.execute(
        text(f"""UPDATE Karyawan SET id_jenis = '{jenis}', nama = '{nama}', gaji_pokok = '{gaji_pokok}', username = '{username}', password = '{password}', updated_at = CURRENT_TIMESTAMP WHERE id_karyawan = {id_emp};""")
    )
    connection.commit()
    return result

def remove_karyawan(id_emp):
    result = connection.execute(
        text(f"""UPDATE Karyawan SET status = 0, updated_at = CURRENT_TIMESTAMP WHERE id_karyawan = {id_emp};""")
    )
    connection.commit()
    return result


'''Query untuk Table Absensi'''
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