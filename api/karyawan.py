from flask import Blueprint, request

from .query import get_list_jenis, get_list_karyawan, add_jenis, add_karyawan, update_karyawan, remove_karyawan


karyawan_bp = Blueprint('api', __name__)

# Table Jenis Karyawan
@karyawan_bp.route('/api/jenis', methods=['GET'])
def list_jenis():
    list_jenis = get_list_jenis().fetchall()
    result = [{
        'id_jenis': row[0],
        'jenis': row[1]
        # 'created_at': row[4],
        # 'updated_at': row[5]
        } for row in list_jenis]
    return result

@karyawan_bp.route('/api/jenis', methods=['POST'])
def tambah_jenis():
    jenis = request.json.get("jenis", None)

    if not jenis:
        return {'status': "field can't blank"}, 403
    else:
        try:
            add_jenis(jenis)
            return {'status': "Success add data"}, 200
        except:
            return {'status': "Add data failed"}, 403

# Table Karyawan
@karyawan_bp.route('/api/karyawan', methods=['GET'])
def list_karyawan():
    list_karyawan = get_list_karyawan().fetchall()
    # print(list_karyawan)
    result = [{
        'id_karyawan': row[0],
        'id_jenis': row[1],
        'jenis': row[2],
        'nama': row[3],
        'gaji_pokok': row[4],
        'username': row[5],
        'password': row[6]
        # 'created_at': row[4],
        # 'updated_at': row[5]
        } for row in list_karyawan]
    return result

@karyawan_bp.route('/api/karyawan', methods=['POST'])
def tambah_karyawan():
    jenis = request.json.get("jenis", None)
    nama = request.json.get("nama", None)
    gaji_pokok = request.json.get("gaji_pokok", None)
    username = request.json.get("username", None)
    password = request.json.get("password", None)

    if not jenis or not nama or not gaji_pokok or not username or not password:
        return {'status': "field can't blank"}, 403
    else:
        try:
            add_karyawan(jenis, nama, gaji_pokok, username, password)
            return {'status': "Success add data"}, 200
        except:
            return {'status': "Add data failed"}, 403

@karyawan_bp.route('/api/karyawan/<int:id>', methods=['PUT'])
def edit_karyawan(id):
    all_emp = list_karyawan()
    for emp in all_emp:
        print(emp)
        if emp['id_karyawan'] == id:
            data = emp

    jenis = request.json.get("jenis", None)
    nama = request.json.get("nama", None)
    gaji_pokok = request.json.get("gaji_pokok", None)
    username = request.json.get("username", None)
    password = request.json.get("password", None)

    if jenis is not None:
        data['id_jenis'] = jenis
    if nama is not None:
        data['nama'] = nama
    if gaji_pokok is not None:
        data['gaji_pokok'] = gaji_pokok
    if username is not None:
        data['username'] = username
    if password is not None:
        data['password'] = password

    update_karyawan(data['id_karyawan'], data['id_jenis'], data['nama'], data['gaji_pokok'], data['username'], data['password'])
    return {'status': "Success update data"}, 200

@karyawan_bp.route('/api/karyawan/delete/<int:id>', methods=['PUT'])
def delete_karyawan(id):
    all_emp = list_karyawan()
    for emp in all_emp:
        if emp['id_karyawan'] == id:
            data = emp

    remove_karyawan(data['id_karyawan'])
    return {'status': "Success delete data"}, 200

