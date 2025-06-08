from flask import jsonify
from flask_restx import Namespace, Resource # type: ignore
# from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError


# from .utils.decorator import role_required
from .query.q_testdb import get_test_db


testdb_ns = Namespace("test-db", description="Test Database related endpoints")

@testdb_ns.route('/')
class TestDBResource(Resource):
    # @jwt_required()
    def get(self):
        """Akses: (admin, karyawan),  Mengambil list semua jenis pegawai"""
        try:
            result = get_test_db()
            if not result:
                return {'status': 'error', 'message': 'Tidak ada jenis pegawai yang ditemukan'}, 401
            return jsonify({'server_time': str(result)})
        except SQLAlchemyError as e:
            return jsonify({'error': str(e)}), 500
