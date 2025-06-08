from flask import logging, request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from .utils.decorator import role_required
from .query.q_jenis_pegawai import *


jenis_pegawai_ns = Namespace("jenis-pegawai", description="Jenis pegawai related endpoints")

jenis_model = jenis_pegawai_ns.model("JenisPegawai", {
    "jenis": fields.String(required=True, description="Jenis pegawai baru"),
})

@jenis_pegawai_ns.route('/')
class JenisPegawaiListResource(Resource):
    @jwt_required()
    def get(self):
        """Akses: (admin, karyawan),  Mengambil list semua jenis pegawai"""
        try:
            result = get_all_jenis_pegawai()
            if not result:
                return {'status': 'error', 'message': 'Tidak ada jenis pegawai yang ditemukan'}, 401
            return result, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        
    @role_required('admin')
    @jenis_pegawai_ns.expect(jenis_model)
    def post(self):
        """Akses: (admin),  Menambahkan jenis pegawai baru"""
        payload = request.get_json()
        try:
            new_jenis = insert_jenis_pegawai(payload)
            if not new_jenis:
                return {"status": "Gagal menambahkan jenis pegawai baru"}, 401
            return {"data": new_jenis, "status": f"Jenis pegawai {new_jenis['jenis'].title()} berhasil ditambahkan"}, 201
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        

@jenis_pegawai_ns.route('/<int:id_jenis>')
class JenisPegawaiDetailResource(Resource):
    @jwt_required()
    def get(self, id_jenis):
        """Akses: (admin, karyawan), Mengambil data jenis berdasarkan ID"""
        try:
            jenis = get_jenis_by_id(id_jenis)
            if not jenis:
                return {'status': 'error', 'message': 'Tidak ada jenis yang ditemukan'}, 401
            return {'data': jenis}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        
    @role_required('admin')
    @jenis_pegawai_ns.expect(jenis_model)
    def put(self, id_jenis):
        """Akses: (admin),  Edit data jenis berdasarkan ID"""
        payload = request.get_json()
        try:
            updated = update_jenis(id_jenis, payload)
            if not updated:
                return {'status': 'error', "message": "Jenis pegawai tidak ditemukan"}, 401
            return {"status": f"{updated[0].title()} berhasil diupdate"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500  
        
    @role_required('admin')
    def delete(self, id_jenis):
        """Akses: (admin), Delete jenis berdasarkan ID"""
        try:
            deleted = delete_jenis(id_jenis)
            if not deleted:
                return {'status': 'error', "message": "Jenis pegawai tidak ditemukan"}, 401
            return {"status": f"{deleted[0].title()} berhasil dihapus"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500 