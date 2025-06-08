from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy.exc import SQLAlchemyError

from .query.q_autentikasi import get_login_admin, get_login_karyawan
from .utils.decorator import role_required
from .utils.blacklist_store import blacklist

auth_ns = Namespace('auth', description='Endpoint Autentikasi Admin dan Karyawan')

login_model = auth_ns.model('Login', {
    'username': fields.String(required=True),
    'password': fields.String(required=True)
})

logout_model = auth_ns.model('Logout', {
    'jti': fields.String(required=True)
})

@auth_ns.route('/protected')
class ProtectedResource(Resource):
    @jwt_required()
    def get(self):
        """Akses: (admin, karyawan), Cek token masih valid"""
        return {'status': 'Token masih valid'}, 200


@auth_ns.route('/login/karyawan')
class LoginKaryawanResource(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        """Login karyawan menggunakan username + password atau kode pemulihan"""
        auth = request.get_json()
        username = auth.get('username')
        password = auth.get('password')

        if not username or not password:
            return {'status': "Fields can't be blank"}, 400

        try:
            get_jwt_response = get_login_karyawan(username, password)
            if get_jwt_response is None:
                return {'status': "Invalid username or password"}, 401
            return get_jwt_response, 200
        except SQLAlchemyError as e:
            auth_ns.logger.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500


@auth_ns.route('/logout/karyawan')
class LogoutKaryawanResource(Resource):
    @auth_ns.expect(logout_model)
    @role_required('karyawan')
    def post(self):
        """Akses: (karyawan), Logout karyawan dengan JTI blacklist"""
        jti = request.json.get('jti')
        if jti:
            blacklist.add(jti)
            return {"msg": "Logout successful"}, 200
        return {"msg": "Missing JTI"}, 400


@auth_ns.route('/login/admin')
class LoginAdminResource(Resource):
    @auth_ns.expect(login_model)
    def post(self):
        """Login admin menggunakan username + password atau kode pemulihan"""
        auth = request.get_json()
        username = auth.get('username')
        password = auth.get('password')

        if not username or not password:
            return {'status': "Fields can't be blank"}, 400

        try:
            get_jwt_response = get_login_admin(username, password)
            if get_jwt_response is None:
                return {'status': "Invalid username or password"}, 401
            return get_jwt_response, 200
        except SQLAlchemyError as e:
            auth_ns.logger.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500


@auth_ns.route('/logout/admin')
class LogoutAdminResource(Resource):
    @role_required('admin')
    def post(self):
        """Akses: (admin), Logout admin (simple endpoint)"""
        return {'status': "Successfully logged out"}, 200
