from sqlalchemy import text
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError
from ..utils.config import get_connection, get_wita


def hash_password(password):
    return generate_password_hash(password, method='pbkdf2:sha256')
    
def get_all_pegawai():
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT k.id_karyawan, k.nip, k.id_jenis, j.jenis, k.id_tipe, t.tipe, k.nama, k.gaji_pokok, k.username, k.password, k.kode_pemulihan, k.bank, k.no_rekening
                FROM karyawan k
                INNER JOIN jeniskaryawan j ON k.id_jenis = j.id_jenis
                INNER JOIN tipekaryawan t ON k.id_tipe = t.id_tipe
                WHERE k.status = 1;   
            """)).mappings().fetchall()
            return [dict(row) for row in result]
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
    
def insert_pegawai(payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            payload = payload.copy()  # penting agar tidak mengubah dict asli
            payload['nip'] = payload['nip'] or payload.pop('nip', None)
            payload['id_jenis'] = payload['id_jenis'] or payload.pop('jenis', None)
            payload['id_tipe'] = payload['id_tipe'] or payload.pop('tipe', None)

            if payload['nip'] is None or payload['id_jenis'] is None or payload['id_tipe'] is None:
                raise ValueError("Field 'nip', 'jenis' dan 'tipe' wajib diisi")
            
            result = connection.execute(text("""
                INSERT INTO karyawan (nip, id_jenis, id_tipe, nama, gaji_pokok, username, kode_pemulihan, bank, no_rekening, status, created_at, updated_at)
                VALUES (:nip, :id_jenis, :id_tipe, :nama, :gaji_pokok, :username, :kode_pemulihan, :bank, :no_rekening, 1, :timestamp_wita, :timestamp_wita)
                RETURNING nama
            """), {**payload, "timestamp_wita": get_wita()}).mappings().fetchone()
            return dict(result)
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
# query/q_pegawai.py
def get_jumlah_pegawai_non_direksi():
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT COUNT(*) as jumlah
                FROM karyawan k
                INNER JOIN jeniskaryawan j ON k.id_jenis = j.id_jenis
                WHERE k.status = 1 AND k.id_jenis != 1;
            """)).mappings().first()
            return result['jumlah'] if result else 0
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return 0
    
def get_pegawai_by_id(id_karyawan):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT k.id_karyawan, k.nip, k.id_jenis, j.jenis, k.id_tipe, t.tipe, k.nama, 
                k.bank, k.no_rekening, k.gaji_pokok, k.username, k.password, k.kode_pemulihan
                FROM karyawan k
                INNER JOIN jeniskaryawan j ON k.id_jenis = j.id_jenis
                INNER JOIN tipekaryawan t ON k.id_tipe = t.id_tipe
                WHERE id_karyawan = :id_karyawan
                AND k.status = 1;   
            """), {'id_karyawan': id_karyawan}).mappings().fetchone()
            return dict(result) if result else None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
    
def update_pegawai(id_karyawan, payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            payload = payload.copy()  # penting agar tidak mengubah dict asli
            payload['id_jenis'] = payload['id_jenis'] or payload.pop('jenis', None)
            payload['id_tipe'] = payload['id_tipe'] or payload.pop('tipe', None)

            if payload['id_jenis'] is None or payload['id_tipe'] is None:
                raise ValueError("Field 'jenis' dan 'tipe' wajib diisi")
            
            result = connection.execute(
                text("""
                    UPDATE karyawan 
                    SET id_jenis = :id_jenis, id_tipe = :id_tipe, nama = :nama, gaji_pokok = :gaji_pokok, 
                        username = :username, bank = :bank, no_rekening = :no_rekening, updated_at = :timestamp_wita
                    WHERE id_karyawan = :id_karyawan 
                    RETURNING nama;
                """),
                {
                    **payload,
                    "id_karyawan": id_karyawan,
                    "timestamp_wita": get_wita(),
                    "bank": payload.get("bank"),
                    "no_rekening": payload.get("no_rekening")
                }
            ).fetchone()
            return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
    
def delete_pegawai(id_karyawan):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""UPDATE karyawan SET status = 0, updated_at = :timestamp_wita 
                    WHERE status = 1 AND id_karyawan = :id_karyawan RETURNING nama;"""),
                {"id_karyawan": id_karyawan, "timestamp_wita": get_wita()}
            ).fetchone()
            return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
    
def change_password_pegawai(id_karyawan, plain_password):
    engine = get_connection()
    try:
        with engine.begin() as connection:
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
                    "timestamp_wita": get_wita()
                }
            ).fetchone()
            return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
