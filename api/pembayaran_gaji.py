# pembayaran_gaji.py
from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from datetime import date
import calendar

from .utils.decorator import role_required
from .query.q_pembayaran_gaji import *


pembayaran_gaji_ns = Namespace("pembayaran-gaji", description="Manajemen pembayaran gaji")

detail_model = pembayaran_gaji_ns.model("DetailPembayaranGaji", {
    "id_karyawan": fields.Integer(required=True, description="ID Karyawan"),
    "bulan": fields.Integer(required=True, description="Bulan pembayaran (1-12)"),
    "tahun": fields.Integer(required=True, description="Tahun pembayaran"),
    "komponen": fields.String(required=True, description="Komponen pembayaran (gaji_bersih, tunjangan, lembur)"),
    "jumlah": fields.Integer(required=True, description="Jumlah pembayaran"),
    "metode": fields.String(required=False, description="Metode pembayaran (transfer/tunai)", default="transfer"),
    "keterangan": fields.String(required=False, description="Keterangan tambahan"),
})

detail_pembayaran_model = pembayaran_gaji_ns.model("DetailPembayaranGaji", {
    "id_karyawan": fields.Integer(required=True, description="ID Karyawan"),
    "bulan": fields.Integer(required=True, description="Bulan pembayaran (1-12)"),
    "tahun": fields.Integer(required=True, description="Tahun pembayaran"),
    "metode": fields.String(required=False, description="Metode pembayaran (transfer/tunai)", default="transfer"),
})

def insert_komponen_pembayaran(id_karyawan, perhitungan, bulan, tahun, komponen, jumlah, metode, keterangan):
    """
    Helper untuk insert detail pembayaran 1 komponen (gaji_pokok, tunjangan, lembur).
    """
    data_pembayaran = {
        "id_karyawan": id_karyawan,
        "bulan": bulan,
        "tahun": tahun,
        "gaji_bersih": perhitungan["gaji_bersih"],
        "tunjangan": perhitungan["tunjangan"],
        "lembur": perhitungan["lembur"],
        "total_dibayar": perhitungan["total_dibayar"],
        "komponen": komponen,
        "jumlah": jumlah,
        "metode": metode,
        "keterangan": keterangan,
    }

    return insert_detail_pembayaran(id_karyawan, data_pembayaran)


@pembayaran_gaji_ns.route('/')
class PembayaranGajiResource(Resource):
    @pembayaran_gaji_ns.doc(params={
        "bulan": "Bulan pembayaran (1-12)",
        "tahun": "Tahun pembayaran",
        "id_karyawan": "Opsional, filter berdasarkan karyawan tertentu"
    })
    @jwt_required()
    def get(self):
        """Ambil daftar pembayaran gaji beserta detail, filter bulan & tahun"""
        bulan = request.args.get("bulan", type=int)
        tahun = request.args.get("tahun", type=int)
        id_user = get_jwt_identity()
        role = get_jwt().get("role")

        id_karyawan = request.args.get('id_karyawan') if role == 'admin' else id_user
        if role == 'admin' and id_karyawan:
            id_karyawan = int(id_karyawan)

        if not bulan or not tahun:
            return {"status": "bulan dan tahun wajib diisi"}, 400

        rows = get_pembayaran_gaji(bulan, tahun, id_karyawan)

        # transformasi: group detail berdasarkan id_pembayaran
        result = {}
        for row in rows:
            id_pembayaran = row["id_pembayaran"]
            if id_pembayaran not in result:
                result[id_pembayaran] = {
                    "id_pembayaran": row["id_pembayaran"],
                    "id_karyawan": row["id_karyawan"],
                    "bulan": row["bulan"],
                    "tahun": row["tahun"],
                    "gaji_pokok": row["gaji_pokok"],
                    "tunjangan": row["tunjangan"],
                    "lembur": row["lembur"],
                    "total_dibayar": row["total_dibayar"],
                    "status_pembayaran": row["status_pembayaran"],
                    "detail": []
                }
            if row["id_detail"]:
                result[id_pembayaran]["detail"].append({
                    "id_detail": row["id_detail"],
                    "komponen": row["komponen"],
                    "jumlah": row["jumlah"],
                    "tanggal_bayar": row["tanggal_bayar"].isoformat() if row["tanggal_bayar"] else None,
                    "metode": row["metode"],
                    "keterangan": row["keterangan"],
                })

        return list(result.values())
    
    @pembayaran_gaji_ns.expect(detail_pembayaran_model)
    @role_required('admin')
    def post(self):
        """Akses: (admin), Tambah pembayaran gaji pokok + tunjangan + lemburan"""
        data = pembayaran_gaji_ns.payload
        id_karyawan = data.get("id_karyawan")
        bulan = data.get("bulan")
        tahun = data.get("tahun")

        sudah_gaji = cek_detail_sudah_ada(id_karyawan, bulan, tahun, komponen="gaji_pokok")
        sudah_tunjangan = cek_detail_sudah_ada(id_karyawan, bulan, tahun, komponen="tunjangan")
        sudah_lembur = cek_detail_sudah_ada(id_karyawan, bulan, tahun, komponen="lembur")
        if sudah_gaji or sudah_tunjangan or sudah_lembur:
            return {
                "status": "error",
                "message": f"ada sebagian gaji untuk bulan ini sudah dibayarkan."
            }, 500

        start = date(tahun, bulan, 1)
        end = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])

        perhitungan = hitung_pembayaran_gaji(start, end, id_karyawan)
        if not perhitungan:
            return {"status": "Data gaji tidak ditemukan"}, 404

        metode = data.get("metode", "transfer")
        keterangan = f"pembayaran keseluruhan gaji {perhitungan['nama']}"

        # List komponen yang mau dimasukkan
        komponen_list = [
            ("gaji_pokok", perhitungan["gaji_bersih"]),
            ("tunjangan", perhitungan["tunjangan"]),
            ("lembur", perhitungan["lembur"]),
        ]

        inserted_details = []
        for komponen, jumlah in komponen_list:
            if jumlah and jumlah > 0:  # hanya insert kalau ada nilai
                id_detail = insert_komponen_pembayaran(
                    id_karyawan, perhitungan, bulan, tahun,
                    komponen, jumlah, metode, keterangan
                )
                if not id_detail:
                    return {"status": f"Gagal insert detail {komponen}"}, 500
                inserted_details.append({"id_detail": id_detail, "komponen": komponen})

        return {"status": "success", "details": inserted_details}, 201
    

@pembayaran_gaji_ns.route('/pokok-tunjangan')
class PembayaranGajiDanTunjanganResource(Resource):
    @pembayaran_gaji_ns.expect(detail_pembayaran_model)
    @role_required('admin')
    def post(self):
        """Akses: (admin), Tambah pembayaran gaji pokok + tunjangan sekaligus"""
        data = pembayaran_gaji_ns.payload
        id_karyawan = data.get("id_karyawan")
        bulan = data.get("bulan")
        tahun = data.get("tahun")

        sudah_gaji = cek_detail_sudah_ada(id_karyawan, bulan, tahun, komponen="gaji_pokok")
        sudah_tunjangan = cek_detail_sudah_ada(id_karyawan, bulan, tahun, komponen="tunjangan")
        if sudah_gaji or sudah_tunjangan:
            return {
                "status": "error",
                "message": f"ada sebagian gaji untuk bulan ini sudah dibayarkan."
            }, 500

        start = date(tahun, bulan, 1)
        end = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])

        perhitungan = hitung_pembayaran_gaji(start, end, id_karyawan)
        if not perhitungan:
            return {"status": "Data gaji tidak ditemukan"}, 404

        metode = data.get("metode", "transfer")
        keterangan = f"pembayaran gaji pokok + tunjangan {perhitungan['nama']}"

        # List komponen yang mau dimasukkan
        komponen_list = [
            ("gaji_pokok", perhitungan["gaji_bersih"]),
            ("tunjangan", perhitungan["tunjangan"]),
        ]

        inserted_details = []
        for komponen, jumlah in komponen_list:
            if jumlah and jumlah > 0:  # hanya insert kalau ada nilai
                id_detail = insert_komponen_pembayaran(
                    id_karyawan, perhitungan, bulan, tahun,
                    komponen, jumlah, metode, keterangan
                )
                if not id_detail:
                    return {"status": f"Gagal insert detail {komponen}"}, 500
                inserted_details.append({"id_detail": id_detail, "komponen": komponen})

        return {"status": "success", "details": inserted_details}, 201
    

@pembayaran_gaji_ns.route('/gaji-pokok')
class PembayaranGajiPokokResource(Resource):
    @pembayaran_gaji_ns.expect(detail_pembayaran_model)
    @role_required('admin')
    def post(self):
        """Akses: (admin), Tambah pembayaran gaji pokok"""
        data = pembayaran_gaji_ns.payload
        id_karyawan = data.get("id_karyawan")
        bulan = data.get("bulan")
        tahun = data.get("tahun")

        start = date(tahun, bulan, 1)
        end = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])

        perhitungan = hitung_pembayaran_gaji(start, end, id_karyawan)
        if not perhitungan:
            return {"status": "Data gaji tidak ditemukan"}, 404

        metode = data.get("metode", "transfer")
        keterangan = f"pembayaran gaji pokok {perhitungan['nama']}"

        sudah_ada = cek_detail_sudah_ada(id_karyawan, bulan, tahun, komponen="gaji_bersih")
        if sudah_ada:
            return {
                "status": "error",
                "message": f"gaji pokok untuk bulan ini sudah dibayarkan."
            }, 500

        id_detail_pembayaran = insert_komponen_pembayaran(
            id_karyawan=id_karyawan,
            perhitungan=perhitungan,
            bulan=bulan,
            tahun=tahun,
            komponen="gaji_bersih",
            jumlah=perhitungan["gaji_bersih"],
            metode=metode,
            keterangan=keterangan
        )

        if not id_detail_pembayaran:
            return {"status": "Gagal insert detail gaji pokok"}, 500

        return {
            "status": "success",
            "details": [
                {"id_detail": id_detail_pembayaran, "komponen": "gaji_pokok"}
            ]
        }, 201
    

@pembayaran_gaji_ns.route('/tunjangan')
class PembayaranTunjanganResource(Resource):
    @pembayaran_gaji_ns.expect(detail_pembayaran_model)
    @role_required('admin')
    def post(self):
        """Akses: (admin), Tambah pembayaran tunjangan"""
        data = pembayaran_gaji_ns.payload
        id_karyawan = data.get("id_karyawan")
        bulan = data.get("bulan")
        tahun = data.get("tahun")

        start = date(tahun, bulan, 1)
        end = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])

        perhitungan = hitung_pembayaran_gaji(start, end, id_karyawan)
        if not perhitungan:
            return {"status": "Data gaji tidak ditemukan"}, 404

        metode = data.get("metode", "transfer")
        keterangan = f"pembayaran tunjangan {perhitungan['nama']}"

        sudah_ada = cek_detail_sudah_ada(id_karyawan, bulan, tahun, komponen="tunjangan")
        if sudah_ada:
            return {
                "status": "error",
                "message": f"tunjangan untuk bulan ini sudah dibayarkan."
            }, 500

        id_detail_pembayaran = insert_komponen_pembayaran(
            id_karyawan=id_karyawan,
            perhitungan=perhitungan,
            bulan=bulan,
            tahun=tahun,
            komponen="tunjangan",
            jumlah=perhitungan["tunjangan"],
            metode=metode,
            keterangan=keterangan
        )

        if not id_detail_pembayaran:
            return {"status": "Gagal insert detail tunjangan"}, 500

        return {
            "status": "success",
            "details": [
                {"id_detail": id_detail_pembayaran, "komponen": "tunjangan"}
            ]
        }, 201

@pembayaran_gaji_ns.route('/lemburan')
class PembayaranLemburanResource(Resource):
    @pembayaran_gaji_ns.expect(detail_pembayaran_model)
    @role_required('admin')
    def post(self):
        """Akses: (admin), Tambah pembayaran lemburan"""
        data = pembayaran_gaji_ns.payload
        id_karyawan = data.get("id_karyawan")
        bulan = data.get("bulan")
        tahun = data.get("tahun")

        start = date(tahun, bulan, 1)
        end = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])

        perhitungan = hitung_pembayaran_gaji(start, end, id_karyawan)
        if not perhitungan:
            return {"status": "Data gaji tidak ditemukan"}, 404

        metode = data.get("metode", "transfer")
        keterangan = f"pembayaran lemburan {perhitungan['nama']}"

        id_detail_pembayaran = insert_komponen_pembayaran(
            id_karyawan=id_karyawan,
            perhitungan=perhitungan,
            bulan=bulan,
            tahun=tahun,
            komponen="lembur",
            jumlah=perhitungan["lembur"],
            metode=metode,
            keterangan=keterangan
        )

        if not id_detail_pembayaran:
            return {"status": "Gagal insert detail lembur"}, 500

        return {
            "status": "success",
            "details": [
                {"id_detail": id_detail_pembayaran, "komponen": "lembur"}
            ]
        }, 201
    