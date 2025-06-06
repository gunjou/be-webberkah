from flask import Blueprint, logging, request
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required, get_jwt

from .query import get_login_karyawan, get_login_admin
from .decorator import role_required
from .blacklist_store import blacklist


autentikasi_bp = Blueprint('api', __name__)

"""<-- Chck token -->"""
@autentikasi_bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    return {'status': 'Token masih valid'}, 200

"""<-- Login & Logout Pegawai -->"""
@autentikasi_bp.route('/login/karyawan', methods=['POST'])
def login_karyawan():
    auth = request.get_json()
    username = auth.get('username')
    password = auth.get('password')

    # Validate input
    if not username or not password:
        return {'status': "Fields can't be blank"}, 400  # Bad Request

    try:
        get_jwt_response = get_login_karyawan(username, password)
        if get_jwt_response is None:
            return {'status': "Invalid username or password"}, 401  # Unauthorized

        return get_jwt_response, 200  # OK
    except SQLAlchemyError as e:
        logging.error(f"Database error: {str(e)}")
        return {'status': "Internal server error"}, 500  # Internal Server Error

@autentikasi_bp.route('/logout/karyawan', methods=['POST'])
@role_required('karyawan')
def logout_karyawan():
    jti = request.json.get('jti')
    if jti:
        blacklist.add(jti)
        return {"msg": "Logout successful"}, 200
    return {"msg": "Missing JTI"}, 400


"""<-- Login & Logout Admin -->"""
@autentikasi_bp.route('/login/admin', methods=['POST'])
def login_admin():
    auth = request.get_json()
    username = auth.get('username')
    password = auth.get('password')

    # Validate input
    if not username or not password:
        return {'status': "Fields can't be blank"}, 400  # Bad Request

    try:
        get_jwt_response = get_login_admin(username, password)
        if get_jwt_response is None:
            return {'status': "Invalid username or password"}, 401  # Unauthorized

        return get_jwt_response, 200  # OK
    except SQLAlchemyError as e:
        logging.error(f"Database error: {str(e)}")
        return {'status': "Internal server error"}, 500  # Internal Server Error

@autentikasi_bp.route('/logout/admin', methods=['POST'])
@role_required('admin')
def logout_admin():
    # In a simple implementation, you can just return a success message
    return {'status': "Successfully logged out"}, 200  # OK