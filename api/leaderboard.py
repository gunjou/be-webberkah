from datetime import timedelta
from flask_restx import Namespace, Resource, reqparse

from .query.q_leaderboard import *
from .utils.decorator import role_required


leaderboard_ns = Namespace('leaderboard', description='Leaderboard untuk melihat peringkat')

# Parser untuk query parameter
leaderboard_parser = reqparse.RequestParser()
leaderboard_parser.add_argument('start_date', type=str, required=False, help='Format: YYYY-MM-DD')
leaderboard_parser.add_argument('end_date', type=str, required=False, help='Format: YYYY-MM-DD')

@leaderboard_ns.route('/')
class LeaderboardResource(Resource):
    @role_required('admin')
    @leaderboard_ns.expect(leaderboard_parser)
    def get(self):
        """Akses: (admin), Menampilkan urutan peringkat pegawai paling rajin"""
        args = leaderboard_parser.parse_args()
        today = datetime.today().date()

        # Ambil nilai awal dari parameter
        raw_start_date = args.get('start_date')
        raw_end_date = args.get('end_date')

        # Tangani string kosong menjadi None
        start_date = raw_start_date if raw_start_date not in [None, ""] else None
        end_date = raw_end_date if raw_end_date not in [None, ""] else None

        try:
            # Konversi ke objek date jika ada
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return {'message': 'Format tanggal tidak valid. Gunakan YYYY-MM-DD.'}, 400

        # Terapkan fallback tanggal
        if start_date is None and end_date is None:
            start_date = today.replace(day=1)
            end_date = today
        elif start_date is not None and end_date is None:
            end_date = today
        elif end_date is not None and start_date is None:
            start_date = end_date.replace(day=1)

        hasil = get_leaderboard_kerajinan(start_date, end_date)

        if hasil is None:
            return {'status': 'Gagal mengambil data peringkat paling rajin'}, 500

        return {
            'start_date': str(start_date),
            'end_date': str(end_date),
            'data': hasil
        }, 200