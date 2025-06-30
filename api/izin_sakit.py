from datetime import time
import os
from flask import current_app, request, send_from_directory, abort
from flask_restx import Namespace, Resource, fields, reqparse
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask_jwt_extended import get_jwt_identity, jwt_required

from .utils.helpers import hitung_jam_kurang, hitung_keterlambatan, hitung_waktu_kerja
from .utils.decorator import role_required
from .query.q_izin_sakit import *

izin_ns = Namespace('perizinan', description='Manajemen Pengajuan Izin/Sakit')

izin_model = izin_ns.model('PengajuanIzin', {
    'id_jenis': fields.Integer(required=True, description='3 = Izin, 4 = Sakit'),
    'keterangan': fields.String(required=True),
    'tgl_mulai': fields.String(required=True, description='Format: YYYY-MM-DD'),
    'tgl_selesai': fields.String(required=True, description='Format: YYYY-MM-DD'),
    'path_lampiran': fields.String(required=False, description='Path file jika ada'),
})

izin_parser = izin_ns.parser()
izin_parser.add_argument('id_jenis', type=int, required=True, location='form', help='3 = Izin, 4 = Sakit')
izin_parser.add_argument('keterangan', type=str, required=False, location='form', help='Masukkan keterangan')
izin_parser.add_argument('tgl_mulai', type=str, required=True, location='form', help='Format: DD-MM-YYYY')
izin_parser.add_argument('tgl_selesai', type=str, required=True, location='form', help='Format: DD-MM-YYYY')
izin_parser.add_argument('file', type=FileStorage, location='files', required=False, help='Path file jika ada')

setengah_hari_parser = reqparse.RequestParser()
setengah_hari_parser.add_argument('jam_selesai', type=str, required=True, help='Format jam selesai: HH:MM')

# Parser untuk menerima file
upload_parser = izin_ns.parser()
upload_parser.add_argument('file', location='files', type='file', required=True)

# Daftar ekstensi file yang diizinkan
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@izin_ns.route('/')
class PengajuanIzinResource(Resource):
    @jwt_required()
    @izin_ns.doc(params={
        'status_izin': 'Filter berdasarkan status izin (pending, approved, rejected)',
        'id_karyawan': 'Filter berdasarkan ID karyawan'
    })
    def get(self):
        """Akses: (admin, karyawan), Menampilkan semua data izin, bisa difilter per status atau per karyawan"""
        status_izin = request.args.get('status_izin')
        id_karyawan = request.args.get('id_karyawan')

        hasil = get_daftar_izin(status_izin, id_karyawan)

        if hasil is None:
            return {'status': 'Gagal mengambil data izin'}, 500

        return {'data': hasil}, 200
    
    @izin_ns.expect(izin_parser)
    @role_required('karyawan')
    def post(self):
        """Akses: (karyawan), Ajukan izin atau sakit (lampiran wajib untuk sakit)"""
        args = izin_parser.parse_args()
        file = args['file']

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
            'id_karyawan': get_jwt_identity(),
            'id_jenis': args['id_jenis'],
            'keterangan': args['keterangan'],
            'tgl_mulai': datetime.strptime(args['tgl_mulai'], "%d-%m-%Y").date(),
            'tgl_selesai': datetime.strptime(args['tgl_selesai'], "%d-%m-%Y").date(),
            'path_lampiran': path_lampiran
        }

        result = insert_pengajuan_izin(data)
        if result is None:
            return {'status': 'Gagal mengajukan izin'}, 500

        return {'status': 'Pengajuan izin berhasil direkam'}, 201
    

@izin_ns.route('/by-karyawan')
class IzinByKaryawan(Resource):
    @role_required('karyawan')
    @izin_ns.doc(params={
        'tanggal': 'Filter izin berdasarkan tanggal tertentu (format: DD-MM-YYYY), default: hari ini'
    })
    def get(self):
        """Akses: (karyawan), Menampilkan izin berdasarkan tanggal (default: hari ini) untuk user login"""
        try:
            tanggal_str = request.args.get('tanggal')
            if tanggal_str:
                tanggal = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
            else:
                tanggal = date.today()

            id_karyawan = get_jwt_identity()

            hasil = get_daftar_izin_oleh_karyawan(id_karyawan, tanggal)

            if hasil is None:
                return {'status': 'Gagal mengambil data izin'}, 500

            return {'data': hasil}, 200
        except Exception as e:
            return {'status': 'Error', 'message': str(e)}, 400
        
        
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
    

@izin_ns.route('/preview/<path:relative_path>')
class PreviewLampiran(Resource):
    @jwt_required()
    @izin_ns.doc(security='Bearer Auth', description='Preview lampiran izin (PDF/JPG/PNG)')
    def get(self, relative_path):
        """
        Akses: (admin/karyawan) Preview file izin berdasarkan path (izin/2025-06/nama_file.pdf)
        """
        # Cegah traversal attack
        if '..' in relative_path or relative_path.startswith('/'):
            abort(400, description='Path tidak valid')

        # Pisahkan folder dan filename
        full_path = os.path.join(current_app.root_path, '..', relative_path)
        folder, filename = os.path.split(full_path)

        if not os.path.exists(full_path):
            abort(404, description='File tidak ditemukan')

        return send_from_directory(folder, filename)
    

@izin_ns.route('/setengah-hari')
class PengajuanIzinSetengahHariResource(Resource):
    @izin_ns.expect(setengah_hari_parser)
    @role_required('karyawan')
    def post(self):
        args = setengah_hari_parser.parse_args()

        id_karyawan = get_jwt_identity()
        jam_selesai = datetime.strptime(args['jam_selesai'], "%H:%M").time()
        lokasi_keluar = "Setengah hari"
        today = datetime.now().date()

        # Ambil absensi hari ini
        absensi = get_absensi_by_date(id_karyawan, today)
        if not absensi or not absensi['jam_masuk']:
            return {'message': 'Anda belum melakukan absensi masuk hari ini'}, 400

        jam_masuk = absensi['jam_masuk']

        # Hitung waktu kerja, keterlambatan, dan jam kurang
        total_jam_kerja = hitung_waktu_kerja(jam_masuk, jam_selesai)
        jam_kurang = hitung_jam_kurang(jam_selesai)

        # Update absensi
        update_absensi_izin_setengah_hari(
            id_karyawan=id_karyawan,
            tanggal=today,
            jam_keluar=jam_selesai,
            lokasi_keluar=lokasi_keluar,
            total_jam_kerja=total_jam_kerja,
            jam_kurang=jam_kurang
        )

        return {'status': 'Izin setengah hari (pulang awal) berhasil dicatat'}, 201


@izin_ns.route('/<int:id_izin>/setujui')
class SetujuiIzinResource(Resource):
    @role_required('admin')
    def put(self, id_izin):
        """Akses: (admin), Menyetujui izin dan memasukkan ke absensi"""
        success = setujui_izin_dan_insert_absensi(id_izin)
        if success is None:
            return {'status': 'Gagal menyetujui izin'}, 500
        if success == 0:
            return {'status': 'ID izin tidak ditemukan'}, 404

        return {'status': 'Izin berhasil disetujui dan dicatat ke absensi'}, 200


@izin_ns.route('/<int:id_izin>/tolak')
class TolakIzinResource(Resource):
    @role_required('admin')
    @izin_ns.expect(izin_ns.model('AlasanTolakModel', {
        'alasan': fields.String(required=True, description='Alasan penolakan')
    }))
    def put(self, id_izin):
        """Akses: (admin), Menolak izin dan mencatat alasan"""
        data = request.json
        alasan = data.get("alasan")

        if not alasan:
            return {"status": "Alasan penolakan wajib diisi"}, 400

        result = tolak_izin(id_izin, alasan)
        if result is None:
            return {"status": "Gagal menolak izin"}, 500
        if result == 0:
            return {"status": "ID izin tidak ditemukan"}, 404

        return {"status": "Izin berhasil ditolak"}, 200


@izin_ns.route('/<int:id_izin>')
class HapusIzin(Resource):
    @jwt_required()
    def delete(self, id_izin):
        """Akses: (admin, karyawan), Hapus (soft-delete)"""
        success = hapus_izin(id_izin)
        if success:
            return {"status": "Berhasil menghapus izin"}, 200
        return {"status": "Gagal menghapus izin"}, 500