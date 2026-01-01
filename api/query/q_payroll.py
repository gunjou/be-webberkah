from sqlalchemy.sql import text

from ..utils.config import get_connection
from ..utils.helpers import clean_decimal, safe_num
from ..utils.get_hari_kerja import get_hari_kerja_efektif_bulanan
from .q_potongan import hitung_potongan_harian, hitung_potongan_bulanan


def preview_payroll_final(id_karyawan, bulan, tahun):
    engine = get_connection()
    hari_kerja = get_hari_kerja_efektif_bulanan(tahun, bulan)
    jumlah_hari_kerja = len(hari_kerja)

    try:
        with engine.connect() as conn:

            # =========================================
            # 1️⃣ Ambil data karyawan
            # =========================================
            karyawan = conn.execute(text("""
                SELECT id_karyawan, nama
                FROM karyawan
                WHERE id_karyawan = :id_karyawan
                  AND status = 1
            """), {"id_karyawan": id_karyawan}).mappings().first()

            if not karyawan:
                return None

            # =========================================
            # 2️⃣ Tentukan jenis pegawai & master gaji
            # =========================================
            master_harian = conn.execute(text("""
                SELECT gaji_harian, tunjangan_makan_harian, tunjangan_transport_harian
                FROM master_gaji_harian
                WHERE id_karyawan = :id_karyawan AND status = 1
            """), {"id_karyawan": id_karyawan}).mappings().first()

            if master_harian:
                jenis_pegawai = "harian"
                gaji_pokok = master_harian["gaji_harian"] * jumlah_hari_kerja
                tunjangan_makan = master_harian["tunjangan_makan_harian"] * jumlah_hari_kerja
                tunjangan_transport = master_harian["tunjangan_transport_harian"] * jumlah_hari_kerja
                tunjangan_jabatan = 0
            else:
                master = conn.execute(text("""
                    SELECT
                        gaji_pokok,
                        tunjangan_jabatan,
                        tunjangan_makan,
                        tunjangan_transport,
                        jenis_penggajian
                    FROM master_gaji_karyawan
                    WHERE id_karyawan = :id_karyawan AND status = 1
                """), {"id_karyawan": id_karyawan}).mappings().first()

                if not master:
                    return None

                jenis_pegawai = master["jenis_penggajian"]
                gaji_pokok = master["gaji_pokok"]
                tunjangan_jabatan = master["tunjangan_jabatan"]
                tunjangan_makan = master["tunjangan_makan"]
                tunjangan_transport = master["tunjangan_transport"]

            total_gaji_kotor = (
                gaji_pokok +
                tunjangan_jabatan +
                tunjangan_makan +
                tunjangan_transport
            )

            # =========================================
            # 3️⃣ Potongan harian
            # =========================================
            ringkasan_potongan = {
                "gaji_pokok": 0.0,
                "tunjangan_makan": 0.0,
                "tunjangan_transport": 0.0,
                "tunjangan_jabatan": 0.0
            }
            
            harian = hitung_potongan_harian(id_karyawan, bulan, tahun)
            for hari in harian["data"]:
                for p in hari["potongan"]:
                    target = p.get("target")
                    nominal = float(p.get("nominal", 0))

                    if target == "gaji_harian":
                        ringkasan_potongan["gaji_pokok"] += nominal
                    elif target in ringkasan_potongan:
                        ringkasan_potongan[target] += nominal

            # =========================================
            # 4️⃣ Potongan bulanan
            # =========================================
            bulanan = hitung_potongan_bulanan(
                id_karyawan=id_karyawan,
                bulan=bulan,
                tahun=tahun,
                jenis_pegawai=harian["jenis_pegawai"],
                total_alpha=harian["total_alpha"],
                total_izin=harian["total_izin"],
                total_sakit=harian["total_sakit"],
                potongan_makan_harian=harian["ringkasan_potongan"]["tunjangan_makan"]
            )

            total_potongan = (
                harian["total_potongan"] +
                bulanan["nominal"]
            )
            
            if bulanan and bulanan.get("nominal", 0) > 0:
                target = bulanan.get("target")
                if target in ringkasan_potongan:
                    ringkasan_potongan[target] += float(bulanan["nominal"])

            ringkasan_potongan["total"] = sum(ringkasan_potongan.values())
            gaji_bersih = float(total_gaji_kotor) - total_potongan

            return clean_decimal( {
                "id_karyawan": id_karyawan,
                "nama_karyawan": karyawan["nama"],
                "jenis_pegawai": jenis_pegawai,
                "bulan": bulan,
                "tahun": tahun,

                "komponen_gaji": {
                    "gaji_pokok": round(gaji_pokok, 2),
                    "tunjangan_jabatan": round(tunjangan_jabatan, 2),
                    "tunjangan_makan": round(tunjangan_makan, 2),
                    "tunjangan_transport": round(tunjangan_transport, 2),
                    "total_gaji_kotor": round(total_gaji_kotor, 2)
                },

                "potongan": {
                    "harian": {
                        "total": harian["total_potongan"],
                        "detail": harian["data"]
                    },
                    "bulanan": bulanan,
                    "ringkasan": ringkasan_potongan,
                    "total_potongan": round(total_potongan, 2)
                },

                "gaji_bersih": round(gaji_bersih, 2)
            })

    except Exception as e:
        print("ERROR preview_payroll_final:", e)
        return None


def generate_payroll_masal(bulan, tahun):
    engine = get_connection()

    try:
        with engine.begin() as conn:  # 🔒 TRANSACTION

            # ===============================
            # 1️⃣ Ambil semua karyawan aktif
            # ===============================
            karyawans = conn.execute(text("""
                SELECT id_karyawan
                FROM karyawan
                WHERE status = 1
                ORDER BY id_karyawan
            """)).mappings().all()

            berhasil = 0
            gagal = []

            # ===============================
            # 2️⃣ Loop & generate payroll
            # ===============================
            for k in karyawans:
                id_karyawan = k["id_karyawan"]

                hasil = preview_payroll_final(
                    id_karyawan=id_karyawan,
                    bulan=bulan,
                    tahun=tahun
                )

                if not hasil:
                    gagal.append(id_karyawan)
                    continue
                
                harian = hitung_potongan_harian(id_karyawan, bulan, tahun)

                total_alpha = harian["total_alpha"]
                total_izin = harian["total_izin"]
                total_sakit = harian["total_sakit"]
                total_menit_terlambat = harian["total_menit_terlambat"]

                keterangan_parts = []
                if total_alpha > 0:
                    keterangan_parts.append(f"Alpha {total_alpha}x")
                if total_izin > 0:
                    keterangan_parts.append(f"Izin {total_izin}x")
                if total_sakit > 0:
                    keterangan_parts.append(f"Sakit {total_sakit}x")
                if total_menit_terlambat > 0:
                    keterangan_parts.append(f"Telat {total_menit_terlambat} menit")

                keterangan = ", ".join(keterangan_parts) if keterangan_parts else "-"

                # ===============================
                # 3️⃣ UPSERT ke penggajian
                # ===============================
                penggajian = conn.execute(text("""
                INSERT INTO penggajian (
                    id_karyawan, bulan, tahun,
                    gaji_kotor, total_potongan, gaji_bersih,
                    total_alpha, total_izin, total_sakit, total_menit_terlambat,
                    keterangan,
                    status_penggajian, generated_at
                ) VALUES (
                    :id_karyawan,
                    :bulan,
                    :tahun,
                    :gaji_kotor,
                    :total_potongan,
                    :gaji_bersih,
                    :total_alpha,
                    :total_izin,
                    :total_sakit,
                    :total_menit_terlambat,
                    :keterangan,
                    'draft',
                    NOW()
                )
                ON CONFLICT (id_karyawan, bulan, tahun)
                DO UPDATE SET
                    gaji_kotor = EXCLUDED.gaji_kotor,
                    total_potongan = EXCLUDED.total_potongan,
                    gaji_bersih = EXCLUDED.gaji_bersih,
                    total_alpha = EXCLUDED.total_alpha,
                    total_izin = EXCLUDED.total_izin,
                    total_sakit = EXCLUDED.total_sakit,
                    total_menit_terlambat = EXCLUDED.total_menit_terlambat,
                    keterangan = EXCLUDED.keterangan,
                    generated_at = NOW()
                RETURNING id_penggajian
            """), {
                "id_karyawan": id_karyawan,
                "bulan": bulan,
                "tahun": tahun,
                "gaji_kotor": hasil["komponen_gaji"]["total_gaji_kotor"],
                "total_potongan": hasil["potongan"]["total_potongan"],
                "gaji_bersih": hasil["gaji_bersih"],
                "total_alpha": total_alpha,
                "total_izin": total_izin,
                "total_sakit": total_sakit,
                "total_menit_terlambat": total_menit_terlambat,
                "keterangan": keterangan
            }).mappings().first()

                id_penggajian = penggajian["id_penggajian"]

                # ===============================
                # 4️⃣ Hapus detail lama
                # ===============================
                conn.execute(text("""
                    DELETE FROM penggajian_detail
                    WHERE id_penggajian = :id_penggajian
                """), {"id_penggajian": id_penggajian})

                # ===============================
                # 5️⃣ Simpan detail gaji
                # ===============================
                komponen = hasil["komponen_gaji"]
                for key, nilai in komponen.items():
                    if key == "total_gaji_kotor":
                        continue
                    conn.execute(text("""
                        INSERT INTO penggajian_detail
                        (id_penggajian, kategori, nilai)
                        VALUES (:id_penggajian, :kategori, :nilai)
                    """), {
                        "id_penggajian": id_penggajian,
                        "kategori": key,
                        "nilai": nilai
                    })

                # ===============================
                # 6️⃣ Simpan ringkasan potongan
                # ===============================
                ringkasan = hasil["potongan"]["ringkasan"]
                for key, nilai in ringkasan.items():
                    if key == "total":
                        continue
                    if nilai > 0:
                        conn.execute(text("""
                            INSERT INTO penggajian_detail
                            (id_penggajian, kategori, nilai)
                            VALUES (:id_penggajian, :kategori, :nilai)
                        """), {
                            "id_penggajian": id_penggajian,
                            "kategori": f"potongan_{key}",
                            "nilai": nilai
                        })

                # ===============================
                # 7️⃣ Log generate
                # ===============================
                conn.execute(text("""
                    INSERT INTO penggajian_log
                    (id_penggajian, action)
                    VALUES (:id_penggajian, 'generate')
                """), {"id_penggajian": id_penggajian})

                berhasil += 1

            # ===============================
            # 8️⃣ Return summary
            # ===============================
            return {
                "bulan": bulan,
                "tahun": tahun,
                "total_karyawan": len(karyawans),
                "berhasil": berhasil,
                "gagal": gagal
            }

    except Exception as e:
        print("ERROR generate_payroll_masal:", e)
        return None
    
    
def get_payroll_all(bulan, tahun):
    engine = get_connection()

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                p.id_penggajian,
                p.id_karyawan,
                k.nama,
                COALESCE(mgk.jenis_penggajian, 'harian') AS jenis_pegawai,

                p.gaji_kotor,
                p.total_potongan,
                p.gaji_bersih,

                p.total_alpha,
                p.total_izin,
                p.total_sakit,
                p.total_menit_terlambat,
                p.keterangan,

                p.status_penggajian,
                p.generated_at
            FROM penggajian p
            JOIN karyawan k ON p.id_karyawan = k.id_karyawan
            LEFT JOIN master_gaji_karyawan mgk
                ON k.id_karyawan = mgk.id_karyawan AND mgk.status = 1
            WHERE
                p.bulan = :bulan
                AND p.tahun = :tahun
                AND p.status = 1
            ORDER BY k.nama
        """), {
            "bulan": bulan,
            "tahun": tahun
        }).mappings().all()

    total_gaji_kotor = 0.0
    total_potongan = 0.0
    total_gaji_bersih = 0.0
    data = []

    for r in rows:
        total_gaji_kotor += float(r["gaji_kotor"])
        total_potongan += float(r["total_potongan"])
        total_gaji_bersih += float(r["gaji_bersih"])

        data.append({
            "id_penggajian": r["id_penggajian"],
            "id_karyawan": r["id_karyawan"],
            "nama": r["nama"],
            "jenis_pegawai": r["jenis_pegawai"],

            "gaji_kotor": round(r["gaji_kotor"], 2),
            "total_potongan": round(r["total_potongan"], 2),
            "gaji_bersih": round(r["gaji_bersih"], 2),

            "total_alpha": r["total_alpha"],
            "total_izin": r["total_izin"],
            "total_sakit": r["total_sakit"],
            "total_menit_terlambat": r["total_menit_terlambat"],
            "keterangan": r["keterangan"],

            "status_penggajian": r["status_penggajian"],
            "generated_at": r["generated_at"].isoformat(),
            "has_detail": True
        })

    return clean_decimal({
        "bulan": bulan,
        "tahun": tahun,
        "jumlah_karyawan": len(data),
        "total_gaji_kotor": round(total_gaji_kotor, 2),
        "total_potongan": round(total_potongan, 2),
        "total_gaji_bersih": round(total_gaji_bersih, 2),
        "data": data
    })


def get_payroll_detail(id_penggajian):
    engine = get_connection()

    with engine.connect() as conn:
        header = conn.execute(text("""
            SELECT
                p.id_penggajian,
                p.id_karyawan,
                k.nama,
                p.bulan,
                p.tahun,
                p.gaji_kotor,
                p.total_potongan,
                p.gaji_bersih,
                p.total_alpha,
                p.total_izin,
                p.total_sakit,
                p.total_menit_terlambat,
                p.keterangan,
                p.status_penggajian,
                p.generated_at
            FROM penggajian p
            JOIN karyawan k ON p.id_karyawan = k.id_karyawan
            WHERE p.id_penggajian = :id_penggajian
              AND p.status = 1
        """), {"id_penggajian": id_penggajian}).mappings().first()

        if not header:
            return None

        details = conn.execute(text("""
            SELECT kategori, nilai
            FROM penggajian_detail
            WHERE id_penggajian = :id_penggajian
        """), {"id_penggajian": id_penggajian}).mappings().all()

    komponen_gaji = {}
    potongan = []

    for d in details:
        if d["kategori"].startswith("potongan_"):
            potongan.append({
                "kategori": d["kategori"].replace("potongan_", ""),
                "nilai": float(d["nilai"])
            })
        else:
            komponen_gaji[d["kategori"]] = float(d["nilai"])

    return {
        "id_penggajian": header["id_penggajian"],
        "id_karyawan": header["id_karyawan"],
        "nama_karyawan": header["nama"],
        "bulan": header["bulan"],
        "tahun": header["tahun"],
        "status_penggajian": header["status_penggajian"],
        "generated_at": header["generated_at"].isoformat(),

        "rekap_disiplin": {
            "total_alpha": header["total_alpha"],
            "total_izin": header["total_izin"],
            "total_sakit": header["total_sakit"],
            "total_menit_terlambat": header["total_menit_terlambat"],
            "keterangan": header["keterangan"]
        },

        "komponen_gaji": komponen_gaji,

        "potongan": {
            "total": float(header["total_potongan"]),
            "detail": potongan
        },

        "gaji_bersih": float(header["gaji_bersih"])
    }

