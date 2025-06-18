from datetime import datetime
import re
import logging
from flask import request
from flask_restx import Namespace, Resource, fields
from werkzeug.datastructures import FileStorage
from sqlalchemy.exc import SQLAlchemyError

from .utils.config import get_timezone
from .utils.decorator import role_required
from .utils.face_detection import verifikasi_wajah
from .utils.filter_radius import get_valid_office_name
from .utils.helpers import hitung_waktu_kerja, hitung_keterlambatan, hitung_jam_kurang

from .query.q_absensi import *


absensi_ns = Namespace('absensi', description='API untuk absensi')

upload_parser = absensi_ns.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='Foto wajah saat check-out')
upload_parser.add_argument('latitude', type=str, required=True, help='Latitude lokasi saat check-out')
upload_parser.add_argument('longitude', type=str, required=True, help='Longitude lokasi saat check-out')

edit_absensi_model = absensi_ns.model('EditAbsensi', {
    'jam_masuk': fields.String(required=True, description='Jam masuk (HH:MM)'),
    'jam_keluar': fields.String(required=False, description='Jam keluar (HH:MM), boleh kosong/null'),
    'lokasi_masuk': fields.String(required=False, description='Nama lokasi masuk (dipilih dari dropdown)'),
    'lokasi_keluar': fields.String(required=False, description='Nama lokasi keluar (dipilih dari dropdown)')
})

add_absensi_model = absensi_ns.model('AddAbsensi', {
    'tanggal': fields.String(required=True, description='Tanggal (YYYY-MM-DD)'),
    'jam_masuk': fields.String(required=True, description='Jam masuk (HH:MM)'),
    'jam_keluar': fields.String(required=False, description='Jam keluar (HH:MM), boleh kosong/null'),
    'lokasi_masuk': fields.String(required=True, description='Nama lokasi masuk (dipilih dari dropdown)'),
    'lokasi_keluar': fields.String(required=False, description='Nama lokasi keluar (dipilih dari dropdown)'),
})


@absensi_ns.route('/add/<int:id_karyawan>')
class AddAbsensiResource(Resource):
    @role_required('admin')
    @absensi_ns.expect(add_absensi_model)
    def post(self, id_karyawan):
        """Akses: (admin), add Absensi karyawan manual oleh admin"""
        data = request.json
        tanggal = data.get("tanggal")
        jam_masuk = data.get("jam_masuk")
        jam_keluar = data.get("jam_keluar")
        lokasi_masuk = data.get("lokasi_masuk")
        lokasi_keluar = data.get("lokasi_keluar")
        
        # Validasi format waktu
        def is_valid_time_format(t):
            return bool(re.match(r"^\d{2}:\d{2}$", t))
        
        if not jam_masuk:
            return {'status': 'Jam masuk wajib diisi'}, 400
        if not is_valid_time_format(jam_masuk):
            return {'status': 'Format jam masuk tidak valid. Gunakan format HH:MM'}, 400
        if jam_keluar and not is_valid_time_format(jam_keluar):
            return {'status': 'Format jam keluar tidak valid. Gunakan format HH:MM'}, 400

        # Hitung nilai turunan
        if not jam_keluar:
            jam_keluar = None
            jam_kurang = None
            total_jam_kerja = None
        else:
            total_jam_kerja = hitung_waktu_kerja(
                datetime.strptime(jam_masuk, "%H:%M").time(),
                datetime.strptime(jam_keluar, "%H:%M").time()
            )
            jam_kurang = hitung_jam_kurang(datetime.strptime(jam_keluar, "%H:%M").time())

        jam_terlambat = hitung_keterlambatan(datetime.strptime(jam_masuk, "%H:%M").time())

        result = add_absensi(
            id_karyawan=id_karyawan,
            tanggal=tanggal,
            jam_masuk=jam_masuk,
            jam_keluar=jam_keluar,
            lokasi_masuk=lokasi_masuk,
            lokasi_keluar=lokasi_keluar,
            jam_terlambat=jam_terlambat,
            jam_kurang=jam_kurang,
            total_jam_kerja=total_jam_kerja
        )

        if result is None:
            return {'status': 'Terjadi kesalahan saat menambahkan absensi'}, 500
        if result == 0:
            return {'status': 'Data tidak ditemukan atau tidak berhasil ditambahkan'}, 404

        return {'status': 'Data absensi berhasil ditambahkan'}, 200


@absensi_ns.route('/check-in/<int:id_karyawan>')
class AbsensiCheckInResource(Resource):
    @role_required('karyawan')
    @absensi_ns.expect(upload_parser)
    @absensi_ns.response(200, 'Check-in berhasil')
    @absensi_ns.response(400, 'Data tidak lengkap atau tidak valid')
    @absensi_ns.response(403, 'Diluar lokasi kerja atau wajah tidak cocok')
    def post(self, id_karyawan):
        """Akses: (karyawan), Check-in karyawan berdasarkan lokasi dan foto"""
        try:
            args = upload_parser.parse_args()
            image = args['file']
            user_lat = args['latitude']
            user_lon = args['longitude']
            
            if image.filename == '':
                return {'error': 'Anda belum memasukkan gambar!'}, 400

            try:
                user_lat = float(user_lat)
                user_lon = float(user_lon)
            except ValueError:
                return {'error': 'Format koordinat salah!'}, 400

            id_jenis = get_jenis_karyawan(id_karyawan)
            if id_jenis is None:
                return {'status': 'error', 'message': 'Karyawan tidak ditemukan'}, 404

            lokasi_absensi = get_valid_office_name(user_lat, user_lon, id_jenis)

            if lokasi_absensi is None:
                if is_wfh_allowed(id_karyawan):
                    lokasi_absensi = "WFH"
                else:
                    return {'status': 'error', 'message': 'Anda berada diluar lokasi kerja'}, 403

            # Verifikasi wajah
            face = verifikasi_wajah(id_karyawan, image)
            if face == "not_detected":
                return {'status': 'error', 'message': 'Wajah tidak terdeteksi!'}, 400
            elif face == "error":
                return {'status': 'error', 'message': 'Gagal memverifikasi wajah.'}, 500
            elif not face:
                return {'status': 'error', 'message': 'Wajah tidak cocok!'}, 403

            tanggal, jam_masuk = get_timezone()
            jam_terlambat = hitung_keterlambatan(jam_masuk)

            add_checkin(id_karyawan, tanggal, jam_masuk, lokasi_absensi, jam_terlambat)

            return {'status': 'Check-in berhasil', 'lokasi': lokasi_absensi}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500

@absensi_ns.route('/check-out/<int:id_karyawan>')
class AbsensiCheckOutResource(Resource):
    @absensi_ns.expect(upload_parser)
    @role_required('karyawan')
    def put(self, id_karyawan):
        """Akses: (karyawan), Check-out karyawan berdasarkan lokasi dan foto"""
        try:
            args = upload_parser.parse_args()
            image = args['file']
            user_lat = args['latitude']
            user_lon = args['longitude']

            if image.filename == '':
                return {'status': 'error', 'message': 'Anda belum memasukkan gambar!'}, 400

            try:
                user_lat = float(user_lat)
                user_lon = float(user_lon)
            except ValueError:
                return {'status': 'error', 'message': f'Format lokasi salah. Latitude: {user_lat}, Longitude: {user_lon}'}, 400

            id_jenis = get_jenis_karyawan(id_karyawan)
            if id_jenis is None:
                return {'status': 'error', 'message': 'Karyawan tidak ditemukan'}, 404

            lokasi_absensi = get_valid_office_name(user_lat, user_lon, id_jenis)

            if lokasi_absensi is None:
                if is_wfh_allowed(id_karyawan):
                    lokasi_absensi = "WFH"
                else:
                    return {'status': 'error', 'message': 'Anda berada di luar lokasi kerja yang diizinkan!'}, 403

            face = verifikasi_wajah(id_karyawan, image)
            if face == "not_detected":
                return {'status': 'error', 'message': 'Wajah tidak terdeteksi. Pastikan wajah terlihat jelas!'}, 400
            elif face == "error":
                return {'status': 'error', 'message': 'Terjadi kesalahan saat memverifikasi wajah.'}, 500
            elif not face:
                return {'status': 'error', 'message': 'Wajah tidak sesuai dengan akun!'}, 403

            tanggal, jam_keluar = get_timezone()
            presensi = get_check_presensi(id_karyawan)
            if not presensi:
                return {'status': 'info', 'message': 'Belum ada presensi hari ini'}, 200

            jam_masuk = presensi.get("jam_masuk")
            if not jam_masuk:
                return {'status': 'info', 'message': 'Anda belum melakukan check-in'}, 200

            jam_kurang = hitung_jam_kurang(jam_keluar)
            total_jam_kerja = hitung_waktu_kerja(jam_masuk, jam_keluar)

            result = update_checkout(id_karyawan, tanggal, jam_keluar, lokasi_absensi, jam_kurang, total_jam_kerja)
            if result is None or result == 0:
                return {'status': 'error', 'message': 'Gagal mencatat check-out atau tidak ditemukan check-in sebelumnya'}, 500

            return {'status': 'Check-out berhasil', 'lokasi': lokasi_absensi}, 200
        except SQLAlchemyError as e:
                logging.error(f"Database error: {str(e)}")
                return {'status': "Internal server error"}, 500


@absensi_ns.route('/delete-check-out/<int:id_absensi>')
class HapusJamKeluar(Resource):
    @role_required('karyawan')
    def delete(self, id_absensi):
        """Akses: (karyawan), Delete check out berdasarkan ID"""
        try:
            deleted = delete_checkout(id_absensi)
            if not deleted:
                return {'status': 'error', "message": "Tidak ditemukan atau belum absen pulang"}, 404
            return {"status": "Absen keluar anda berhasil dihapus"}, 200
        except SQLAlchemyError as e:
            logging.error(f"Database error: {str(e)}")
            return {'status': "Internal server error"}, 500


@absensi_ns.route('/history/<int:id_karyawan>')
class AbsensiHarianPersonalResource(Resource):
    @role_required('karyawan')
    @absensi_ns.doc(params={'tanggal': 'Format tanggal DD-MM-YYYY'})
    def get(self, id_karyawan):
        """Akses: (karyawan), Lihat riwayat absensi harian karyawan berdasarkan tanggal tertentu"""
        tanggal_param = request.args.get('tanggal')

        try:
            if tanggal_param:
                tanggal_filter = datetime.strptime(tanggal_param, "%d-%m-%Y").date()
            else:
                tanggal_filter, _ = get_timezone()
        except ValueError:
            return {'status': 'Format tanggal tidak valid. Gunakan DD-MM-YYYY'}, 400

        result = get_history_absensi_harian(id_karyawan, tanggal_filter)
        return {'history': result}, 200

@absensi_ns.route('/check/<int:id_karyawan>')
class CekPresensiResource(Resource):
    @role_required('karyawan')
    def get(self, id_karyawan):
        """Akses: (karyawan), Check presensi karyawan berdasarkan id"""
        cek_presensi = get_check_presensi(id_karyawan)

        if not cek_presensi:
            return {"message": "Belum ada presensi"}, 200

        result = {
            "id_absensi": cek_presensi["id_absensi"],
            "tanggal": cek_presensi["tanggal"].strftime('%d-%m-%Y'),
            "jam_masuk": cek_presensi["jam_masuk"].strftime('%H:%M') if cek_presensi["jam_masuk"] else None,
            "jam_keluar": cek_presensi["jam_keluar"].strftime('%H:%M') if cek_presensi["jam_keluar"] else None,
            "lokasi_masuk": cek_presensi["lokasi_masuk"],
            "lokasi_keluar": cek_presensi["lokasi_keluar"],
            "jam_terlambat": cek_presensi["jam_terlambat"]
        }

        return result, 200
    

@absensi_ns.route('/hadir')
class AbsensiHarianAdmin(Resource):
    @role_required('admin')
    @absensi_ns.doc(params={'tanggal': 'Format tanggal DD-MM-YYYY'})
    def get(self):
        """Akses: (admin), Check karyawan dengan status hadir berdasarkan tanggal"""
        tanggal_param = request.args.get('tanggal')
        try:
            if tanggal_param:
                tanggal_filter = datetime.strptime(tanggal_param, "%d-%m-%Y").date()
            else:
                tanggal_filter, _ = get_timezone()  # default: hari ini
        except ValueError:
            return {'status': 'Format tanggal tidak valid. Gunakan DD-MM-YYYY'}, 400

        data = query_absensi_harian_admin(tanggal_filter)
        return {'absensi': data}, 200


@absensi_ns.route('/tidak-hadir')
class AbsensiTidakHadir(Resource):
    @role_required('admin')
    @absensi_ns.doc(params={'tanggal': 'Format tanggal DD-MM-YYYY'})
    def get(self):
        """Akses: (admin), Check karyawan dengan status tidak hadir berdasarkan tanggal"""
        tanggal_param = request.args.get('tanggal')

        try:
            if tanggal_param:
                tanggal_filter = datetime.strptime(tanggal_param, "%d-%m-%Y").date()
            else:
                tanggal_filter, _ = get_timezone()
        except ValueError:
            return {'status': 'Format tanggal tidak valid. Gunakan DD-MM-YYYY'}, 400

        data = query_absensi_tidak_hadir(tanggal_filter)
        return {'absensi': data}, 200


@absensi_ns.route('/izin-sakit')
class AbsensiIzinSakit(Resource):
    @role_required('admin')
    @absensi_ns.doc(params={'tanggal': 'Format tanggal DD-MM-YYYY'})
    def get(self):
        """Akses: (admin), Check karyawan dengan status izin/sakit berdasarkan tanggal"""
        tanggal_param = request.args.get('tanggal')

        try:
            if tanggal_param:
                tanggal_filter = datetime.strptime(tanggal_param, "%d-%m-%Y").date()
            else:
                tanggal_filter, _ = get_timezone()
        except ValueError:
            return {'status': 'Format tanggal tidak valid. Gunakan DD-MM-YYYY'}, 400

        data = query_absensi_izin_sakit(tanggal_filter)
        return {'absensi': data}, 200


@absensi_ns.route('/edit/<int:id_absensi>')
class EditAbsensi(Resource):
    @absensi_ns.expect(edit_absensi_model)
    @role_required('admin')
    def put(self, id_absensi):
        """Akses: (admin), Edit data presensi karyawan"""
        data = request.json
        jam_masuk = data.get("jam_masuk")
        jam_keluar = data.get("jam_keluar")
        lokasi_masuk = data.get("lokasi_masuk")
        lokasi_keluar = data.get("lokasi_keluar")

        # Validasi format waktu
        def is_valid_time_format(t):
            return bool(re.match(r"^\d{2}:\d{2}$", t))

        if not jam_masuk:
            return {'status': 'Jam masuk wajib diisi'}, 400
        if not is_valid_time_format(jam_masuk):
            return {'status': 'Format jam masuk tidak valid. Gunakan format HH:MM'}, 400
        if jam_keluar and not is_valid_time_format(jam_keluar):
            return {'status': 'Format jam keluar tidak valid. Gunakan format HH:MM'}, 400

        # Hitung nilai turunan
        if not jam_keluar:
            jam_keluar = None
            jam_kurang = None
            total_jam_kerja = None
        else:
            total_jam_kerja = hitung_waktu_kerja(
                datetime.strptime(jam_masuk, "%H:%M").time(),
                datetime.strptime(jam_keluar, "%H:%M").time()
            )
            jam_kurang = hitung_jam_kurang(datetime.strptime(jam_keluar, "%H:%M").time())

        jam_terlambat = hitung_keterlambatan(datetime.strptime(jam_masuk, "%H:%M").time())

        result = update_absensi_by_id(
            id_absensi=id_absensi,
            jam_masuk=jam_masuk,
            jam_keluar=jam_keluar,
            jam_terlambat=jam_terlambat,
            jam_kurang=jam_kurang,
            total_jam_kerja=total_jam_kerja,
            lokasi_masuk=lokasi_masuk,
            lokasi_keluar=lokasi_keluar
        )

        if result is None:
            return {'status': 'Terjadi kesalahan saat memperbarui data'}, 500
        if result == 0:
            return {'status': 'Data tidak ditemukan atau tidak berhasil diperbarui'}, 404

        return {'status': 'Data absensi berhasil diperbarui'}, 200


@absensi_ns.route('/delete/<int:id_absensi>')
class HapusAbsensi(Resource):
    @absensi_ns.response(200, 'Berhasil menghapus absensi')
    @absensi_ns.response(404, 'Absensi tidak ditemukan')
    @absensi_ns.response(500, 'Terjadi kesalahan saat menghapus data')
    @role_required('admin')
    def delete(self, id_absensi):
        """Akses: (admin), Delete data presensi karyawan"""
        try:
            result = remove_absensi(id_absensi)
            if result is None:
                return {'status': "Terjadi kesalahan saat menghapus absensi"}, 500
            if result == 0:
                return {'status': "Absensi tidak ditemukan"}, 404
            return {'status': "Berhasil menghapus absensi"}, 200
        except Exception as e:
            return {'status': f"Terjadi kesalahan: {str(e)}"}, 500
