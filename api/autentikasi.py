from flask import Blueprint, logging, request
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required

from .query import get_login_karyawan, get_login_admin


autentikasi_bp = Blueprint('api', __name__)

"""<- Login & Logout Pegawai ->"""
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
@jwt_required()  # Ensure the user is authenticated
def logout_karyawan():
    # In a simple implementation, you can just return a success message
    return {'status': "Successfully logged out"}, 200  # OK


"""<- Login & Logout Admin ->"""
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
@jwt_required()  # Ensure the user is authenticated
def logout_admin():
    # In a simple implementation, you can just return a success message
    return {'status': "Successfully logged out"}, 200  # OK