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
    

@payroll_ns.route('/preview/masal')
class PreviewPayrollMasalResource(Resource):
    @jwt_required()
    @payroll_ns.expect(payroll_masal_parser)
    def get(self):
        args = payroll_masal_parser.parse_args()

        hasil = preview_payroll_masal_fast(
            args['bulan'],
            args['tahun']
        )

        if not hasil:
            return {
                "status": "error",
                "message": "Gagal generate preview payroll masal"
            }, 500

        return hasil, 200