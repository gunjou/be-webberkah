from datetime import datetime, date, time
import os
from flask import Blueprint, request
from werkzeug.utils import secure_filename
from flask_jwt_extended import get_jwt_identity

from .config import get_allowed_extensions
from .query import add_permohonan_lembur, approve_lembur, check_lembur, create_notifikasi, get_all_lembur_by_date, get_id_karyawan_from_lembur, get_karyawan, reject_lembur, remove_pengajuan_lembur
from .decorator import role_required


# Path root ke folder lampiran (harus sama dengan tempat file disimpan saat upload)
BASE_UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads'))
lembur_bp = Blueprint('api', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in get_allowed_extensions()

"""<-- Karyawan Side -->"""
@lembur_bp.route('/pengajuan-lembur', methods=['POST'])
@role_required('karyawan')
def pengajuan_lembur():
    id_karyawan = get_jwt_identity()
    karyawan = get_karyawan(id_karyawan)

    # Ambil data dari form
    tanggal = request.form.get('tanggal')
    jam_mulai = request.form.get('jam_mulai')
    jam_selesai = request.form.get('jam_selesai')
    deskripsi = request.form.get('deskripsi')
    file = request.files.get('lampiran')

    # Validasi kolom dasar
    if not all([tanggal, jam_mulai, jam_selesai, deskripsi]):
        return {'status': "Semua kolom wajib diisi"}, 400

    # Simpan file jika ada
    path_lampiran = None
    if file:
        if not allowed_file(file.filename):
            return {'status': "Format file tidak diperbolehkan"}, 400

        ekstensi = file.filename.rsplit('.', 1)[1].lower()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = secure_filename(f"lembur_{id_karyawan}_{timestamp}.{ekstensi}")

        # Gunakan BASE_UPLOAD_FOLDER
        folder_path = os.path.join(BASE_UPLOAD_FOLDER, datetime.now().strftime('%Y/%m'))
        os.makedirs(folder_path, exist_ok=True)

        full_path = os.path.join(folder_path, filename)
        file.save(full_path)

        # Ambil path relatif dari BASE_UPLOAD_FOLDER
        rel_path = os.path.relpath(full_path, BASE_UPLOAD_FOLDER)
        path_lampiran = rel_path  # <- ini yang akan disimpan ke DB

    # Simpan ke DB
    id_lembur = add_permohonan_lembur(id_karyawan, tanggal, jam_mulai, jam_selesai, deskripsi, path_lampiran)
    create_notifikasi(
        id_karyawan=None,
        role_user='admin',
        jenis='lembur',
        subject='Pengajuan Lembur Baru',
        pesan=f"{karyawan['nama']} mengajukan lembur pada {tanggal} pukul {jam_mulai} - {jam_selesai}."
    )

    if id_lembur is None:
        return {'status': "Gagal mengirimkan permohonan lembur"}, 500

    return {'status': "Berhasil mengirimkan permohonan lembur", 'id_lembur': id_lembur}, 201

@lembur_bp.route('/hapus-lembur/<int:id_lembur>', methods=['DELETE'])
@role_required('karyawan')
def hapus_lembur(id_lembur):
    try:
        result = remove_pengajuan_lembur(id_lembur)
        if result is None or result == 0:
            return {'status': "Gagal menghapus pengajuan lembur"}, 500
        return {'status': "Berhasil menghapus pengajuan lembur"}, 200
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500
    
@lembur_bp.route('/check-lembur', methods=['GET'])
@role_required('karyawan')
def lihat_lembur():
    from flask_jwt_extended import get_jwt_identity

    id_karyawan = get_jwt_identity()

    # Ambil tanggal dari parameter query jika ada, kalau tidak gunakan hari ini
    tanggal_str = request.args.get('tanggal')
    try:
        if tanggal_str:
            tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
        else:
            tanggal = date.today()

        detail_lembur = check_lembur(id_karyawan, tanggal)

        if not detail_lembur:
            return {'status': 'success', 'data': None}, 200

        # Format ulang jam dan tanggal (opsional)
        detail_lembur['tanggal'] = detail_lembur['tanggal'].strftime('%d-%m-%Y')
        detail_lembur['jam_mulai'] = detail_lembur['jam_mulai'].strftime('%H:%M')
        detail_lembur['jam_selesai'] = detail_lembur['jam_selesai'].strftime('%H:%M')

        return {'status': 'success', 'data': detail_lembur}, 200

    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500


"""<-- Admin Side -->"""
@lembur_bp.route('/lembur/list', methods=['GET'])
@role_required('admin')
def list_lembur():
    tanggal = request.args.get('tanggal')  # format: YYYY-MM-DD

    # Validasi format tanggal jika ada
    if tanggal:
        try:
            datetime.strptime(tanggal, '%Y-%m-%d')
        except ValueError:
            return {'status': 'error', 'message': 'Format tanggal tidak valid (YYYY-MM-DD)'}, 400

    try:
        data_lembur = get_all_lembur_by_date(tanggal)

        for lembur in data_lembur:
            try:
                # Konversi jam ke string agar JSON-serializable
                jam_mulai = lembur['jam_mulai'].strftime('%H:%M') if isinstance(lembur['jam_mulai'], time) else str(lembur['jam_mulai'])
                jam_selesai = lembur['jam_selesai'].strftime('%H:%M') if isinstance(lembur['jam_selesai'], time) else str(lembur['jam_selesai'])

                lembur['jam_mulai'] = jam_mulai
                lembur['jam_selesai'] = jam_selesai

                # Hitung durasi (dalam jam)
                jm = datetime.strptime(jam_mulai, '%H:%M')
                js = datetime.strptime(jam_selesai, '%H:%M')
                lembur['durasi_lembur'] = (js - jm).seconds // 3600
            except Exception:
                lembur['durasi_lembur'] = None


        return {'status': 'success', 'data': data_lembur, 'count': len(data_lembur)}, 200

    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@lembur_bp.route('/lembur/<int:id_lembur>/approve', methods=['POST'])
@role_required('admin')
def lembur_diterima(id_lembur):
    try:
        approve_lembur(id_lembur)
        id_karyawan = get_id_karyawan_from_lembur(id_lembur)
        create_notifikasi(
            id_karyawan=id_karyawan,
            role_user='karyawan',
            jenis='lembur',
            subject='Status Permohonan Lembur',
            pesan='Permohonan lembur Anda telah disetujui.'  # atau ditolak
        )
        return {'status': 'success', 'message': 'Lembur disetujui'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

@lembur_bp.route('/lembur/<int:id_lembur>/reject', methods=['POST'])
@role_required('admin')
def lembur_ditolak(id_lembur):
    alasan = request.json.get('alasan_penolakan', '')
    if not alasan:
        return {'status': 'error', 'message': 'Alasan penolakan wajib diisi'}, 400

    try:
        reject_lembur(id_lembur, alasan)
        id_karyawan = get_id_karyawan_from_lembur(id_lembur)
        create_notifikasi(
            id_karyawan=id_karyawan,
            role_user='karyawan',
            jenis='lembur',
            subject='Status Permohonan Lembur',
            pesan='Permohonan lembur Anda telah ditolak.'  # atau disetujui
        )
        return {'status': 'success', 'message': 'Lembur ditolak'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500
