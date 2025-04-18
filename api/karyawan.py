from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from .query import get_list_jenis, get_list_karyawan, add_jenis, add_karyawan, get_list_tipe, update_karyawan, remove_karyawan, get_karyawan
from .decorator import role_required

karyawan_bp = Blueprint('api', __name__)

'''<--- Table Jenis Karyawan --->'''
@karyawan_bp.route('/jenis', methods=['GET'])
# @role_required('admin')
def list_jenis():
    jenis_list = get_list_jenis()
    return {'jenis_karyawan': jenis_list}, 200  # OK


@karyawan_bp.route('/jenis', methods=['POST'])
@role_required('admin')
def tambah_jenis():
    jenis = request.json.get("jenis", None)

    if not jenis:
        return {'status': "Kolom 'jenis' tidak boleh kosong"}, 400  # Bad Request

    try:
        jenis_id = add_jenis(jenis)
        if jenis_id is None:
            return {'status': "Gagal menambahkan data"}, 500  # Internal Server Error
        return {'status': "Berhasil menambahkan data", 'jenis': jenis}, 201  # Created
    except SQLAlchemyError as e:
        return {'status': f"Gagal menambahkan data: {str(e)}"}, 500

@karyawan_bp.route('/tipe', methods=['GET'])
# @role_required('admin')
def list_tipe():
    tipe_list = get_list_tipe()
    return {'tipe_karyawan': tipe_list}, 200  # OK

'''<--- Table Karyawan --->'''
@karyawan_bp.route('/karyawan', methods=['GET'])
@role_required('admin')
def list_karyawan():
    karyawan_list = get_list_karyawan()  # Tidak perlu memanggil fetchall()
    
    # Karyawan_list sudah dalam format dictionary, jadi tidak perlu diubah lagi
    return {'karyawan': karyawan_list}, 200

@karyawan_bp.route('/karyawan', methods=['POST'])
@role_required('admin')
def tambah_karyawan():
    data = request.json
    jenis = data.get('jenis')
    tipe = data.get('tipe')
    nama = data.get('nama')
    gaji_pokok = data.get('gaji_pokok')
    username = data.get('username')
    kode_pemulihan = data.get('kode_pemulihan')

    if not all([jenis, tipe, nama, gaji_pokok, username, kode_pemulihan]):
        return {'status': "Semua kolom harus diisi"}, 400  # Bad Request

    karyawan_id = add_karyawan(jenis, tipe, nama, gaji_pokok, username, kode_pemulihan)
    
    if karyawan_id is None:
        return {'status': "Gagal menambahkan karyawan"}, 500  # Internal Server Error

    return {'status': "Berhasil menambahkan karyawan", 'nama': nama}, 201  # Created


@karyawan_bp.route('/karyawan/<int:id>', methods=['PUT'])
@role_required('admin')
def edit_karyawan(id):
    karyawan = get_karyawan(id)

    if karyawan is None:
        return {'status': "Karyawan tidak ditemukan"}, 404  # Not Found

    # Ambil data dari request
    jenis = request.json.get("jenis", None)
    tipe = request.json.get("tipe", None)
    nama = request.json.get("nama", None)
    gaji_pokok = request.json.get("gaji_pokok", None)
    username = request.json.get("username", None)
    kode_pemulihan = request.json.get("kode_pemulihan", None)

    # Perbarui data jika ada input baru
    if jenis is not None:
        karyawan['id_jenis'] = jenis
    if tipe is not None:
        karyawan['id_tipe'] = tipe
    if nama is not None:
        karyawan['nama'] = nama
    if gaji_pokok is not None:
        karyawan['gaji_pokok'] = gaji_pokok
    if username is not None:
        karyawan['username'] = username
    if kode_pemulihan is not None:
        karyawan['kode_pemulihan'] = kode_pemulihan

    result = update_karyawan(
        karyawan['id_karyawan'],
        karyawan['id_jenis'],
        karyawan['id_tipe'],
        karyawan['nama'],
        karyawan['gaji_pokok'],
        karyawan['username'],
        karyawan['kode_pemulihan']
    )
    
    if result is None or result == 0:
        return {'status': "Gagal memperbarui data karyawan"}, 500

    return {'status': f"Berhasil memperbarui data {karyawan['nama']}"}, 200


@karyawan_bp.route('/karyawan/delete/<int:id>', methods=['PUT'])
@role_required('admin')
def delete_karyawan(id):
    karyawan = get_karyawan(id)

    if not karyawan:
        return {'status': "Karyawan tidak ditemukan"}, 404

    try:
        nama_remove = karyawan['nama']
        result = remove_karyawan(karyawan['id_karyawan'])
        if result is None or result == 0:
            return {'status': "Gagal menghapus karyawan"}, 500
        return {'status': f"Berhasil menghapus {nama_remove}"}, 200
    except Exception as e:
        return {'status': f"Terjadi kesalahan: {str(e)}"}, 500
