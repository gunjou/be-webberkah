from flask_jwt_extended import create_access_token
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection

connection = get_connection().connect()


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
                {"username": username, "kode_pemulihan": password}
            ).mappings().fetchone()

        if not result:
            return None

        access_token = create_access_token(
            identity=str(result['id_karyawan']),
            additional_claims={"role": 'karyawan'}
        )

        return {
            'access_token': access_token,
            'message': 'login success',
            'id_karyawan': result['id_karyawan'],
            'jenis': result['jenis'],
            'nama': result['nama']
        }

    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
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

        access_token = create_access_token(
            identity=str(result['id_admin']),
            additional_claims={"role": 'admin'}
        )

        return {
            'access_token': access_token,
            'message': 'login success',
            'id_admin': result['id_admin'],
            'nama': result['nama']
        }

    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return {'msg': 'Internal server error'}
