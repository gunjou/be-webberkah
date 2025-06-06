import os
from datetime import datetime
from flask import Blueprint, abort, request, send_file
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from .decorator import role_required
from .query import add_permohonan_izin, approve_izin, check_izin, create_notifikasi, get_all_izin_by_date, get_id_karyawan_from_izin, get_karyawan, reject_izin, remove_pengajuan
from .config import get_allowed_extensions


# Path root ke folder lampiran (harus sama dengan tempat file disimpan saat upload)
BASE_UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))
perizinan_bp = Blueprint('api', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in get_allowed_extensions()

"""<-- Karyawan Side -->"""
@perizinan_bp.route('/pengajuan-izin', methods=['POST'])
@role_required('karyawan')
def pengajuan_izin():
    from flask_jwt_extended import get_jwt_identity
    id_karyawan = get_jwt_identity()
    karyawan = get_karyawan(id_karyawan)

    # Ambil data dari form
    id_jenis = request.form.get('jenis_izin', type=int)
    tgl_mulai = request.form.get('tgl_mulai')
    tgl_selesai = request.form.get('tgl_selesai')
    keterangan = request.form.get('keterangan')
    file = request.files.get('lampiran')

    # Validasi dasar
    if not all([id_jenis, tgl_mulai, tgl_selesai, keterangan]):
        return {'status': "Semua kolom harus diisi"}, 400

    # Mapping jenis
    jenis_map = {3: 'izin', 4: 'sakit'}
    jenis_label = jenis_map.get(id_jenis)
    if not jenis_label:
        return {'status': "Jenis izin tidak valid"}, 400

    # Validasi lampiran hanya untuk sakit
    if id_jenis == 4 and not file:
        return {'status': "Lampiran wajib diunggah untuk izin sakit"}, 400

    # Simpan file jika ada
    path_lampiran = None
    if file:
        if not allowed_file(file.filename):
            return {'status': "Format file tidak diperbolehkan"}, 400

        ekstensi = file.filename.rsplit('.', 1)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = secure_filename(f"lampiran_{jenis_label}_{timestamp}.{ekstensi}")

        # Gunakan BASE_UPLOAD_FOLDER
        folder_path = os.path.join(BASE_UPLOAD_FOLDER, datetime.now().strftime('%Y/%m'))
        os.makedirs(folder_path, exist_ok=True)

        full_path = os.path.join(folder_path, filename)
        file.save(full_path)

        # Ambil path relatif dari BASE_UPLOAD_FOLDER
        rel_path = os.path.relpath(full_path, BASE_UPLOAD_FOLDER)
        path_lampiran = rel_path  # <- ini yang akan disimpan ke DB

    # Simpan data ke DB
    id_izin = add_permohonan_izin(id_karyawan, id_jenis, tgl_mulai, tgl_selesai, keterangan, path_lampiran)
    create_notifikasi(
        id_karyawan=None,  # untuk admin
        role_user='admin',
        jenis='izin',
        subject='Pengajuan Izin Baru',
        pesan=f"{karyawan['nama']} mengajukan izin dari {tgl_mulai} sampai {tgl_selesai}."
    )

    if id_izin is None:
        return {'status': "Gagal mengirimkan permohonan izin"}, 500

    return {'status': "Berhasil mengirimkan permohonan izin", 'id_izin': id_izin}, 201

@perizinan_bp.route('/hapus-pengajuan/<int:id_izin>', methods=['DELETE'])
@role_required('karyawan')
def hapus_pengajuan(id_izin):
    try:
        result = remove_pengajuan(id_izin)
        if result is None or result == 0:
            return {'status': "Gagal menghapus permohonan izin"}, 500
        return {'status': "Berhasil menghapus permohonan izin"}, 200
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@perizinan_bp.route('/check-izin', methods=['GET'])
@role_required('karyawan')
def lihat_izin():
    from flask_jwt_extended import get_jwt_identity
    from datetime import datetime, date

    id_karyawan = get_jwt_identity()

    # Ambil tanggal dari query param, default ke hari ini
    tanggal_str = request.args.get('tanggal')
    try:
        if tanggal_str:
            tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
        else:
            tanggal = date.today()

        detail_izin = check_izin(id_karyawan, tanggal)

        if not detail_izin:
            return {'status': 'success', 'data': None}, 200

        # Format tanggal dan hitung jumlah hari
        tgl_mulai = datetime.strptime(str(detail_izin['tgl_mulai']), '%Y-%m-%d')
        tgl_selesai = datetime.strptime(str(detail_izin['tgl_selesai']), '%Y-%m-%d')
        jumlah_hari = (tgl_selesai - tgl_mulai).days + 1

        detail_izin['tgl_mulai'] = tgl_mulai.strftime('%d-%m-%Y')
        detail_izin['tgl_selesai'] = tgl_selesai.strftime('%d-%m-%Y')
        detail_izin['durasi_izin'] = jumlah_hari

        return {'status': 'success', 'data': detail_izin}, 200

    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500


"""<-- Admin Side -->"""
@perizinan_bp.route('/izin/list', methods=['GET'])
@role_required('admin')
def list_izin():
    from datetime import datetime

    tanggal = request.args.get('tanggal')  # format: YYYY-MM-DD

    # Validasi format tanggal jika diberikan
    if tanggal:
        try:
            datetime.strptime(tanggal, '%Y-%m-%d')
        except ValueError:
            return {'status': 'error', 'message': 'Format tanggal tidak valid (YYYY-MM-DD)'}, 400

    try:
        data_izin = get_all_izin_by_date(tanggal)

        for izin in data_izin:
            try:
                tgl_mulai = datetime.strptime(str(izin['tgl_mulai']), '%Y-%m-%d')
                tgl_selesai = datetime.strptime(str(izin['tgl_selesai']), '%Y-%m-%d')
                izin['durasi_izin'] = (tgl_selesai - tgl_mulai).days + 1  # inklusif
            except Exception as parse_err:
                izin['durasi_izin'] = None  # fallback jika error parsing

        return {'status': 'success', 'data': data_izin, 'count': len(data_izin)}, 200

    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@perizinan_bp.route('/izin/<int:id_izin>/approve', methods=['POST'])
@role_required('admin')
def izin_diterima(id_izin):
    try:
        approve_izin(id_izin)
        id_karyawan = get_id_karyawan_from_izin(id_izin)
        create_notifikasi(
            id_karyawan=id_karyawan,
            role_user='karyawan',
            jenis='izin',
            subject='Status Permohonan Izin',
            pesan='Permohonan izin Anda telah disetujui.'  # atau ditolak
        )
        return {'status': 'success', 'message': 'Izin disetujui'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500
    
@perizinan_bp.route('/izin/<int:id_izin>/reject', methods=['POST'])
@role_required('admin')
def izin_ditolak(id_izin):
    alasan = request.json.get('alasan_penolakan', '')
    if not alasan:
        return {'status': 'error', 'message': 'Alasan penolakan wajib diisi'}, 400

    try:
        reject_izin(id_izin, alasan)
        id_karyawan = get_id_karyawan_from_izin(id_izin)
        create_notifikasi(
            id_karyawan=id_karyawan,
            role_user='karyawan',
            jenis='izin',
            subject='Status Permohonan Izin',
            pesan='Permohonan izin Anda telah ditolak.'  # atau disetujui
        )
        return {'status': 'success', 'message': 'Izin ditolak'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500
    

"""<-- Both Side -->"""
@perizinan_bp.route('/lampiran/<path:filename>', methods=['GET'])
@jwt_required()
def get_lampiran(filename):
    # Hanya izinkan akses dalam folder uploads
    full_path = os.path.join(BASE_UPLOAD_FOLDER, filename)
    safe_path = os.path.abspath(full_path)

    if not safe_path.startswith(BASE_UPLOAD_FOLDER) or not os.path.exists(safe_path):
        return abort(403)

    return send_file(safe_path)