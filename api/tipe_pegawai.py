from flask import logging, request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from .utils.decorator import role_required
from .query.q_tipe_pegawai import *


tipe_pegawai_ns = Namespace("tipe-pegawai", description="Tipe pegawai related endpoints")

tipe_model = tipe_pegawai_ns.model("TipePegawai", {
    "tipe": fields.String(required=True, description="Tipe pegawai baru"),
})

@tipe_pegawai_ns.route('/')
class TipePegawaiListResource(Resource):
    @role_required('admin')
    def get(self):
        """Akses: (admin), Mengambil list semua tipe pegawai"""
        try:
            result = get_all_tipe_pegawai()
            if not result:
                return {'status': 'error', 'message': 'Tidak ada tipe pegawai yang ditemukan'}, 401
            return result, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        
    @tipe_pegawai_ns.expect(tipe_model)
    @role_required('admin')
    def post(self):
        """Akses: (admin), Menambahkan tipe pegawai baru"""
        payload = request.get_json()
        try:
            new_tipe = insert_tipe_pegawai(payload)
            if not new_tipe:
                return {"status": "Gagal menambahkan tipe pegawai baru"}, 401
            return {"data": new_tipe, "status": f"Tipe pegawai {new_tipe['tipe'].title()} berhasil ditambahkan"}, 201
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        

@tipe_pegawai_ns.route('/<int:id_tipe>')
class TipePegawaiDetailResource(Resource):
    @jwt_required()
    def get(self, id_tipe):
        """Akses: (admin, karyawan), Mengambil data tipe berdasarkan ID"""
        try:
            tipe = get_tipe_by_id(id_tipe)
            if not tipe:
                return {'status': 'error', 'message': 'Tidak ada tipe yang ditemukan'}, 401
            return {'data': tipe}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        
    @role_required('admin')
    @tipe_pegawai_ns.expect(tipe_model)
    def put(self, id_tipe):
        """Akses: (admin), Edit data tipe berdasarkan ID"""
        payload = request.get_json()
        try:
            updated = update_tipe(id_tipe, payload)
            if not updated:
                return {'status': 'error', "message": "Tipe pegawai tidak ditemukan"}, 401
            return {"status": f"{updated[0].title()} berhasil diupdate"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500  
        
    @role_required('admin')
    def delete(self, id_tipe):
        """Akses: (admin), Delete tipe berdasarkan ID"""
        try:
            deleted = delete_tipe(id_tipe)
            if not deleted:
                return {'status': 'error', "message": "Tipe pegawai tidak ditemukan"}, 401
            return {"status": f"{deleted[0].title()} berhasil dihapus"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500 