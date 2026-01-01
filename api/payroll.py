from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required

from .query.q_payroll import *


payroll_ns = Namespace('payroll', description='Endpoint Payroll')

payroll_preview_parser = reqparse.RequestParser()
payroll_preview_parser.add_argument('id_karyawan', type=int, required=True, location='args')
payroll_preview_parser.add_argument('bulan', type=int, required=True, location='args')
payroll_preview_parser.add_argument('tahun', type=int, required=True, location='args')

payroll_masal_parser = reqparse.RequestParser()
payroll_masal_parser.add_argument('bulan', type=int, required=True, location='args')
payroll_masal_parser.add_argument('tahun', type=int, required=True, location='args')


@payroll_ns.route('/preview')
class PreviewPayrollResource(Resource):
    @jwt_required()
    @payroll_ns.expect(payroll_preview_parser)
    def get(self):
        args = payroll_preview_parser.parse_args()

        hasil = preview_payroll_final(
            args['id_karyawan'],
            args['bulan'],
            args['tahun']
        )

        if not hasil:
            return {
                "status": "error",
                "message": "Gagal generate preview payroll"
            }, 500

        return hasil, 200
    
    
@payroll_ns.route('/generate/all')
class GeneratePayrollMasalResource(Resource):
    @jwt_required()
    @payroll_ns.expect(payroll_masal_parser)
    def post(self):
        args = payroll_masal_parser.parse_args()

        hasil = generate_payroll_masal(
            bulan=args['bulan'],
            tahun=args['tahun']
        )

        if not hasil:
            return {
                "status": "error",
                "message": "Gagal generate payroll masal"
            }, 500

        return {
            "status": "success",
            "message": "Payroll masal berhasil digenerate",
            "data": hasil
        }, 200
        

@payroll_ns.route('/all')
class GetPayrollAllResource(Resource):
    @jwt_required()
    @payroll_ns.expect(payroll_masal_parser)
    def get(self):
        args = payroll_masal_parser.parse_args()

        hasil = get_payroll_all(
            args['bulan'],
            args['tahun']
        )

        if not hasil:
            return {
                "status": "error",
                "message": "Data payroll tidak ditemukan"
            }, 404

        return hasil, 200
    
@payroll_ns.route('/detail/<int:id_penggajian>')
class PayrollDetailResource(Resource):
    @jwt_required()
    def get(self, id_penggajian):
        hasil = get_payroll_detail(id_penggajian)

        if not hasil:
            return {
                "status": "error",
                "message": "Data payroll tidak ditemukan"
            }, 404

        return hasil, 200

