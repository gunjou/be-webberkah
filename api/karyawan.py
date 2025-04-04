from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from .query import get_list_jenis, get_list_karyawan, add_jenis, add_karyawan, update_karyawan, remove_karyawan, get_karyawan


karyawan_bp = Blueprint('api', __name__)

'''<--- Table Jenis Karyawan --->'''
@karyawan_bp.route('/api/jenis', methods=['GET'])
def list_jenis():
    jenis_list = get_list_jenis()  # Memanggil fungsi yang sudah dioptimalkan
    return {'jenis_karyawan': jenis_list}, 200  # Mengembalikan hasil dalam format JSON

@karyawan_bp.route('/api/jenis', methods=['POST'])
def tambah_jenis():
    jenis = request.json.get("jenis", None)

    if not jenis:
        return {'status': "Field can't be blank"}, 400  # Menggunakan 400 untuk Bad Request

    try:
        jenis_id = add_jenis(jenis)  # Menyimpan ID jenis yang baru ditambahkan
        if jenis_id is None:
            return {'status': "Add data failed"}, 500  # Menggunakan 500 untuk Internal Server Error
        return {'status': "Success add data", 'jenis': jenis}, 201  # Menggunakan 201 untuk Created
    except SQLAlchemyError as e:
        return {'status': f"Add data failed: {str(e)}"}, 500  # Mengembalikan pesan kesalahan


'''<--- Table Karyawan --->'''
@karyawan_bp.route('/api/karyawan', methods=['GET'])
@jwt_required()
def list_karyawan():
    karyawan_list = get_list_karyawan()  # Tidak perlu memanggil fetchall()
    
    # Karyawan_list sudah dalam format dictionary, jadi tidak perlu diubah lagi
    return {'karyawan': karyawan_list}, 200

@karyawan_bp.route('/api/karyawan', methods=['POST'])
def tambah_karyawan():
    data = request.json
    jenis = data.get('jenis')
    nama = data.get('nama')
    gaji_pokok = data.get('gaji_pokok')
    username = data.get('username')
    password = data.get('password')

    if not all([jenis, nama, gaji_pokok, username, password]):
        return {'status': "All fields are required"}, 400

    karyawan_id = add_karyawan(jenis, nama, gaji_pokok, username, password)
    
    if karyawan_id is None:
        return {'status': "Failed to add employee"}, 500

    return {'status': "Employee added successfully", 'nama': nama}, 201

@karyawan_bp.route('/api/karyawan/<int:id>', methods=['PUT'])
def edit_karyawan(id):
    # Mencari karyawan berdasarkan ID
    karyawan = get_karyawan(id)

    if karyawan is None:
        return {'status': "Employee not found"}, 404  # Mengembalikan 404 jika tidak ditemukan

    # Mengambil data dari request
    jenis = request.json.get("jenis", None)
    nama = request.json.get("nama", None)
    gaji_pokok = request.json.get("gaji_pokok", None)
    username = request.json.get("username", None)
    password = request.json.get("password", None)

    # Memperbarui data karyawan hanya jika ada input baru
    if jenis is not None:
        karyawan['id_jenis'] = jenis
    if nama is not None:
        karyawan['nama'] = nama
    if gaji_pokok is not None:
        karyawan['gaji_pokok'] = gaji_pokok
    if username is not None:
        karyawan['username'] = username
    if password is not None:
        karyawan['password'] = password

    # Memperbarui karyawan di database
    result = update_karyawan(karyawan['id_karyawan'], karyawan['id_jenis'], karyawan['nama'], karyawan['gaji_pokok'], karyawan['username'], karyawan['password'])
    
    if result is None or result == 0:
        return {'status': "Failed to update employee"}, 500  # Mengembalikan 500 jika gagal

    return {'status': "Success update data"}, 200  # Mengembalikan 200 jika berhasil

@karyawan_bp.route('/api/karyawan/delete/<int:id>', methods=['PUT'])
def delete_karyawan(id):
    # Mencari karyawan berdasarkan ID
    karyawan = get_karyawan(id)

    if not karyawan:
        return {'status': "Employee not found"}, 404

    # Mengubah status karyawan menjadi 0
    try:
        result = remove_karyawan(karyawan['id_karyawan'])
        if result is None or result == 0:
            return {'status': "Failed to update employee status"}, 500
        return {'status': "Success deleted employee"}, 200
    except Exception as e:
        return {'status': str(e)}, 500

