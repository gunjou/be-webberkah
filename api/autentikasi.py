from flask import Blueprint, logging, request
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required

from .query import get_login


autentikasi_bp = Blueprint('api', __name__)


@autentikasi_bp.route('/login', methods=['POST'])
def login():
    auth = request.get_json()
    username = auth.get('username')
    password = auth.get('password')

    # Validate input
    if not username or not password:
        return {'status': "Fields can't be blank"}, 400  # Bad Request

    try:
        get_jwt_response = get_login(username, password)
        if get_jwt_response is None:
            return {'status': "Invalid username or password"}, 401  # Unauthorized

        return {'status': "Success", 'jwt': get_jwt_response}, 200  # OK
    except SQLAlchemyError as e:
        logging.error(f"Database error: {str(e)}")
        return {'status': "Internal server error"}, 500  # Internal Server Error

@autentikasi_bp.route('/logout', methods=['POST'])
@jwt_required()  # Ensure the user is authenticated
def logout():
    # In a simple implementation, you can just return a success message
    return {'status': "Successfully logged out"}, 200  # OK