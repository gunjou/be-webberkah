from flask import logging, request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from .utils.decorator import role_required
from .query.q_admin import *

admin_ns = Namespace("admin", description="Admin related endpoints")

admin_model = admin_ns.model("Admin", {
    "nama": fields.String(required=True, description="nama admin"),
    "username": fields.String(required=True, description="username admin"),
    "kode_pemulihan": fields.String(required=True, description="kode pemulihan admin"),
})

password_model = admin_ns.model("GantiPasswordAdmin", {
    "password": fields.String(required=True, description="Password baru admin"),
    "konfir_password": fields.String(required=True, description="Konfirmasi password baru admin"),
})


@admin_ns.route('/')
class AdminListResource(Resource):
    @role_required('admin')
    def get(self):
        """Akses: (admin), Mengambil list semua admin"""
        try:
            result = get_all_admin()
            if not result:
                return {'status': 'error', 'message': 'Tidak ada admin yang ditemukan'}, 401
            return result, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        
    @role_required('admin')
    @admin_ns.expect(admin_model)
    def post(self):
        """Akses: (admin), Menambahkan admin baru"""
        payload = request.get_json()
        try:
            new_admin = insert_admin(payload)
            if not new_admin:
                return {"status": "Gagal menambahkan admin"}, 401
            return {"data": new_admin, "status": f"Admin {new_admin['nama_admin']} berhasil ditambahkan"}, 201
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        

@admin_ns.route('/<int:id_admin>')
class AdminDetailResource(Resource):
    @role_required('admin')
    def get(self, id_admin):
        """Akses: (admin), Mengambil data admin berdasarkan ID"""
        try:
            admin = get_admin_by_id(id_admin)
            if not admin:
                return {'status': 'error', 'message': 'Tidak ada admin yang ditemukan'}, 401
            return {'data': admin}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        
    @role_required('admin')
    @admin_ns.expect(admin_model)
    def put(self, id_admin):
        """Akses: (admin), Edit data admin berdasarkan ID"""
        payload = request.get_json()
        try:
            updated = update_admin(id_admin, payload)
            if not updated:
                return {'status': 'error', "message": "Admin tidak ditemukan"}, 401
            return {"status": f"{updated[0]} berhasil diupdate"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500  
        
    @role_required('admin')
    def delete(self, id_admin):
        """Akses: (admin), Delete admin berdasarkan ID"""
        try:
            deleted = delete_admin(id_admin)
            if not deleted:
                return {'status': 'error', "message": "Admin tidak ditemukan"}, 401
            return {"status": f"{deleted[0]} berhasil dihapus"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500 
        

@admin_ns.route('/<int:id_admin>/password')
class AdminPasswordResource(Resource):
    @admin_ns.expect(password_model)
    @role_required('admin')
    def put(self, id_admin):
        """Akses: (admin), Mengubah password admin"""
        payload = request.get_json()
        # Validasi field kosong
        if not payload.get("password") or not payload.get("konfir_password"):
            return {"status": "error", "message": "Semua field harus diisi"}, 400
        # Validasi password dan konfirmasi harus sama
        if payload["password"] != payload["konfir_password"]:
            return {"status": "error", "message": "Password dan konfirmasi tidak sama"}, 400
        try:
            result = change_password_admin(id_admin, payload["password"])
            if not result:
                return {"status": "Gagal mengganti password"}, 401
            return {"status": f"Password {result[0].title()} berhasil diganti"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {"status": "Internal server error"}, 500
