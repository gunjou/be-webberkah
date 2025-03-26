from flask import Blueprint, jsonify, request
from datetime import datetime

from .query import get_list_absensi, add_checkin, add_checkout
from .face_detection import verifikasi_wajah


absensi_bp = Blueprint('api', __name__)

@absensi_bp.route('/api/absensi', methods=['GET', 'POST', 'PUT'])
def absensi():
    id_karyawan = 1

    def hitung_selisih_waktu(jam_masuk, jam_keluar):
        selisih = (jam_keluar.hour * 60 + jam_keluar.minute) - (jam_masuk.hour * 60 + jam_masuk.minute)
        jam, menit = divmod(selisih, 60)
        
        return f"{jam} jam {menit} menit"

    if  request.method == 'GET':
        list_absensi = get_list_absensi().fetchall()
        result = [{
            'id': index + 1,
            'id_absensi': row[0],
            'id_karyawan': row[1],
            'nama': row[2],
            'id_jenis': row[3],
            'jenis': row[4],
            # 'nama': row[5],
            'tanggal': row[6].strftime("%d-%m-%Y"),
            'jam_masuk': row[7].strftime('%H:%M:%S'),
            'jam_keluar': row[8].strftime('%H:%M:%S'),
            'selisih': hitung_selisih_waktu(row[7], row[8])
            # 'created_at': row[9],
            # 'updated_at': row[10]
            } for index, row in enumerate(list_absensi)]
        return result
    
    elif request.method == 'POST':
        # Periksa apakah file gambar ada dalam request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400

        # Upload file
        image = request.files['file']

        # Periksa apakah file memiliki nama
        if image.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        face = verifikasi_wajah(id_karyawan, image)
        if face == True:
            # now = datetime.now()
            tanggal = datetime.now().date()
            jam_masuk = datetime.now().time()
            add_checkin(id_karyawan, tanggal, jam_masuk)
            return {'status': 'check in successed'}
        else:
            return {'status': 'face not match'}
    
    # Check out
    elif request.method == 'PUT':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400

        # Upload file
        image = request.files['file']

        # Periksa apakah file memiliki nama
        if image.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        face = verifikasi_wajah(id_karyawan, image)
        if face == True:
            # now = datetime.now()
            tanggal = datetime.now().date()
            jam_keluar = datetime.now().time()
            add_checkout(id_karyawan, tanggal, jam_keluar)
            return {'status': 'check out successed'}
        else:
            return {'status': 'face not match'}

    else:
        return {'status': 'Method not found'}, 404
    
