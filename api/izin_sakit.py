import os
from flask import current_app, request
from flask_restx import Namespace, Resource, fields # type: ignore
from werkzeug.utils import secure_filename

from .utils.decorator import role_required
from .query.q_izin_sakit import *

izin_ns = Namespace('perizinan', description='Manajemen Pengajuan Izin/Sakit')

izin_model = izin_ns.model('PengajuanIzin', {
    'id_karyawan': fields.Integer(required=True),
    'id_jenis': fields.Integer(required=True, description='3 = Izin, 4 = Sakit'),
    'keterangan': fields.String(required=True),
    'tgl_mulai': fields.String(required=True, description='Format: YYYY-MM-DD'),
    'tgl_selesai': fields.String(required=True, description='Format: YYYY-MM-DD'),
    'path_lampiran': fields.String(required=False, description='Path file jika ada'),
})

izin_parser = izin_ns.parser()
izin_parser.add_argument('id_karyawan', type=int, required=True, location='form')
izin_parser.add_argument('id_jenis', type=int, required=True, location='form')
izin_parser.add_argument('keterangan', type=str, required=False, location='form')
izin_parser.add_argument('tgl_mulai', type=str, required=True, location='form')
izin_parser.add_argument('tgl_selesai', type=str, required=True, location='form')
izin_parser.add_argument('file', type='FileStorage', location='files', required=False)

# Parser untuk menerima file
upload_parser = izin_ns.parser()
upload_parser.add_argument('file', location='files', type='file', required=True)

# Daftar ekstensi file yang diizinkan
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@izin_ns.route('/')
class PengajuanIzinResource(Resource):
    @izin_ns.expect(izin_parser)
    @role_required('karyawan')
    def post(self):
        """Akses: (karyawan), Ajukan izin atau sakit (lampiran wajib untuk sakit)"""
        args = izin_parser.parse_args()
        file = args.get('file')

        # Validasi lampiran jika jenis = 4 (sakit)
        if args['id_jenis'] == 4 and file is None:
            return {'status': 'Lampiran wajib untuk permohonan sakit'}, 400

        path_lampiran = None
        if file and allowed_file(file.filename):
            today_str = datetime.now().strftime('%Y-%m')
            upload_dir = os.path.join(current_app.root_path, '..', 'uploads', 'izin', today_str)
            os.makedirs(upload_dir, exist_ok=True)

            filename = secure_filename(file.filename)
            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)

            path_lampiran = os.path.join('uploads', 'izin', today_str, filename)
        elif file:
            return {'status': 'Ekstensi file tidak diizinkan'}, 400

        # Susun data yang dikirim ke fungsi query
        data = {
            'id_karyawan': args['id_karyawan'],
            'id_jenis': args['id_jenis'],
            'keterangan': args['keterangan'],
            'tgl_mulai': args['tgl_mulai'],
            'tgl_selesai': args['tgl_selesai'],
            'path_lampiran': path_lampiran
        }

        result = insert_pengajuan_izin(data)
        if result is None:
            return {'status': 'Gagal mengajukan izin'}, 500

        return {'status': 'Pengajuan izin berhasil direkam'}, 201
    

    @role_required('admin')
    @izin_ns.doc(params={
        'status_izin': 'Filter berdasarkan status izin (pending, disetujui, ditolak)',
        'id_karyawan': 'Filter berdasarkan ID karyawan'
    })
    def get(self):
        """Akses: (admin), Menampilkan semua data izin, bisa difilter per status atau per karyawan"""
        status_izin = request.args.get('status_izin')
        id_karyawan = request.args.get('id_karyawan')

        hasil = get_daftar_izin(status_izin, id_karyawan)

        if hasil is None:
            return {'status': 'Gagal mengambil data izin'}, 500

        return {'data': hasil}, 200
    

@izin_ns.route('/upload')
class UploadLampiran(Resource):
    @role_required('karyawan')  # hanya karyawan yang boleh upload
    @izin_ns.expect(upload_parser)
    @izin_ns.doc(security='Bearer Auth', description="Upload lampiran izin (PDF/JPG/PNG)")
    def post(self):
        """Akses: (karyawan), API untuk uplod document ke sistem"""
        file = request.files.get('file')
        if not file or file.filename == '':
            return {'status': 'File tidak ditemukan'}, 400

        if not allowed_file(file.filename):
            return {'status': 'Ekstensi file tidak diizinkan'}, 400

        # Tentukan direktori penyimpanan
        today_str = datetime.now().strftime('%Y-%m')
        upload_dir = os.path.join(current_app.root_path, '..', 'uploads', 'izin', today_str)
        os.makedirs(upload_dir, exist_ok=True)

        # Simpan file secara aman
        filename = secure_filename(file.filename)
        save_path = os.path.join(upload_dir, filename)
        file.save(save_path)

        relative_path = os.path.join('uploads', 'izin', today_str, filename)

        return {
            'status': 'Upload berhasil',
            'path_lampiran': relative_path
        }, 200
    

@izin_ns.route('/<int:id>/setujui')
class SetujuiIzinResource(Resource):
    @role_required('admin')
    def put(self, id):
        """Akses: (admin), Menyetujui izin dan memasukkan ke absensi"""
        success = setujui_izin_dan_insert_absensi(id)
        if success is None:
            return {'status': 'Gagal menyetujui izin'}, 500
        if success == 0:
            return {'status': 'ID izin tidak ditemukan'}, 404

        return {'status': 'Izin berhasil disetujui dan dicatat ke absensi'}, 200


@izin_ns.route('/<int:id>/tolak')
class TolakIzinResource(Resource):
    @role_required('admin')
    @izin_ns.expect(izin_ns.model('AlasanTolakModel', {
        'alasan': fields.String(required=True, description='Alasan penolakan')
    }))
    def put(self, id):
        """Akses: (admin), Menolak izin dan mencatat alasan"""
        data = request.json
        alasan = data.get("alasan")

        if not alasan:
            return {"status": "Alasan penolakan wajib diisi"}, 400

        result = tolak_izin(id, alasan)
        if result is None:
            return {"status": "Gagal menolak izin"}, 500
        if result == 0:
            return {"status": "ID izin tidak ditemukan"}, 404

        return {"status": "Izin berhasil ditolak"}, 200
