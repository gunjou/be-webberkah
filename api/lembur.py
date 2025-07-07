import calendar
from datetime import datetime, time
import os
from flask import current_app, request, send_from_directory, abort
from flask_restx import Namespace, Resource, fields, reqparse
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from .utils.decorator import role_required
from .query.q_lembur import *


lembur_ns = Namespace('lembur', description='Manajemen Pengajuan Lembur')

lembur_parser = lembur_ns.parser()
lembur_parser.add_argument('id_karyawan', type=int, required=False, location='form', help='Wajib diisi jika role admin')
lembur_parser.add_argument('tanggal', type=str, required=True, location='form', help='Format: DD-MM-YYYY')
lembur_parser.add_argument('jam_mulai', type=str, required=True, location='form', help='Format: HH:MM')
lembur_parser.add_argument('jam_selesai', type=str, required=True, location='form', help='Format: HH:MM')
lembur_parser.add_argument('keterangan', type=str, required=False, location='form', help='Keterangan lembur')
lembur_parser.add_argument('file', type=FileStorage, location='files', required=False, help='Path file jika ada')

# Daftar ekstensi file yang diizinkan
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@lembur_ns.route('/pengajuan')
class PengajuanLemburResource(Resource):
    @lembur_ns.expect(lembur_parser)
    @jwt_required()
    def post(self):
        """Akses: (admin/karyawan), Ajukan lembur"""
        args = lembur_parser.parse_args()
        file = args['file']
        current_user_id = get_jwt_identity()
        current_role = get_jwt()['role']  # Ambil role dari token

        # Tentukan id_karyawan
        if current_role == 'admin':
            if not args['id_karyawan']:
                return {'status': 'id_karyawan wajib diisi oleh admin'}, 400
            id_karyawan = args['id_karyawan']
        else:
            id_karyawan = current_user_id  # karyawan

        # Upload file jika ada
        path_lampiran = None
        if file and allowed_file(file.filename):
            today_str = datetime.now().strftime('%Y-%m')
            upload_dir = os.path.join(current_app.root_path, '..', 'uploads', 'lembur', today_str)
            os.makedirs(upload_dir, exist_ok=True)

            filename = secure_filename(file.filename)
            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)

            path_lampiran = os.path.join('uploads', 'lembur', today_str, filename)
        elif file:
            return {'status': 'Ekstensi file tidak diizinkan'}, 400

        tanggal = datetime.strptime(args['tanggal'], "%d-%m-%Y").date()

        if args['jam_mulai'] == args['jam_selesai']:
            return {'status': 'Jam mulai dan selesai tidak boleh sama'}, 400
        
        # Konversi jam_mulai
        if args['jam_mulai'].strip() == '24:00':
            jam_mulai = time(0, 0)
        else:
            try:
                jam_mulai = datetime.strptime(args['jam_mulai'], "%H:%M").time()
            except ValueError:
                return {'status': 'Format jam_mulai tidak valid (gunakan HH:MM)'}, 400
        # Konversi jam_selesai
        if args['jam_selesai'].strip() == '24:00':
            jam_selesai = time(0, 0)
        else:
            try:
                jam_selesai = datetime.strptime(args['jam_selesai'], "%H:%M").time()
            except ValueError:
                return {'status': 'Format jam_selesai tidak valid (gunakan HH:MM)'}, 400

        result_hitung = hitung_bayaran_lembur(id_karyawan, tanggal, jam_mulai, jam_selesai)
        if result_hitung is None:
            return {'status': 'Gagal menghitung bayaran lembur'}, 500

        data = {
            'id_karyawan': id_karyawan,
            'tanggal': tanggal,
            'jam_mulai': jam_mulai,
            'jam_selesai': jam_selesai,
            'keterangan': args['keterangan'],
            'path_lampiran': path_lampiran,
            'menit_lembur': result_hitung['menit_lembur'],
            'bayaran_perjam': result_hitung['bayaran_perjam'],
            'total_bayaran': result_hitung['total_bayaran']
        }

        result = insert_pengajuan_lembur(data)
        if result is None:
            return {'status': 'Gagal mengajukan lembur'}, 500

        return {'status': 'Pengajuan lembur berhasil direkam'}, 201


@lembur_ns.route('/')
class DaftarLemburResource(Resource):
    @jwt_required()
    @lembur_ns.doc(params={
        'status_lembur': 'Filter berdasarkan status lembur (pending, approved, rejected)',
        'id_karyawan': 'Filter berdasarkan ID karyawan',
        'tanggal': 'Filter lembur berdasarkan satu tanggal tertentu (format: YYYY-MM-DD)',
        'start_date': 'Tanggal mulai rentang pencarian lembur (format: YYYY-MM-DD)',
        'end_date': 'Tanggal akhir rentang pencarian lembur (format: YYYY-MM-DD)'
    })
    def get(self):
        """Akses: (admin, karyawan), Menampilkan data lembur dengan filter fleksibel berdasarkan status, karyawan, dan tanggal"""
        args = request.args
        status_lembur = args.get('status_lembur')
        id_karyawan = args.get('id_karyawan')
        tanggal_str = args.get('tanggal')
        start_date_str = args.get('start_date')
        end_date_str = args.get('end_date')

        try:
            tanggal = start_date = end_date = None

            # Validasi eksklusif: hanya boleh salah satu jenis filter
            if tanggal_str and (start_date_str or end_date_str):
                return {'status': 'error', 'message': 'Gunakan hanya salah satu: `tanggal` atau (`start_date` dan `end_date`)'}, 400

            if tanggal_str:
                tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
            elif start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            elif not tanggal_str and not start_date_str and not end_date_str:
                # fallback default: bulan ini
                today = date.today()
                start_date = date(today.year, today.month, 1)
                end_date = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
            else:
                return {'status': 'error', 'message': 'Untuk rentang tanggal, isi `start_date` dan `end_date` lengkap'}, 400

        except ValueError:
            return {'status': 'error', 'message': 'Format tanggal tidak valid. Gunakan YYYY-MM-DD'}, 400

        hasil = get_daftar_lembur(status_lembur, id_karyawan, start_date, end_date, tanggal)

        if hasil is None:
            return {'status': 'Gagal mengambil data lembur'}, 500

        return {'data': hasil}, 200


@lembur_ns.route('/preview/<path:relative_path>')
class PreviewLampiranLembur(Resource):
    @jwt_required()
    @lembur_ns.doc(
        security='Bearer Auth',
        description='Preview lampiran lembur (PDF/JPG/PNG)',
        params={'relative_path': 'Contoh: lampiran/lembur/2025-06/nama_file.pdf'}
    )
    def get(self, relative_path):
        """
        Akses: (admin/karyawan) Preview file lembur berdasarkan relative path (misal: lampiran/lembur/2025-06/nama_file.pdf)
        """
        # Mencegah path traversal
        if '..' in relative_path or relative_path.startswith('/'):
            abort(400, description='Path tidak valid')

        # Dapatkan path absolut
        full_path = os.path.join(current_app.root_path, '..', relative_path)
        folder, filename = os.path.split(full_path)

        if not os.path.exists(full_path):
            abort(404, description='File tidak ditemukan')

        return send_from_directory(folder, filename)
    

@lembur_ns.route('/by-karyawan')
class LemburByKaryawan(Resource):
    @role_required('karyawan')
    @lembur_ns.doc(params={
        'tanggal': 'Filter lembur berdasarkan tanggal tertentu (format: DD-MM-YYYY), default: hari ini'
    })
    def get(self):
        """Akses: (karyawan), Menampilkan lembur berdasarkan tanggal (default: hari ini) untuk user login"""
        try:
            tanggal_str = request.args.get('tanggal')
            if tanggal_str:
                tanggal = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
            else:
                tanggal = date.today()

            id_karyawan = get_jwt_identity()

            hasil = get_daftar_lembur_oleh_karyawan(id_karyawan, tanggal)

            if hasil is None:
                return {'status': 'Gagal mengambil data lembur'}, 500

            return {'data': hasil}, 200
        except Exception as e:
            return {'status': 'Error', 'message': str(e)}, 400


@lembur_ns.route('/<int:id_lembur>/setujui')
class SetujuiLemburResource(Resource):
    @role_required('admin')
    @lembur_ns.doc(security='Bearer Auth', description='Menyetujui lembur')
    def put(self, id_lembur):
        """Akses: Admin - Setujui lembur (tanpa insert absensi)"""
        success = setujui_lembur(id_lembur)
        if success is None:
            return {'status': 'Gagal menyetujui lembur'}, 500
        if success == 0:
            return {'status': 'ID lembur tidak ditemukan atau sudah tidak aktif'}, 404

        return {'status': 'Lembur berhasil disetujui'}, 200


@lembur_ns.route('/<int:id_lembur>/tolak')
class TolakLemburResource(Resource):
    @role_required('admin')
    @lembur_ns.doc(security='Bearer Auth', description='Menolak lembur')
    def put(self, id_lembur):
        """Akses: Admin - Tolak lembur (tanpa insert absensi)"""
        success = tolak_lembur(id_lembur)
        if success is None:
            return {'status': 'Gagal menolak lembur'}, 500
        if success == 0:
            return {'status': 'ID lembur tidak ditemukan atau sudah tidak aktif'}, 404

        return {'status': 'Lembur berhasil ditolak'}, 200


@lembur_ns.route('/<int:id_lembur>')
class HapusLembur(Resource):
    @jwt_required()
    def delete(self, id_lembur):
        """Akses: (admin/karyawan), Hapus (soft-delete) lembur"""
        success = hapus_lembur(id_lembur)
        if success:
            return {"status": "Berhasil menghapus lembur"}, 200
        return {"status": "Gagal menghapus lembur"}, 500
