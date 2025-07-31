from datetime import date, datetime, time, timedelta
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.config import get_connection, get_wita


def hitung_bayaran_lembur(id_karyawan, tanggal, jam_mulai, jam_selesai):
    engine = get_connection()
    with engine.connect() as conn:
        # Ambil gaji pokok
        q = text("SELECT gaji_pokok, id_jenis FROM karyawan WHERE id_karyawan = :id_karyawan AND status = 1")
        result = conn.execute(q, {"id_karyawan": id_karyawan}).fetchone()
        if not result or result.gaji_pokok is None:
            return None
        gaji_pokok = result.gaji_pokok
        id_jenis = result.id_jenis

        # Cek apakah tanggal adalah hari libur nasional
        libur_query = text("""
            SELECT 1 FROM liburnasional
            WHERE status = 1 AND tanggal = :tanggal
            LIMIT 1
        """)
        libur_result = conn.execute(libur_query, {"tanggal": tanggal}).scalar()

        is_minggu = tanggal.weekday() == 6
        is_libur = is_minggu or libur_result is not None

        gaji_per_hari = gaji_pokok / 26
        gaji_per_jam = gaji_per_hari / 8

        # Tentukan pengali berdasarkan jenis karyawan dan hari
        if id_jenis == 6:  # K3 Lapangan
            pengali = 2.0 if is_libur else 1.0
        else:  # Selain K3 Lapangan
            pengali = 2.0 if is_libur else 1.25

        bayaran_perjam = round(gaji_per_jam * pengali)

        # Hitung durasi kerja
        mulai_dt = datetime.combine(date.today(), jam_mulai)
        selesai_dt = datetime.combine(date.today(), jam_selesai)
        if jam_selesai <= jam_mulai:
            selesai_dt += timedelta(days=1)

        total_durasi = (selesai_dt - mulai_dt).total_seconds() / 3600  # dalam jam

        # Penyesuaian jam istirahat (potong 1 jam jika dalam rentang pagi dan hari libur)
        if is_libur and jam_mulai >= time(7, 0) and jam_selesai <= time(17, 0):
            total_durasi -= 1

            # Batas maksimal 8 jam lembur
            if total_durasi > 8:
                total_durasi = 8

        # Jika di luar waktu tersebut, tidak dipotong istirahat atau tidak dibatasi
        total_durasi = max(total_durasi, 0)
        total_bayaran = round(total_durasi * bayaran_perjam)
        menit_lembur = round(total_durasi * 60)

        return {
            'bayaran_perjam': bayaran_perjam,
            'total_bayaran': total_bayaran,
            'menit_lembur': menit_lembur,
        }

def insert_pengajuan_lembur(data):
    engine = get_connection()
    try:
        with engine.begin() as conn:
            query = text("""
                INSERT INTO lembur (
                    id_karyawan, tanggal, jam_mulai, jam_selesai,
                    keterangan, path_lampiran,
                    status_lembur, status, menit_lembur,
                    bayaran_perjam, total_bayaran,
                    created_at, updated_at
                ) VALUES (
                    :id_karyawan, :tanggal, :jam_mulai, :jam_selesai,
                    :keterangan, :path_lampiran,
                    'pending', 1, :menit_lembur,
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
                "menit_lembur": data['menit_lembur'],
                "bayaran_perjam": data['bayaran_perjam'],
                "total_bayaran": data['total_bayaran'],
                "timestamp_wita": get_wita()
            })
            return 1
    except SQLAlchemyError as e:
        print("DB Error:", str(e))
        return None
    
def get_daftar_lembur(status_lembur=None, id_karyawan=None, start_date=None, end_date=None, tanggal=None):
    engine = get_connection()
    try:
        with engine.connect() as connection:
            query = """
                SELECT l.id_lembur, l.id_karyawan, k.nama AS nama_karyawan,
                       l.tanggal, l.jam_mulai, l.jam_selesai,
                       l.keterangan, l.path_lampiran, l.status_lembur,
                       l.alasan_penolakan, l.bayaran_perjam, l.total_bayaran, l.menit_lembur,
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
            elif start_date and end_date:
                query += " AND l.tanggal BETWEEN :start_date AND :end_date"
                params['start_date'] = start_date
                params['end_date'] = end_date

            query += " ORDER BY l.created_at DESC"

            result = connection.execute(text(query), params).mappings().fetchall()

            data = []
            for row in result:
                row_dict = {
                    key: value.isoformat() if isinstance(value, (datetime, date, time)) else value
                    for key, value in row.items()
                }

                # # Hitung jam lembur
                # jam_mulai = row['jam_mulai']
                # jam_selesai = row['jam_selesai']
                # if isinstance(jam_mulai, time) and isinstance(jam_selesai, time):
                #     mulai_dt = datetime.combine(date.today(), jam_mulai)
                #     selesai_dt = datetime.combine(date.today(), jam_selesai)
                #     if jam_selesai <= jam_mulai:
                #         selesai_dt += timedelta(days=1)
                #     durasi = selesai_dt - mulai_dt
                #     row_dict['jam_lembur'] = round(durasi.total_seconds() / 3600, 2)
                # else:
                #     row_dict['jam_lembur'] = None

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
    
def update_lembur_by_id(data):
    engine = get_connection()
    try:
        with engine.begin() as conn:
            query = text("""
                UPDATE lembur
                SET jam_mulai = :jam_mulai,
                    jam_selesai = :jam_selesai,
                    keterangan = :keterangan,
                    menit_lembur = :menit_lembur,
                    bayaran_perjam = :bayaran_perjam,
                    total_bayaran = :total_bayaran,
                    updated_at = :updated_at
                WHERE id_lembur = :id_lembur AND status = 1
            """)
            conn.execute(query, {
                "jam_mulai": data['jam_mulai'],
                "jam_selesai": data['jam_selesai'],
                "keterangan": data['keterangan'],
                "menit_lembur": data['menit_lembur'],
                "bayaran_perjam": data['bayaran_perjam'],
                "total_bayaran": data['total_bayaran'],
                "updated_at": get_wita(),
                "id_lembur": data['id_lembur']
            })
            return 1
    except SQLAlchemyError as e:
        print(f"Update Lembur Error: {str(e)}")
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
