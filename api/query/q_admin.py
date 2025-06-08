from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash
from ..utils.config import get_connection, get_wita


connection = get_connection().connect()
timestamp_wita = get_wita()

def hash_password(password):
    return generate_password_hash(password)

def get_all_admin():
    try:
        result = connection.execute(text("""
            SELECT id_admin, nama, username, password, kode_pemulihan
            FROM admin
            WHERE status = 1;   
        """)).mappings().fetchall()
        return [dict(row) for row in result]
    except SQLAlchemyError as e:
        connection.rollback()
        print(f"Error occurred: {str(e)}")
        return []
    
def insert_admin(payload):
    try:
        result = connection.execute(text("""
            INSERT INTO admin (nama, username, kode_pemulihan, status, created_at, updated_at)
            VALUES (:nama, :username, :kode_pemulihan, 1, :timestamp_wita, timestamp_wita)
            RETURNING nama
        """), {**payload, "timestamp_wita": timestamp_wita}).mappings().fetchone()
        connection.commit()
        return dict(result)
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def get_admin_by_id(id_admin):
    try:
        result = connection.execute(text("""
            SELECT id_admin, nama, username, password, kode_pemulihan
            FROM admin
            WHERE id_admin = :id_admin
            AND status = 1;   
        """), {'id_admin': id_admin}).mappings().fetchone()
        return dict(result) if result else None
    except SQLAlchemyError as e:
        connection.rollback()
        print(f"Error occurred: {str(e)}")
        return []
    
def update_admin(id_admin, payload):
    try:
        result = connection.execute(
            text("""
                UPDATE admin SET nama = :nama, username = :username, password = :password, 
                kode_pemulihan = :kode_pemulihan, updated_at = :timestamp_wita
                WHERE id_admin = :id_admin RETURNING nama;
                """
                ),
            {**payload, "id_admin": id_admin, "timestamp_wita": timestamp_wita}
        ).fetchone()
        connection.commit()
        return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
    
def delete_admin(id_admin):
    try:
        result = connection.execute(
            text("UPDATE admin SET status = 0, updated_at = :timestamp_wita WHERE status = 1 AND id_admin = :id_admin RETURNING nama;"),
            {"id_admin": id_admin, "timestamp_wita": timestamp_wita}
        ).fetchone()
        connection.commit()
        return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
    
def change_password_admin(id_admin, plain_password):
    try:
        hashed_password = hash_password(plain_password)
        result = connection.execute(
            text("""
                UPDATE admin 
                SET password = :password, updated_at = :timestamp_wita
                WHERE id_admin = :id_admin AND status = 1
                RETURNING nama;
            """),
            {
                "password": hashed_password,
                "id_admin": id_admin,
                "timestamp_wita": timestamp_wita
            }
        ).fetchone()
        connection.commit()
        return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
