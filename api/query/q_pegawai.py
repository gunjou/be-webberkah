from sqlalchemy import text
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError
from ..utils.config import get_connection, get_wita


connection = get_connection().connect()
timestamp_wita = get_wita()

def hash_password(password):
    return generate_password_hash(password, method='pbkdf2:sha256')
    
def get_all_pegawai():
    try:
        result = connection.execute(text("""
            SELECT k.id_karyawan, k.id_jenis, j.jenis, k.id_tipe, t.tipe, k.nama, k.gaji_pokok, k.username, k.password, k.kode_pemulihan
            FROM karyawan k
            INNER JOIN jeniskaryawan j ON k.id_jenis = j.id_jenis
            INNER JOIN tipekaryawan t ON k.id_tipe = t.id_tipe
            WHERE k.status = 1;   
        """)).mappings().fetchall()
        return [dict(row) for row in result]
    except SQLAlchemyError as e:
        connection.rollback()
        print(f"Error occurred: {str(e)}")
        return []
    
def insert_pegawai(payload):
    try:
        payload = payload.copy()  # penting agar tidak mengubah dict asli
        payload['id_jenis'] = payload.pop('jenis', None)
        payload['id_tipe'] = payload.pop('tipe', None)

        if payload['id_jenis'] is None or payload['id_tipe'] is None:
            raise ValueError("Field 'jenis' dan 'tipe' wajib diisi")
        
        result = connection.execute(text("""
            INSERT INTO karyawan (id_jenis, id_tipe, nama, gaji_pokok, username, kode_pemulihan, status, created_at, updated_at)
            VALUES (:id_jenis, :id_tipe, :nama, :gaji_pokok, :username, :kode_pemulihan, 1, :timestamp_wita, :timestamp_wita)
            RETURNING nama
        """), {**payload, "timestamp_wita": timestamp_wita}).mappings().fetchone()
        connection.commit()
        return dict(result)
    except SQLAlchemyError as e:
        connection.rollback()
        print(f"Error occurred: {str(e)}")
        return None
    
def get_pegawai_by_id(id_karyawan):
    try:
        result = connection.execute(text("""
            SELECT k.id_karyawan, k.id_jenis, j.jenis, k.id_tipe, t.tipe, k.nama, k.gaji_pokok, k.username, k.password, k.kode_pemulihan
            FROM karyawan k
            INNER JOIN jeniskaryawan j ON k.id_jenis = j.id_jenis
            INNER JOIN tipekaryawan t ON k.id_tipe = t.id_tipe
            WHERE id_karyawan = :id_karyawan
            AND k.status = 1;   
        """), {'id_karyawan': id_karyawan}).mappings().fetchone()
        return dict(result) if result else None
    except SQLAlchemyError as e:
        connection.rollback()
        print(f"Error occurred: {str(e)}")
        return []
    
def update_pegawai(id_karyawan, payload):
    try:
        payload = payload.copy()  # penting agar tidak mengubah dict asli
        payload['id_jenis'] = payload.pop('jenis', None)
        payload['id_tipe'] = payload.pop('tipe', None)

        if payload['id_jenis'] is None or payload['id_tipe'] is None:
            raise ValueError("Field 'jenis' dan 'tipe' wajib diisi")
        
        result = connection.execute(
            text("""
                UPDATE karyawan SET id_jenis = :id_jenis, id_tipe = :id_tipe, nama = :nama, gaji_pokok = :gaji_pokok, 
                username = :username, updated_at = :timestamp_wita
                WHERE id_karyawan = :id_karyawan RETURNING nama;
                """
                ),
            {**payload, "id_karyawan": id_karyawan, "timestamp_wita": timestamp_wita}
        ).fetchone()
        connection.commit()
        return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
    
def delete_pegawai(id_karyawan):
    try:
        result = connection.execute(
            text("""UPDATE karyawan SET status = 0, updated_at = :timestamp_wita 
                 WHERE status = 1 AND id_karyawan = :id_karyawan RETURNING nama;"""),
            {"id_karyawan": id_karyawan, "timestamp_wita": timestamp_wita}
        ).fetchone()
        connection.commit()
        return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
    
def change_password_pegawai(id_karyawan, plain_password):
    try:
        hashed_password = hash_password(plain_password)
        result = connection.execute(
            text("""
                UPDATE karyawan 
                SET password = :password, updated_at = :timestamp_wita
                WHERE id_karyawan = :id_karyawan AND status = 1
                RETURNING nama;
            """),
            {
                "password": hashed_password,
                "id_karyawan": id_karyawan,
                "timestamp_wita": timestamp_wita
            }
        ).fetchone()
        connection.commit()
        return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
