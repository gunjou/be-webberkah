from flask import logging, request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from .utils.decorator import role_required
from .query.q_pegawai import *

pegawai_ns = Namespace("pegawai", description="Pegawai related endpoints")

pegawai_model = pegawai_ns.model("Pegawai", {
    "id_jenis": fields.Integer(required=True, description="id jenis pegawai"),
    "id_tipe": fields.Integer(required=True, description="id tipe pegawai"),
    "nama": fields.String(required=True, description="nama pegawai"),
    "gaji_pokok": fields.Integer(required=True, description="gaji pokok pegawai"),
    "username": fields.String(required=True, description="username pegawai"),
    "password": fields.String(required=False, description="password pegawai"),
    "kode_pemulihan": fields.String(required=False, description="kode pemulihan pegawai"),
})

password_model = pegawai_ns.model("GantiPasswordPegawai", {
    "password": fields.String(required=True, description="Password baru pegawai"),
    "konfir_password": fields.String(required=True, description="Konfirmasi assword baru pegawai"),
})      

@pegawai_ns.route('/')
class PegawaiListResource(Resource):
    @role_required('admin')
    def get(self):
        """Akses: (admin), Mengambil list semua pegawai"""
        try:
            result = get_all_pegawai()
            if not result:
                return {'status': 'error', 'message': 'Tidak ada pegawai yang ditemukan'}, 401
            return result, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        
    @pegawai_ns.expect(pegawai_model)
    @role_required('admin')
    def post(self):
        """Akses: (admin), Menambahkan pegawai baru"""
        payload = request.get_json()
        try:
            new_pegawai = insert_pegawai(payload)
            if not new_pegawai:
                return {"status": "Gagal menambahkan pegawai baru"}, 401
            return {"data": new_pegawai, "status": f"Pegawai baru dengan nama {new_pegawai['nama'].title()} berhasil ditambahkan"}, 201
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        

@pegawai_ns.route('/<int:id_karyawan>')
class PegawaiDetailResource(Resource):
    @jwt_required()
    def get(self, id_karyawan):
        """Akses: (admin, karyawan), Mengambil data pegawai berdasarkan ID"""
        try:
            pegawai = get_pegawai_by_id(id_karyawan)
            if not pegawai:
                return {'status': 'error', 'message': 'Tidak ada pegawai yang ditemukan'}, 401
            return {'data': pegawai}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500
        
    @pegawai_ns.expect(pegawai_model)
    @jwt_required()
    def put(self, id_karyawan):
        """Akses: (admin, karyawan), Edit data pegawai berdasarkan ID"""
        payload = request.get_json()
        try:
            print(payload)
            updated = update_pegawai(id_karyawan, payload)
            if not updated:
                return {'status': 'error', "message": "Pegawai tidak ditemukan"}, 401
            return {"status": f"Data pegawai {updated[0].title()} berhasil diupdate"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500  
        
    @role_required('admin')
    def delete(self, id_karyawan):
        """Akses: (admin), Delete pegawai berdasarkan ID"""
        try:
            deleted = delete_pegawai(id_karyawan)
            if not deleted:
                return {'status': 'error', "message": "Pegawai tidak ditemukan"}, 401
            return {"status": f"Data pegawai {deleted[0].title()} berhasil dihapus"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500 
        

@pegawai_ns.route('/<int:id_karyawan>/password')
class PegawaiPasswordResource(Resource):
    @pegawai_ns.expect(password_model)
    @role_required('karyawan')
    def put(self, id_karyawan):
        """Akses: (karyawan), Mengubah password pegawai"""
        payload = request.get_json()
        # Validasi form kosong
        if not payload.get("password") or not payload.get("konfir_password"):
            return {"status": "error", "message": "Semua field harus diisi"}, 400
        # Validasi password sama
        if payload['password'] != payload['konfir_password']:
            return {"status": "error", "message": "Password dan konfirmasi tidak sama"}, 400
        # Lanjut ke proses ganti password
        try:
            result = change_password_pegawai(id_karyawan, payload["password"])
            if not result:
                return {"status": "Gagal mengganti password"}, 401
            return {"status": f"Password {result[0].title()} berhasil diganti"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {"status": "Internal server error"}, 500
