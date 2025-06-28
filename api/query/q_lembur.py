from datetime import date, datetime, time, timedelta
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection, get_wita


def hitung_bayaran_lembur(id_karyawan, tanggal, jam_mulai, jam_selesai):
    engine = get_connection()
    with engine.connect() as conn:
        # Ambil gaji pokok
        q = text("SELECT gaji_pokok FROM karyawan WHERE id_karyawan = :id_karyawan")
        result = conn.execute(q, {"id_karyawan": id_karyawan}).fetchone()
        if not result or result.gaji_pokok is None:
            return None
        gaji_pokok = result.gaji_pokok

        # Ambil semua libur nasional aktif di bulan yang sama
        first_day = tanggal.replace(day=1)
        next_month = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1)
        last_day = (next_month - timedelta(days=1)).day

        start_date = first_day
        end_date = tanggal.replace(day=last_day)

        libur_query = text("""
            SELECT tanggal FROM liburnasional
            WHERE status = 1 AND tanggal BETWEEN :start AND :end
        """)
        libur_result = conn.execute(libur_query, {
            "start": start_date,
            "end": end_date
        }).fetchall()

        libur_dates = set([row.tanggal for row in libur_result])

        # Hitung hari kerja reguler (tanpa Minggu dan hari libur nasional)
        hari_reguler = sum(
            1 for d in range(1, last_day + 1)
            if (
                datetime(tanggal.year, tanggal.month, d).weekday() != 6 and
                datetime(tanggal.year, tanggal.month, d).date() not in libur_dates
            )
        )

        if hari_reguler == 0:
            return None  # Hindari pembagian nol

        gaji_per_hari = gaji_pokok / hari_reguler
        gaji_per_jam = gaji_per_hari / 8

        # Hitung bayaran per jam lembur (pakai pengali 2)
        bayaran_perjam = round(gaji_per_jam * 2, 2)

        # Hitung durasi kerja
        mulai_dt = datetime.combine(date.today(), jam_mulai)
        selesai_dt = datetime.combine(date.today(), jam_selesai)
        if jam_selesai <= jam_mulai:
            selesai_dt += timedelta(days=1)

        durasi_jam = (selesai_dt - mulai_dt).total_seconds() / 3600
        durasi_jam = min(durasi_jam, 8)  # Batasi maksimal 8 jam

        total_bayaran = round(durasi_jam * bayaran_perjam, 2)

        return {
            'bayaran_perjam': bayaran_perjam,
            'total_bayaran': total_bayaran
        }

def insert_pengajuan_lembur(data):
    engine = get_connection()
    try:
        with engine.begin() as conn:
            query = text("""
                INSERT INTO lembur (
                    id_karyawan, tanggal, jam_mulai, jam_selesai,
                    keterangan, path_lampiran,
                    status_lembur, status,
                    bayaran_perjam, total_bayaran,
                    created_at, updated_at
                ) VALUES (
                    :id_karyawan, :tanggal, :jam_mulai, :jam_selesai,
                    :keterangan, :path_lampiran,
                    'pending', 1,
                    :bayaran_perjam, :total_bayaran,
                    :timestamp_wita, :timestamp_wita
                )
            """)
            conn.execute(query, {
                "id_karyawan": data['id_karyawan'],
                "tanggal": data['tanggal'],
                "jam_mulai": data['jam_mulai'],
                "jam_selesai": data['jam_selesai'],
                "keterangan": data['keterangan'],
                "path_lampiran": data['path_lampiran'],
                "bayaran_perjam": data['bayaran_perjam'],
                "total_bayaran": data['total_bayaran'],
                "timestamp_wita": get_wita()
            })
            return 1
    except SQLAlchemyError as e:
        print("DB Error:", str(e))
        return None
    
def get_daftar_lembur(status_lembur=None, id_karyawan=None, tanggal=None):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = """
                SELECT l.id_lembur, l.id_karyawan, k.nama AS nama_karyawan,
                       l.tanggal, l.jam_mulai, l.jam_selesai,
                       l.keterangan, l.path_lampiran, l.status_lembur,
                       l.alasan_penolakan, l.bayaran_perjam, l.total_bayaran,
                       l.created_at, l.updated_at
                FROM lembur l
                JOIN karyawan k ON l.id_karyawan = k.id_karyawan
                WHERE l.status = 1
            """
            params = {}

            if status_lembur:
                query += " AND l.status_lembur = :status_lembur"
                params['status_lembur'] = status_lembur
            if id_karyawan:
                query += " AND l.id_karyawan = :id_karyawan"
                params['id_karyawan'] = int(id_karyawan)
            if tanggal:
                query += " AND l.tanggal = :tanggal"
                params['tanggal'] = tanggal

            query += " ORDER BY l.created_at DESC"

            result = connection.execute(text(query), params).mappings().fetchall()

            data = []
            for row in result:
                row_dict = {
                    key: value.isoformat() if isinstance(value, (datetime, date, time)) else value
                    for key, value in row.items()
                }

                # Hitung jam lembur
                jam_mulai = row['jam_mulai']
                jam_selesai = row['jam_selesai']
                if isinstance(jam_mulai, time) and isinstance(jam_selesai, time):
                    mulai_dt = datetime.combine(date.today(), jam_mulai)
                    selesai_dt = datetime.combine(date.today(), jam_selesai)
                    if jam_selesai <= jam_mulai:
                        selesai_dt += timedelta(days=1)
                    durasi = selesai_dt - mulai_dt
                    jam_lembur = round(durasi.total_seconds() / 3600, 2)
                    row_dict['jam_lembur'] = jam_lembur
                else:
                    row_dict['jam_lembur'] = None

                data.append(row_dict)

            return data
    except SQLAlchemyError as e:
        print(f"DB Error: {str(e)}")
        return None
    
def get_daftar_lembur_oleh_karyawan(id_karyawan, tanggal=None):
    if tanggal is None:
        tanggal = date.today()

    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = """
                SELECT l.id_lembur, l.id_karyawan, k.nama AS nama_karyawan,
                       l.tanggal, l.jam_mulai, l.jam_selesai,
                       l.keterangan, l.path_lampiran, l.status_lembur,
                       l.alasan_penolakan, l.bayaran_perjam, l.total_bayaran,
                       l.created_at, l.updated_at
                FROM lembur l
                JOIN karyawan k ON l.id_karyawan = k.id_karyawan
                WHERE l.status = 1
                  AND l.id_karyawan = :id_karyawan
                  AND l.tanggal = :tanggal
                ORDER BY l.created_at DESC
            """
            params = {
                'id_karyawan': id_karyawan,
                'tanggal': tanggal
            }

            result = connection.execute(text(query), params).mappings().fetchall()

            data = []
            for row in result:
                row_dict = {}
                for key, value in row.items():
                    if isinstance(value, (datetime, date, time)):
                        row_dict[key] = value.isoformat()
                    else:
                        row_dict[key] = value
                data.append(row_dict)

            return data

    except SQLAlchemyError as e:
        print(f"DB Error: {str(e)}")
        return None

def setujui_lembur(id_lembur):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                UPDATE lembur
                SET status_lembur = 'approved',
                    updated_at = :timestamp_wita
                WHERE id_lembur = :id_lembur
            """), {
                "id_lembur": id_lembur,
                "timestamp_wita": get_wita()
            })

            return 1  # Berhasil
    except SQLAlchemyError as e:
        print(f"[DB Error] Gagal setujui lembur: {e}")
        return None

def tolak_lembur(id_lembur):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                UPDATE lembur
                SET status_lembur = 'rejected',
                    updated_at = :timestamp_wita
                WHERE id_lembur = :id_lembur
            """), {
                "id_lembur": id_lembur,
                "timestamp_wita": get_wita()
            })

            return 1  # Berhasil
    except SQLAlchemyError as e:
        print(f"[DB Error] Gagal tolak lembur: {e}")
        return None

def hapus_lembur(id_lembur):
    engine = get_connection()
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    UPDATE lembur
                    SET status = 0, updated_at = :updated_at
                    WHERE id_lembur = :id_lembur
                """),
                {
                    "id_lembur": id_lembur,
                    "updated_at": get_wita()
                }
            )
            return True
    except SQLAlchemyError as e:
        print(f"DB Error (hapus_lembur): {str(e)}")
        return False
