from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from ..utils.config import get_connection, get_wita


def get_all_jenis_pegawai():
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT id_jenis, jenis
                FROM jeniskaryawan
                WHERE status = 1;   
            """)).mappings().fetchall()
            return [dict(row) for row in result]
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
    
def insert_jenis_pegawai(payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(text("""
                INSERT INTO jeniskaryawan (jenis, status, created_at, updated_at)
                VALUES (:jenis, 1, :timestamp_wita, timestamp_wita)
                RETURNING jenis
            """), {**payload, "timestamp_wita": get_wita()}).mappings().fetchone()
            return dict(result)
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def get_jenis_by_id(id_jenis):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT id_jenis, jenis
                FROM jeniskaryawan
                WHERE id_jenis = :id_jenis
                AND status = 1;   
            """), {'id_jenis': id_jenis}).mappings().fetchone()
            return dict(result) if result else None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
    
def update_jenis(id_jenis, payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    UPDATE jeniskaryawan SET jenis = :jenis, updated_at = :timestamp_wita
                    WHERE id_jenis = :id_jenis RETURNING jenis;
                    """
                    ),
                {**payload, "id_jenis": id_jenis, "timestamp_wita": get_wita()}
            ).fetchone()
            return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
    
def delete_jenis(id_jenis):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""UPDATE jeniskaryawan SET status = 0, updated_at = :timestamp_wita 
                    WHERE status = 1 AND id_jenis = :id_jenis RETURNING jenis;"""),
                {"id_jenis": id_jenis, "timestamp_wita": get_wita()}
            ).fetchone()
            return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None