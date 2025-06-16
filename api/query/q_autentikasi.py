from flask_jwt_extended import create_access_token
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash

from ..utils.config import get_connection

connection = get_connection().connect()


def get_login_karyawan(username, password):
    try:
        # Ambil data karyawan berdasarkan username saja (bukan password)
        result = connection.execute(
            text("""
                SELECT k.id_karyawan, k.username, k.password, j.jenis, k.nama, k.status
                FROM Karyawan k
                INNER JOIN JenisKaryawan j ON k.id_jenis = j.id_jenis
                WHERE k.username = :username
                AND k.status = 1;
            """),
            {"username": username}
        ).mappings().fetchone()

        # Jika ditemukan dan password cocok
        if result and check_password_hash(result['password'], password):
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

        # Jika tidak cocok, coba cek kode pemulihan
        if not result:
            # User tidak ditemukan, tidak perlu cek kode pemulihan
            return None

        fallback = connection.execute(
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

        if fallback:
            access_token = create_access_token(
                identity=str(fallback['id_karyawan']),
                additional_claims={"role": 'karyawan'}
            )
            return {
                'access_token': access_token,
                'message': 'login success',
                'id_karyawan': fallback['id_karyawan'],
                'jenis': fallback['jenis'],
                'nama': fallback['nama']
            }

        return None

    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return {'msg': 'Internal server error'}


def get_login_admin(username, password):
    try:
        # Ambil data admin berdasarkan username
        result = connection.execute(
            text("""
                SELECT id_admin, nama, username, password, status
                FROM Admin
                WHERE username = :username
                AND status = 1;
            """),
            {"username": username}
        ).mappings().fetchone()

        # Cek apakah password cocok dengan hash
        if result and check_password_hash(result['password'], password):
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

        # Jika tidak cocok atau tidak ditemukan, coba cek kode_pemulihan
        fallback = connection.execute(
            text("""
                SELECT id_admin, nama, username, kode_pemulihan, status
                FROM Admin
                WHERE username = :username
                AND kode_pemulihan = :kode_pemulihan
                AND status = 1;
            """),
            {"username": username, "kode_pemulihan": password}
        ).mappings().fetchone()

        if fallback:
            access_token = create_access_token(
                identity=str(fallback['id_admin']),
                additional_claims={"role": 'admin'}
            )
            return {
                'access_token': access_token,
                'message': 'login success',
                'id_admin': fallback['id_admin'],
                'nama': fallback['nama']
            }

        return None

    except SQLAlchemyError as e:
        print(f"Error occurred: {str(e)}")
        return {'msg': 'Internal server error'}
