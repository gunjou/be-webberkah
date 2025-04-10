from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
import pytz
from datetime import time

from .config import get_timezone
from .query import get_list_absensi, add_checkin, update_checkout
from .face_detection import verifikasi_wajah
from .filter_radius import get_valid_office_name


absensi_bp = Blueprint('api', __name__)


def hitung_waktu_kerja(jam_masuk, jam_keluar):
    if jam_keluar is None:
        return 0  # Belum check-out, waktu kerja dianggap 0 menit

    total_masuk = jam_masuk.hour * 60 + jam_masuk.minute
    total_keluar = jam_keluar.hour * 60 + jam_keluar.minute

    selisih = total_keluar - total_masuk
    return max(selisih, 0)  # Hindari nilai negatif jika jam_keluar lebih kecil (data tidak valid)


def hitung_keterlambatan(jam_masuk):
    wita = pytz.timezone("Asia/Makassar")

    # Konversi ke waktu WITA jika aware
    if jam_masuk.tzinfo is not None:
        jam_masuk = jam_masuk.astimezone(wita).time()

    jam_masuk_batas = time(8, 0)  # Jam 08:00 WITA

    if jam_masuk <= jam_masuk_batas:
        return 0  # Tidak terlambat

    # Hitung selisih menit
    terlambat = (jam_masuk.hour * 60 + jam_masuk.minute) - (jam_masuk_batas.hour * 60 + jam_masuk_batas.minute)
    return terlambat


@absensi_bp.route('/absensi', methods=['GET'])
@jwt_required()
def absensi():
    list_absensi = get_list_absensi()
    result = [{
        'id': index + 1,
        'id_absensi': row['id_absensi'],
        'id_karyawan': row['id_karyawan'],
        'nama': row['nama'],
        'id_jenis': row['id_jenis'],
        'jenis': row['jenis'],
        'tanggal': row['tanggal'].strftime("%d-%m-%Y"),
        'jam_masuk': row['jam_masuk'].strftime('%H:%M') if row['jam_masuk'] else None,
        'jam_keluar': row['jam_keluar'].strftime('%H:%M') if row['jam_keluar'] else None,  # Menangani jam_keluar yang None
        'lokasi_masuk': row['lokasi_masuk'] if row['lokasi_masuk'] else None,
        'lokasi_keluar': row['lokasi_keluar'] if row['lokasi_keluar'] else None,
        'status_absen': (
            'Belum Check-in' if row['jam_masuk'] is None else
            'Belum Check-out' if row['jam_keluar'] is None else
            'Selesai bekerja'
        ),
        'waktu_terlambat': hitung_keterlambatan(row['jam_masuk']),
        'jumlah_jam_kerja': hitung_waktu_kerja(row['jam_masuk'], row['jam_keluar'])
    } for index, row in enumerate(list_absensi)]
    
    return {'absensi': result}, 200  # Mengembalikan hasil dalam format JSON
    
@absensi_bp.route('/wajah/<int:id_karyawan>', methods=['POST'])
def check_wajah(id_karyawan):
    # Periksa apakah file gambar ada dalam request
    # if 'file' not in request.files:
    #     return jsonify({'error': 'No file part in the request'}), 400

    # Upload file
    # image = request.files['file']
    image = 19

    # Periksa apakah file memiliki nama
    # if image.filename == '':
    #     return jsonify({'error': 'No selected file'}), 400
    
    # Verifikasi wajah
    face = verifikasi_wajah(id_karyawan, image)
    if face:
        
        if face is None:
            return jsonify({'status': 'Failed to record check-in'}), 500
        
        return jsonify({'status': 'wajah cocok'}), 200
    else:
        return jsonify({'status': 'wajah tidak cocok'}), 403
    
@absensi_bp.route('/absensi/<int:id_karyawan>', methods=['POST'])
@jwt_required()
def check_in(id_karyawan):
    # Periksa apakah file gambar ada dalam request
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada foto yang anda masukkan!'}), 400
    
    # Periksa apakah koordinat lokasi ada dalam request
    user_lat = request.form.get('latitude')  # Ambil dari form-data
    user_lon = request.form.get('longitude')  # Ambil dari form-data

    if not user_lat or not user_lon:
        return jsonify({'error': 'Anda belum memberikan lokasi!'}), 400

    # Konversi latitude dan longitude ke float
    try:
        user_lat = float(user_lat)
        user_lon = float(user_lon)
    except ValueError:
        return jsonify({'error': f'Format data lokasi anda salah. Latitude: {user_lat}, Longitude: {user_lon}'}), 400

    # Cek apakah user dalam radius lokasi yang diizinkan
    lokasi_absensi = get_valid_office_name(user_lat, user_lon)

    if lokasi_absensi is None:
        return jsonify({'status': 'error', 'message': 'Anda berada diluar lokasi kerja, lakukan absensi di lokasi yang sudah ditentukan!'}), 403

    # Upload file
    image = request.files['file']

    # Periksa apakah file memiliki nama
    if image.filename == '':
        return jsonify({'error': 'Anda belum memasukkan gambar!'}), 400
    
    # Verifikasi wajah
    face = verifikasi_wajah(id_karyawan, image)
    
    if face == "not_detected":
        return jsonify({'status': 'error', 'message': 'Wajah tidak terdeteksi dalam gambar. Pastikan wajah terlihat jelas!'}), 400
    elif face == "error":
        return jsonify({'status': 'error', 'message': 'Terjadi kesalahan saat memverifikasi wajah.'}), 500
    elif not face:
        return jsonify({'status': 'error', 'message': 'Wajah anda tidak sesuai dengan akun!'}), 403

    tanggal, jam_masuk = get_timezone()
    
    # Menambahkan check-in
    result = add_checkin(id_karyawan, tanggal, jam_masuk, lokasi_absensi)
    if result is None:
        return jsonify({'status': 'error', 'message': 'Data yang anda masukkan belum lengkap!'}), 500
    
    return jsonify({'status': 'Check-in succeeded', 'lokasi': lokasi_absensi}), 200

    
@absensi_bp.route('/absensi/<int:id_karyawan>', methods=['PUT'])
@jwt_required()
def check_out(id_karyawan):
    # Periksa apakah file gambar ada dalam request
    if 'file' not in request.files:
        return jsonify({'error': 'Tidak ada foto yang anda masukkan!'}), 400

    # Ambil latitude dan longitude dari form-data
    user_lat = request.form.get('latitude')
    user_lon = request.form.get('longitude')

    if not user_lat or not user_lon:
        return jsonify({'error': 'Anda belum memberikan lokasi!'}), 400

    # Konversi koordinat ke float
    try:
        user_lat = float(user_lat)
        user_lon = float(user_lon)
    except ValueError:
        return jsonify({'error': f'Format data lokasi anda salah. Latitude: {user_lat}, Longitude: {user_lon}'}), 400

    # Cek apakah user dalam radius lokasi yang diizinkan
    lokasi_absensi = get_valid_office_name(user_lat, user_lon)

    if lokasi_absensi is None:
        return jsonify({'status': 'error', 'message': 'Anda berada diluar lokasi kerja, lakukan absensi di lokasi yang sudah ditentukan!'}), 403

    # Upload file
    image = request.files['file']

    # Periksa apakah file memiliki nama
    if image.filename == '':
        return jsonify({'error': 'Anda belum memasukkan gambar!'}), 400
    
    # Verifikasi wajah
    face = verifikasi_wajah(id_karyawan, image)

    if face == "not_detected":
        return jsonify({'status': 'error', 'message': 'Wajah tidak terdeteksi dalam gambar. Pastikan wajah terlihat jelas!'}), 400
    elif face == "error":
        return jsonify({'status': 'error', 'message': 'Terjadi kesalahan saat memverifikasi wajah.'}), 500
    elif not face:
        return jsonify({'status': 'error', 'message': 'Wajah anda tidak sesuai dengan akun!'}), 403

    tanggal, jam_keluar = get_timezone()
    
    # Update jam keluar
    result = update_checkout(id_karyawan, tanggal, jam_keluar, lokasi_absensi)
    if result is None or result == 0:
        return jsonify({'status': 'error', 'message': 'Gagal mencatat absen pulang atau tidak ditemukan absen masuk sebelumnya'}), 500
    
    return jsonify({'status': 'Absen pulang berhasil', 'lokasi': lokasi_absensi}), 200