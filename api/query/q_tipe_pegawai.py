from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from ..utils.config import get_connection, get_wita


def get_all_tipe_pegawai():
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT id_tipe, tipe
                FROM tipekaryawan
                WHERE status = 1;   
            """)).mappings().fetchall()
            return [dict(row) for row in result]
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
    
def insert_tipe_pegawai(payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(text("""
                INSERT INTO tipekaryawan (tipe, status, created_at, updated_at)
                VALUES (:tipe, 1, :timestamp_wita, timestamp_wita)
                RETURNING tipe
            """), {**payload, "timestamp_wita": get_wita()}).mappings().fetchone()
            return dict(result)
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return None
    
def get_tipe_by_id(id_tipe):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT id_tipe, tipe
                FROM tipekaryawan
                WHERE id_tipe = :id_tipe
                AND status = 1;   
            """), {'id_tipe': id_tipe}).mappings().fetchone()
            return dict(result) if result else None
    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return []
    
def update_tipe(id_tipe, payload):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    UPDATE tipekaryawan SET tipe = :tipe, updated_at = :timestamp_wita
                    WHERE id_tipe = :id_tipe RETURNING tipe;
                    """
                    ),
                {**payload, "id_tipe": id_tipe, "timestamp_wita": get_wita()}
            ).fetchone()
            return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None
    
def delete_tipe(id_tipe):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""UPDATE tipekaryawan SET status = 0, updated_at = :timestamp_wita 
                    WHERE status = 1 AND id_tipe = :id_tipe RETURNING tipe;"""),
                {"id_tipe": id_tipe, "timestamp_wita": get_wita()}
            ).fetchone()
            return result
    except SQLAlchemyError as e:
        print(f"Error: {e}")
        return None