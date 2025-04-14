from flask import Blueprint, jsonify, request
from datetime import date, datetime, time
import pytz
import re

from .config import get_timezone
from .decorator import role_required
from .query import get_list_absensi, add_checkin, update_checkout, get_list_tidak_hadir, get_check_presensi, update_absensi_times, remove_abseni
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
        return None  # Tidak terlambat

    # Hitung selisih menit
    terlambat = (jam_masuk.hour * 60 + jam_masuk.minute) - (jam_masuk_batas.hour * 60 + jam_masuk_batas.minute)
    return terlambat

def hitung_jam_kurang(jam_keluar):
    """
    Menghitung jumlah menit kekurangan jam kerja jika checkout sebelum jam 17:00.
    :param jam_keluar_str: string format "HH:MM:SS"
    :return: int (jumlah menit) atau None jika tidak ada kekurangan
    """
    waktu_ideal_pulang = time(17, 0)  # 17:00:00

    try:
        jam_keluar_obj = datetime.strptime(jam_keluar, "%H:%M:%S").time()
    except ValueError:
        return None  # Jika format waktu tidak valid

    if jam_keluar_obj < waktu_ideal_pulang:
        delta = datetime.combine(date.today(), waktu_ideal_pulang) - datetime.combine(date.today(), jam_keluar_obj)
        return int(delta.total_seconds() // 60)
    
    return None  # Jika checkout >= 17:00


"""<-- API Check in & Check out -->"""
@absensi_bp.route('/absensi/<int:id_karyawan>', methods=['POST'])
@role_required('karyawan')
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
    jam_terlambat = hitung_keterlambatan(jam_masuk)

    # Menambahkan check-in
    result = add_checkin(id_karyawan, tanggal, jam_masuk, lokasi_absensi, jam_terlambat)
    if result is None:
        return jsonify({'status': 'error', 'message': 'Data yang anda masukkan belum lengkap!'}), 500
    
    return jsonify({'status': 'Check-in succeeded', 'lokasi': lokasi_absensi}), 200

@absensi_bp.route('/absensi/<int:id_karyawan>', methods=['PUT'])
@role_required('karyawan')
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

    cek_presensi = get_check_presensi(id_karyawan)
    if not cek_presensi:
        return {"message": "Belum ada presensi"}, 200

    jam_masuk = cek_presensi.get("jam_masuk")
    if not jam_masuk:
        return {"message": "Belum ada jam masuk"}, 200

    jam_kurang = hitung_jam_kurang(jam_keluar)
    total_jam_kerja = hitung_waktu_kerja(jam_masuk, jam_keluar)

    # Update jam keluar
    result = update_checkout(id_karyawan, tanggal, jam_keluar, lokasi_absensi, jam_kurang, total_jam_kerja)
    if result is None or result == 0:
        return jsonify({'status': 'error', 'message': 'Gagal mencatat absen pulang atau tidak ditemukan absen masuk sebelumnya'}), 500
    
    return jsonify({'status': 'Absen pulang berhasil', 'lokasi': lokasi_absensi}), 200


"""<-- Get Presensi -->"""
@absensi_bp.route('/absensi/hadir', methods=['GET'])
@role_required('admin')
def absensi():
    tanggal_param = request.args.get('tanggal')  # Ambil query param ?tanggal=DD-MM-YYYY

    try:
        if tanggal_param:
            tanggal_filter = datetime.strptime(tanggal_param, "%d-%m-%Y").date()
        else:
            tanggal_filter, _ = get_timezone()  # default: hari ini
    except ValueError:
        return {'status': 'Format tanggal tidak valid. Gunakan DD-MM-YYYY'}, 400

    list_absensi = get_list_absensi(tanggal_filter)
    result = [{
        'id': index + 1,
        'id_absensi': row['id_absensi'],
        'id_karyawan': row['id_karyawan'],
        'nama': row['nama'],
        'id_jenis': row['id_jenis'],
        'jenis': row['jenis'],
        'tanggal': row['tanggal'].strftime("%d-%m-%Y"),
        'jam_masuk': row['jam_masuk'].strftime('%H:%M') if row['jam_masuk'] else None,
        'jam_keluar': row['jam_keluar'].strftime('%H:%M') if row['jam_keluar'] else None,
        'jam_terlambat': row['jam_terlambat'],
        'jam_kurang': row['jam_kurang'],
        'total_jam_kerja': row['total_jam_kerja'],
        'lokasi_masuk': row['lokasi_masuk'] if row['lokasi_masuk'] else None,
        'lokasi_keluar': row['lokasi_keluar'] if row['lokasi_keluar'] else None,
        'id_presensi': row['id_presensi'],
        'status_presensi': row['status_presensi'],
        'status_absen': (
            'Belum Check-in' if row['jam_masuk'] is None else
            'Belum Check-out' if row['jam_keluar'] is None else
            'Selesai bekerja'
        )
    } for index, row in enumerate(list_absensi)]
    
    return {'absensi': result}, 200

@absensi_bp.route('/absensi/tidak_hadir', methods=['GET'])
@role_required('admin')
def absensi_tidak_hadir():
    tanggal_param = request.args.get('tanggal')  # Ambil query param ?tanggal=DD-MM-YYYY

    try:
        if tanggal_param:
            tanggal_filter = datetime.strptime(tanggal_param, "%d-%m-%Y").date()
        else:
            tanggal_filter, _ = get_timezone()
    except ValueError:
        return {'status': 'Format tanggal tidak valid. Gunakan DD-MM-YYYY'}, 400

    list_tidak_hadir = get_list_tidak_hadir(tanggal_filter)

    result = [{
        "id": index + 1,
        "id_karyawan": row["id_karyawan"],
        "nama": row["nama"],
        "id_jenis": row["id_jenis"],
        "jenis": row["jenis"],
        'tanggal': row['tanggal'].strftime("%d-%m-%Y"),
        "status_absen": "Tanpa Keterangan"
    } for index, row in enumerate(list_tidak_hadir)]
    
    return {'absensi': result}, 200

@absensi_bp.route('/absensi/edit/<int:id_absensi>', methods=['PUT'])
@role_required('admin')
def edit_absensi(id_absensi):
    data = request.json
    jam_masuk = data.get("jam_masuk")
    jam_keluar = data.get("jam_keluar")

    # Validasi format waktu HH:MM
    def is_valid_time_format(t):
        return bool(re.match(r"^\d{2}:\d{2}$", t))

    if not jam_masuk:
        return {'status': 'Jam masuk wajib diisi'}, 400
    if not is_valid_time_format(jam_masuk):
        return {'status': 'Format jam masuk tidak valid. Gunakan format HH:MM'}, 400
    if jam_keluar and not is_valid_time_format(jam_keluar):
        return {'status': 'Format jam keluar tidak valid. Gunakan format HH:MM'}, 400

    # Jika jam_keluar berupa string kosong, perlakukan sebagai None
    if jam_keluar == "":
        jam_keluar = None
        total_jam_kerja = None
    else:
        total_jam_kerja = hitung_waktu_kerja(
            datetime.strptime(jam_masuk, "%H:%M").time(),
            datetime.strptime(jam_keluar, "%H:%M").time()
        )
        jam_kurang = hitung_jam_kurang(jam_keluar)

    jam_terlambat = hitung_keterlambatan(datetime.strptime(jam_masuk, "%H:%M").time())

    result = update_absensi_times(id_absensi, jam_masuk, jam_keluar, jam_terlambat, jam_kurang, total_jam_kerja)

    if result is None:
        return {'status': 'Terjadi kesalahan saat memperbarui data'}, 500
    if result == 0:
        return {'status': 'Data tidak ditemukan atau tidak berhasil diperbarui'}, 404

    return {'status': 'Data absensi berhasil diperbarui'}, 200

@absensi_bp.route('/absensi/delete/<int:id_absensi>', methods=['PUT'])
@role_required('admin')
def delete_absensi(id_absensi):
    try:
        result = remove_abseni(id_absensi)
        if result is None or result == 0:
            return {'status': "Gagal menghapus absensi"}, 500
        return {'status': "Berhasil menghapus absensi"}, 200
    except Exception as e:
        return {'status': f"Terjadi kesalahan: {str(e)}"}, 500