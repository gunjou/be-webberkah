from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..utils.helpers import serialize_row
from ..utils.config import get_connection, get_wita, get_timezone

def get_all_hutang(status_hutang=None):
    engine = get_connection()
    try:
        with engine.connect() as conn:
            base_query = """
                SELECT 
                    h.id_hutang, h.id_karyawan, k.nama, k.nama_panggilan, h.nominal, h.keterangan,
                    h.status_hutang, h.tanggal, h.created_at, h.updated_at
                FROM hutang h
                JOIN karyawan k ON k.id_karyawan = h.id_karyawan
                WHERE h.status = 1 AND k.status = 1
            """

            # Tambahkan filter jika status_hutang diberikan
            if status_hutang:
                base_query += " AND h.status_hutang = :status_hutang"

            base_query += " ORDER BY h.created_at DESC;"

            stmt = text(base_query)

            if status_hutang:
                result = conn.execute(stmt, {"status_hutang": status_hutang})
            else:
                result = conn.execute(stmt)

            return [serialize_row(row) for row in result.mappings().fetchall()]
    except SQLAlchemyError as e:
        print(f"[error GET hutang] {e}")
        return []

def insert_hutang(id_karyawan, tanggal, nominal, keterangan):
    engine = get_connection()
    try:
        with engine.begin() as conn:
            now = datetime.now()
            query = text("""
                INSERT INTO hutang (
                    id_karyawan, tanggal, nominal, keterangan,
                    status_hutang, status, created_at, updated_at
                ) VALUES (
                    :id_karyawan, :tanggal, :nominal, :keterangan,
                    'belum lunas', 1, :created_at, :updated_at
                )
            """)
            conn.execute(query, {
                "id_karyawan": id_karyawan,
                "tanggal": tanggal,
                "nominal": nominal,
                "keterangan": keterangan,
                "created_at": now,
                "updated_at": now
            })
            return True
    except SQLAlchemyError as e:
        print(f"[error INSERT hutang] {e}")
        return None
    
def get_hutang_by_id(id_hutang):
    engine = get_connection()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    h.id_hutang, h.id_karyawan, k.nama, k.nama_panggilan, h.nominal, h.keterangan,
                    h.status_hutang, h.tanggal, h.created_at, h.updated_at
                FROM hutang h
                JOIN karyawan k ON k.id_karyawan = h.id_karyawan
                WHERE h.status = 1 AND h.id_hutang = :id_hutang
                LIMIT 1;
            """), {"id_hutang": id_hutang})
            row = result.mappings().fetchone()
            return serialize_row(row) if row else None
    except SQLAlchemyError as e:
        print(f"[error GET hutang by id] {e}")
        return None

def update_hutang_by_id(id_hutang, nominal, keterangan, status_hutang):
    engine = get_connection()
    try:
        with engine.begin() as conn:
            update_query = text("""
                UPDATE hutang
                SET nominal = :nominal,
                    keterangan = :keterangan,
                    status_hutang = :status_hutang,
                    updated_at = :timestamp_wita
                WHERE id_hutang = :id_hutang AND status = 1
            """)
            conn.execute(update_query, {
                "nominal": nominal,
                "keterangan": keterangan,
                "status_hutang": status_hutang,
                "timestamp_wita": get_wita(),
                "id_hutang": id_hutang
            })

            return True
    except SQLAlchemyError as e:
        print(f"[error UPDATE hutang] {e}")
        return None

def soft_delete_hutang_by_id(id_hutang):
    engine = get_connection()
    try:
        with engine.begin() as conn:
            delete_query = text("""
                UPDATE hutang
                SET status = 0,
                    updated_at = :timestamp_wita
                WHERE id_hutang = :id_hutang AND status = 1
            """)
            conn.execute(delete_query, {
                "id_hutang": id_hutang,
                "timestamp_wita": get_wita()
            })
            return True
    except SQLAlchemyError as e:
        print(f"[error SOFT DELETE hutang] {e}")
        return None
    
def get_hutang_by_karyawan(id_karyawan, status_hutang=None):
    engine = get_connection()
    try:
        with engine.connect() as conn:
            base_query = """
                SELECT 
                    h.id_hutang, h.id_karyawan, k.nama, k.nama_panggilan, h.nominal, h.keterangan, 
                    h.status_hutang, h.created_at, h.updated_at
                FROM hutang h
                JOIN karyawan k ON k.id_karyawan = h.id_karyawan
                WHERE h.id_karyawan = :id_karyawan AND h.status = 1 AND k.status = 1
            """

            params = {"id_karyawan": id_karyawan}

            if status_hutang in ["lunas", "belum lunas"]:
                base_query += " AND h.status_hutang = :status_hutang"
                params["status_hutang"] = status_hutang

            result = conn.execute(text(base_query), params).mappings().all()
            list_hutang = [serialize_row(row) for row in result]

            # Query total nominal hutang
            total_query = """
                SELECT COALESCE(SUM(nominal), 0) AS total_hutang
                FROM hutang
                WHERE id_karyawan = :id_karyawan AND status = 1
            """
            if status_hutang in ["lunas", "belum lunas"]:
                total_query += " AND status_hutang = :status_hutang"

            total_hutang = conn.execute(text(total_query), params).scalar()

            return {
                "data": list_hutang,
                "total_hutang": total_hutang
            }
    except SQLAlchemyError as e:
        print(f"[ERROR] get_hutang_by_karyawan: {e}")
        return None
    
def create_pembayaran_hutang_by_karyawan(id_karyawan, nominal, metode, keterangan, id_hutang=None):
    engine = get_connection()
    try:
        with engine.begin() as conn:
            if id_hutang:
                # Validasi hutang spesifik
                query = text("""
                    SELECT id_hutang, nominal, (
                        SELECT COALESCE(SUM(nominal), 0)
                        FROM pembayaran_hutang
                        WHERE pembayaran_hutang.id_hutang = hutang.id_hutang AND status = 1
                    ) as sudah_dibayar
                    FROM hutang
                    WHERE id_hutang = :id_hutang AND id_karyawan = :id_karyawan AND status = 1
                """)
                hutang_rows = conn.execute(query, {"id_karyawan": id_karyawan, "id_hutang": id_hutang}).fetchall()
            else:
                # Ambil semua hutang aktif milik karyawan
                query = text("""
                    SELECT id_hutang, nominal, (
                        SELECT COALESCE(SUM(nominal), 0)
                        FROM pembayaran_hutang
                        WHERE pembayaran_hutang.id_hutang = hutang.id_hutang AND status = 1
                    ) as sudah_dibayar
                    FROM hutang
                    WHERE id_karyawan = :id_karyawan AND status = 1
                    ORDER BY created_at ASC
                """)
                hutang_rows = conn.execute(query, {"id_karyawan": id_karyawan}).fetchall()

            if not hutang_rows:
                return {"message": "Karyawan ini tidak memiliki hutang aktif."}, 400

            sisa_nominal = nominal
            pembayaran_data = []

            for row in hutang_rows:
                id_hutang = row.id_hutang
                total_hutang = row.nominal
                sudah_dibayar = row.sudah_dibayar
                sisa_hutang = total_hutang - sudah_dibayar

                if sisa_nominal <= 0:
                    break

                bayar = min(sisa_nominal, sisa_hutang)

                if bayar > 0:
                    pembayaran_data.append({
                        "id_hutang": id_hutang,
                        "nominal": bayar,
                        "metode": metode,
                        "keterangan": keterangan,
                        "total_hutang": total_hutang,
                        "sudah_dibayar": sudah_dibayar + bayar
                    })
                    sisa_nominal -= bayar

            if not pembayaran_data:
                return {"message": "Tidak ada hutang yang perlu dibayar."}, 400

            for item in pembayaran_data:
                # Insert pembayaran
                insert_query = text("""
                    INSERT INTO pembayaran_hutang (
                        id_hutang, nominal, metode, keterangan, tanggal, status, created_at, updated_at
                    )
                    VALUES (
                        :id_hutang, :nominal, :metode, :keterangan, :tanggal, 1, :timestamp_wita, :timestamp_wita
                    )
                """)
                params = {
                    "id_hutang": item["id_hutang"],
                    "nominal": item["nominal"],
                    "metode": item["metode"],
                    "keterangan": item["keterangan"],
                    "tanggal": get_wita().date(),
                    "timestamp_wita": get_wita()
                }
                conn.execute(insert_query, params)

                # Cek dan update status_hutang ke 'lunas' jika sudah lunas
                if item["sudah_dibayar"] >= item["total_hutang"]:
                    update_status_query = text("""
                        UPDATE hutang
                        SET status_hutang = 'lunas', updated_at = :timestamp_wita
                        WHERE id_hutang = :id_hutang
                    """)
                    conn.execute(update_status_query, {
                        "id_hutang": item["id_hutang"],
                        "timestamp_wita": get_wita()
                    })

            return {"message": f"Pembayaran berhasil dicatat sebanyak {nominal - sisa_nominal}."}, 200
    except Exception as e:
        return {"message": str(e)}, 500
