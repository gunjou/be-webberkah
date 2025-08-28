from flask import request
from flask_restx import Namespace, Resource, reqparse, fields

from .query.q_hutang import *
from .utils.decorator import role_required


hutang_ns = Namespace("hutang", description="Manajemen hutang karyawan")

hutang_input = hutang_ns.model("InputHutang", {
    "id_karyawan": fields.Integer(required=True, description="ID karyawan yang berhutang"),
    "tanggal": fields.String(required=True, description="Tanggal hutang (YYYY-MM-DD)"),
    "nominal": fields.Integer(required=True, description="Jumlah nominal hutang"),
    "keterangan": fields.String(required=False, description="Keterangan tambahan"),
})

update_hutang_parser = hutang_ns.parser()
update_hutang_parser.add_argument('nominal', type=int, required=False, location='form', help='Nominal hutang')
update_hutang_parser.add_argument('keterangan', type=str, required=False, location='form', help='Keterangan hutang')
update_hutang_parser.add_argument('status_hutang', type=str, required=False, location='form', help='Status hutang (lunas / belum lunas)')

pembayaran_hutang_parser = hutang_ns.parser()
pembayaran_hutang_parser.add_argument('id_karyawan', type=int, required=True, location='form', help='ID Karyawan')
pembayaran_hutang_parser.add_argument('nominal', type=int, required=True, location='form', help='Nominal pembayaran')
pembayaran_hutang_parser.add_argument('metode', type=str, required=True, location='form', help='Metode pembayaran')
pembayaran_hutang_parser.add_argument('keterangan', type=str, required=False, location='form', help='Keterangan')
pembayaran_hutang_parser.add_argument('id_hutang', type=int, required=False, location='form', help='Opsional untuk pembayaran tunai')


@hutang_ns.route("/")
class HutangListAdmin(Resource):
    @hutang_ns.doc(params={
        'status_hutang': '(optional) Filter berdasarkan status hutang [lunas, belum lunas]',
    })
    @role_required('admin')  # hanya admin yang bisa akses
    def get(self):
        """Akses: (admin), Mendapatkan daftar semua hutang karyawan"""
        try:
            args = request.args
            status_hutang = args.get("status_hutang")
            data = get_all_hutang(status_hutang=status_hutang)
            return {"status": "success", "data": data}, 200
        except Exception as e:
                return {'status': 'Error', 'message': str(e)}, 400
        
    @hutang_ns.expect(hutang_input)
    @role_required('admin')
    def post(self):
        """Akses: (admin), Menambahkan hutang ke karyawan tertentu"""
        try:
            json_data = request.get_json()
            id_karyawan = json_data.get("id_karyawan")
            tanggal = json_data.get("tanggal")
            nominal = json_data.get("nominal")
            keterangan = json_data.get("keterangan", "")

            # Validasi input
            if not all([id_karyawan, tanggal, nominal]):
                return {"status": "fail", "message": "Semua field wajib diisi"}, 400

            inserted = insert_hutang(id_karyawan, tanggal, nominal, keterangan)
            if inserted:
                return {"status": "success", "message": "Hutang berhasil ditambahkan"}, 201
            return {"status": "fail", "message": "Gagal menambahkan hutang"}, 400

        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
        

@hutang_ns.route("/<int:id_hutang>")
@hutang_ns.param("id_hutang", "ID Hutang")
class HutangById(Resource):
    @role_required("admin")
    def get(self, id_hutang):
        """Akses: (admin), Mendapatkan detail hutang berdasarkan ID"""
        try:
            data = get_hutang_by_id(id_hutang)
            if data:
                return {"status": "success", "data": data}, 200
            else:
                return {"status": "not found", "message": "Hutang tidak ditemukan"}, 404
        except Exception as e:
            return {"status": "error", "message": str(e)}, 400
        
    @hutang_ns.expect(update_hutang_parser)
    @role_required("admin")
    def put(self, id_hutang):
        """Akses: (admin), Mengedit nominal, keterangan, atau status_hutang hutang"""
        args = update_hutang_parser.parse_args()

        # Ambil data hutang lama
        data_lama = get_hutang_by_id(id_hutang)
        if not data_lama:
            return {"status": "not found", "message": "Hutang tidak ditemukan"}, 404

        # Gunakan nilai lama jika tidak ada input baru
        nominal = args['nominal'] if args['nominal'] is not None else data_lama['nominal']
        keterangan = args['keterangan'] if args['keterangan'] is not None else data_lama['keterangan']
        status_hutang = args['status_hutang'] if args['status_hutang'] is not None else data_lama['status_hutang']

        try:
            update_hutang_by_id(id_hutang, nominal, keterangan, status_hutang)
            return {"status": "success", "message": "Hutang berhasil diperbarui"}, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 400
        
    @role_required("admin")
    def delete(self, id_hutang):
        """Akses: (admin), Soft delete hutang dengan mengganti status jadi 0"""
        data = get_hutang_by_id(id_hutang)
        if not data:
            return {"status": "not found", "message": "Hutang tidak ditemukan"}, 404

        try:
            affected_rows = soft_delete_hutang_by_id(id_hutang)
            if affected_rows == 0:
                return {"status": "fail", "message": "Hutang sudah dihapus"}, 400
            return {"status": "success", "message": "Hutang berhasil dihapus"}, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
        

@hutang_ns.route("/karyawan/<int:id_karyawan>")
class HutangByKaryawan(Resource):
    @hutang_ns.doc(params={
        'status_hutang': '(optional) Filter berdasarkan status hutang [lunas, belum lunas]',
    })
    @role_required("admin")
    def get(self, id_karyawan):
        """Akses: (admin), Get daftar hutang dan total hutang berdasarkan ID karyawan"""
        status_hutang = request.args.get("status_hutang", None)
        try:
            result = get_hutang_by_karyawan(id_karyawan, status_hutang=status_hutang)
            if result is None:
                return {"message": "Gagal mengambil data hutang"}, 500

            return {
                "status": "success",
                "message": "Berhasil mengambil data hutang",
                "data": result["data"],
                "total_hutang": result["total_hutang"]
            }, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
        

@hutang_ns.route('/pembayaran')
class PembayaranHutangResource(Resource):
    @hutang_ns.expect(pembayaran_hutang_parser)
    @role_required("admin")
    def post(self):
        """Akses: (admin), Pembayaran hutang baik itu dengan pemotongan gaji atau tunai"""
        args = pembayaran_hutang_parser.parse_args()

        id_karyawan = args.get('id_karyawan')
        nominal = args.get('nominal')
        metode = args.get('metode')
        keterangan = args.get('keterangan') or ''
        id_hutang = args.get('id_hutang')

        if nominal <= 0:
            return {"message": "Nominal harus lebih dari 0"}, 400

        try:
            result, status = create_pembayaran_hutang_by_karyawan(
                id_karyawan=id_karyawan,
                nominal=nominal,
                metode=metode,
                keterangan=keterangan,
                id_hutang=id_hutang
            )
            return result, status
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
        
    @hutang_ns.doc(params={
        'bulan': '(opsional) Format YYYY-MM, default bulan ini',
        'id_karyawan': '(opsional) Filter berdasarkan ID karyawan',
        'metode': '(opsional) Filter berdasarkan metode pembayaran (misal: tunai, potong gaji)'
    })
    @role_required("admin")
    def get(self):
        """Akses: (admin), Mendapatkan riwayat pembayaran hutang"""
        try:
            bulan = request.args.get("bulan", None)
            id_karyawan = request.args.get("id_karyawan", None)
            metode = request.args.get("metode", None)

            data = get_pembayaran_hutang(bulan=bulan, id_karyawan=id_karyawan, metode=metode)

            return {
                "status": "success",
                "message": "Berhasil mengambil riwayat pembayaran",
                "data": data
            }, 200
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500