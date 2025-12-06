import os
import requests
from datetime import datetime, date

from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from flask_jwt_extended import get_jwt, jwt_required, get_jwt_identity

from dotenv import load_dotenv
from werkzeug.datastructures import FileStorage

from .utils.decorator import role_required
from .query.q_perizinan import *

load_dotenv()

# =======================
# ENV CONFIG
# =======================
CDN_UPLOAD_URL = os.getenv("CDN_UPLOAD_URL")
API_KEY_ABSENSI = os.getenv("API_KEY_ABSENSI")

ALLOWED_IMAGE = {"jpg", "jpeg", "png"}

perizinan_ns = Namespace("perizinan-new", description="Manajemen Perizinan (Versi Baru)")

# =======================
# REQUEST PARSER
# =======================
perizinan_parser = perizinan_ns.parser()
perizinan_parser.add_argument("id_jenis", type=int, required=True, location="form")
perizinan_parser.add_argument("keterangan", type=str, required=False, location="form")
perizinan_parser.add_argument("tgl_mulai", type=str, required=True, location="form")     # DD-MM-YYYY
perizinan_parser.add_argument("tgl_selesai", type=str, required=True, location="form")   # DD-MM-YYYY
perizinan_parser.add_argument("potong_cuti", type=int, required=False, location="form")
perizinan_parser.add_argument("file", type=FileStorage, location="files", required=True)

# =======================
# GET PERIZINAN PARSER
# =======================
get_perizinan_parser = perizinan_ns.parser()
get_perizinan_parser.add_argument("status_izin", type=str, required=False, location="args")
get_perizinan_parser.add_argument("id_karyawan", type=str, required=False, location="args")
get_perizinan_parser.add_argument("tanggal", type=str, required=False, location="args")       # YYYY-MM-DD
get_perizinan_parser.add_argument("start_date", type=str, required=False, location="args")
get_perizinan_parser.add_argument("end_date", type=str, required=False, location="args")

reject_parser = perizinan_ns.parser()
reject_parser.add_argument("alasan", type=str, required=True, location="form", help="Alasan penolakan wajib diisi")


@perizinan_ns.route("/ajukan")
class AjukanPerizinan(Resource):
    @jwt_required()
    @role_required("karyawan")
    @perizinan_ns.expect(perizinan_parser)
    def post(self):
        """
        Akses: (karyawan), Pengajuan perizinan baru menggunakan CDN private untuk lampiran.
        4. Sakit, 3. Izin, 6. Izin Setengah Hari
        """
        args = perizinan_parser.parse_args()
        file = args.get("file")

        try:
            id_karyawan = get_jwt_identity()

            # ==========================================
            # VALIDASI DAN PARSE TANGGAL
            # ==========================================
            try:
                tgl_mulai = datetime.strptime(args["tgl_mulai"], "%d-%m-%Y").date()
                tgl_selesai = datetime.strptime(args["tgl_selesai"], "%d-%m-%Y").date()
            except ValueError:
                return {"status": False, "message": "Format tanggal harus DD-MM-YYYY"}, 400

            # ==========================================
            # UPLOAD LAMPIRAN (JIKA ADA)
            # ==========================================
            lampiran_url = None

            if file:
                filename = file.filename.lower()

                if "." not in filename:
                    return {"status": False, "message": "Nama file tidak valid"}, 400

                ext = filename.rsplit(".", 1)[1]
                if ext not in ALLOWED_IMAGE:
                    return {"status": False, "message": "Lampiran harus berupa image jpg/jpeg/png"}, 400

                # Upload ke CDN Private
                cdn_url = f"{CDN_UPLOAD_URL}/izin"
                files = {"file": (filename, file.stream, file.mimetype)}
                headers = {"X-API-KEY": API_KEY_ABSENSI}
                print("DEBUG CDN KEY:", API_KEY_ABSENSI)


                cdn_res = requests.post(cdn_url, files=files, headers=headers)

                if cdn_res.status_code != 200:
                    return {
                        "status": False,
                        "message": "Gagal upload lampiran ke CDN",
                        "cdn_response": cdn_res.text,
                    }, 500

                lampiran_url = cdn_res.json().get("url")

            # ==========================================
            # SUSUN DATA INSERT
            # ==========================================
            data = {
                "id_karyawan": id_karyawan,
                "id_jenis": args["id_jenis"],
                "keterangan": args.get("keterangan"),
                "tgl_mulai": tgl_mulai,
                "tgl_selesai": tgl_selesai,
                "potong_cuti": args.get("potong_cuti", 0),
                "path_lampiran": lampiran_url,
            }

            result = insert_pengajuan_perizinan(data)

            if result is None:
                return {"status": False, "message": "Gagal menyimpan data perizinan"}, 500

            return {
                "status": True,
                "message": "Pengajuan perizinan berhasil diajukan",
                "lampiran": lampiran_url,
            }, 201

        except Exception as e:
            return {"status": False, "message": str(e)}, 500


@perizinan_ns.route("/")
class DaftarPerizinan(Resource):
    @jwt_required()
    @perizinan_ns.doc(params={
        "status_izin": "pending / approved / rejected",
        "id_karyawan": "ID karyawan",
        "tanggal": "Tanggal tunggal (YYYY-MM-DD)",
        "start_date": "Tanggal mulai rentang (YYYY-MM-DD)",
        "end_date": "Tanggal akhir rentang (YYYY-MM-DD)"
    })
    def get(self):
        """
        Get daftar perizinan (akses: admin & karyawan).
        """
        status_izin = request.args.get("status_izin")
        id_karyawan = request.args.get("id_karyawan")
        tanggal_str = request.args.get("tanggal")
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")

        try:
            tanggal = start_date = end_date = None

            # === VALIDASI EXCLUSIVE FILTER ===
            if tanggal_str and (start_date_str or end_date_str):
                return {
                    "status": False,
                    "message": "Gunakan hanya salah satu: `tanggal` atau `start_date & end_date`"
                }, 400

            # === Tanggal tunggal ===
            if tanggal_str:
                tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()

            # === Rentang tanggal ===
            elif start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            # === Default bulan berjalan ===
            else:
                today = date.today()
                start_date = today.replace(day=1)
                # dapatkan hari pertama bulan berikutnya, lalu mundur 1 hari
                next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
                end_date = next_month - timedelta(days=1)

            hasil = get_daftar_perizinan(
                status_izin=status_izin,
                id_karyawan=id_karyawan,
                tanggal=tanggal,
                start_date=start_date,
                end_date=end_date
            )

            if hasil is None:
                return {"status": False, "message": "Gagal mengambil data perizinan"}, 500

            return {"status": True, "total": len(hasil), "message": "Data izin success", "data": hasil}, 200

        except ValueError:
            return {"status": False, "message": "Format tanggal harus YYYY-MM-DD"}, 400

        except Exception as e:
            return {"status": False, "message": str(e)}, 500
        

@perizinan_ns.route("/by-karyawan")
class PerizinanByKaryawan(Resource):
    @jwt_required()
    @role_required("karyawan")
    @perizinan_ns.doc(params={
        "tanggal": "Filter tanggal (opsional, format YYYY-MM-DD), default: today()"
    })
    def get(self):
        """
        Mendapatkan daftar izin milik karyawan (berdasarkan JWT Identity).
        Default: per hari (today).
        """
        id_karyawan = get_jwt_identity()
        tanggal_str = request.args.get("tanggal")

        try:
            # Jika tidak ada tanggal → default today
            if tanggal_str:
                tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
            else:
                tanggal = date.today()

            hasil = get_izin_by_karyawan(id_karyawan, tanggal)

            if hasil is None:
                return {"status": False, "message": "Gagal mengambil data izin"}, 500

            return {
                "status": True,
                "tanggal_filter": tanggal.isoformat(),
                "data": hasil
            }, 200

        except ValueError:
            return {"status": False, "message": "Format tanggal harus YYYY-MM-DD"}, 400

        except Exception as e:
            return {"status": False, "message": str(e)}, 500
        
        
@perizinan_ns.route("/approve/<int:id_izin>")
class ApproveIzin(Resource):
    @jwt_required()
    @role_required("admin")
    def put(self, id_izin):
        """
        Menyetujui permohonan izin karyawan.
        - Hanya admin yang bisa approve
        - Mengubah status_izin -> approved
        """
        try:
            result = approve_izin(id_izin)

            if result is None:
                return {"status": False, "message": "Terjadi kesalahan pada database"}, 500

            if result == 0:
                return {"status": False, "message": "Izin tidak ditemukan"}, 404

            return {
                "status": True,
                "message": "Permohonan izin berhasil disetujui",
                "id_izin": id_izin
            }, 200

        except Exception as e:
            return {"status": False, "message": str(e)}, 500


@perizinan_ns.route("/reject/<int:id_izin>")
class RejectIzin(Resource):

    @jwt_required()
    @role_required("admin")
    @perizinan_ns.expect(reject_parser)
    def put(self, id_izin):
        """
        Menolak permohonan izin.
        Admin wajib memberikan alasan penolakan.
        """
        args = reject_parser.parse_args()
        alasan = args.get("alasan")

        if not alasan or alasan.strip() == "":
            return {"status": False, "message": "Alasan penolakan wajib diisi"}, 400

        try:
            result = reject_izin(id_izin, alasan)

            if result is None:
                return {"status": False, "message": "Kesalahan pada database"}, 500

            if result == 0:
                return {"status": False, "message": "Izin tidak ditemukan"}, 404

            return {
                "status": True,
                "message": "Permohonan izin telah ditolak",
                "id_izin": id_izin,
                "alasan_penolakan": alasan
            }, 200

        except Exception as e:
            return {"status": False, "message": str(e)}, 500


@perizinan_ns.route("/delete/<int:id_izin>")
class DeleteIzin(Resource):
    @jwt_required()
    def delete(self, id_izin):
        """
        Soft delete permohonan izin.
        Admin dapat menghapus semua izin.
        Karyawan hanya dapat menghapus izin miliknya.
        """
        try:
            jwt_data = get_jwt()
            user_role = jwt_data.get("role")
            user_id = get_jwt_identity()

            # ================================
            # 1. Jika admin → langsung boleh
            # ================================
            if user_role == "admin":
                result = soft_delete_izin(id_izin)

                if result is None:
                    return {"status": False, "message": "Kesalahan database"}, 500
                if result == 0:
                    return {"status": False, "message": "Izin tidak ditemukan"}, 404

                return {
                    "status": True,
                    "message": "Data izin berhasil dihapus (soft delete)",
                    "id_izin": id_izin
                }, 200

            # ==========================================
            # 2. Jika karyawan → harus cek owner izin
            # ==========================================
            izin_owner = check_izin_owner(id_izin)

            if izin_owner is None:
                return {"status": False, "message": "Izin tidak ditemukan"}, 404

            if int(izin_owner) != int(user_id):
                return {
                    "status": False,
                    "message": "Anda tidak memiliki akses untuk menghapus izin ini"
                }, 403

            # Jika pemilik → boleh hapus
            result = soft_delete_izin(id_izin)

            if result is None:
                return {"status": False, "message": "Kesalahan database"}, 500

            return {
                "status": True,
                "message": "Data izin berhasil dihapus (soft delete)",
                "id_izin": id_izin
            }, 200

        except Exception as e:
            return {"status": False, "message": str(e)}, 500
