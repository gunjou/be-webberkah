from sqlalchemy.sql import text

from ..utils.config import get_connection
from ..utils.get_hari_kerja import get_hari_kerja_efektif_bulanan


def hitung_potongan_harian(id_karyawan, bulan, tahun):
    engine = get_connection()
    hari_kerja = get_hari_kerja_efektif_bulanan(tahun, bulan)
    try:
        with engine.connect() as conn:

            # =====================================================
            # 1️⃣ Tentukan jenis pegawai & ambil master gaji
            # =====================================================

            # Cek pegawai harian
            master_harian = conn.execute(text("""
                SELECT
                    gaji_harian,
                    tunjangan_transport_harian,
                    tunjangan_makan_harian
                FROM master_gaji_harian
                WHERE id_karyawan = :id_karyawan
                  AND status = 1
            """), {"id_karyawan": id_karyawan}).mappings().first()

            if master_harian:
                jenis_pegawai = "harian"
                gaji_harian = float(master_harian["gaji_harian"])
                base_makan = float(master_harian["tunjangan_makan_harian"])
                base_transport = float(master_harian["tunjangan_transport_harian"])
            else:
                # Pegawai tetap / magang
                master_bulanan = conn.execute(text("""
                    SELECT
                        tunjangan_transport,
                        tunjangan_makan,
                        jenis_penggajian
                    FROM master_gaji_karyawan
                    WHERE id_karyawan = :id_karyawan
                      AND status = 1
                """), {"id_karyawan": id_karyawan}).mappings().first()

                if not master_bulanan:
                    raise Exception("Master gaji tidak ditemukan")

                jenis_pegawai = master_bulanan["jenis_penggajian"]  # tetap / magang
                base_makan = master_bulanan["tunjangan_makan"]
                base_transport = master_bulanan["tunjangan_transport"]

            # =====================================================
            # 2️⃣ Ambil absensi bulanan
            # =====================================================

            absensi = conn.execute(text("""
                SELECT
                    a.tanggal,
                    a.jam_terlambat,
                    a.id_status,
                    s.nama_status as jenis_izin
                FROM absensi a
                INNER JOIN statuspresensi s on a.id_status = s.id_status
                WHERE
                    a.id_karyawan = :id_karyawan
                    AND EXTRACT(MONTH FROM a.tanggal) = :bulan
                    AND EXTRACT(YEAR FROM a.tanggal) = :tahun
                    AND a.status = 1
                ORDER BY a.tanggal
            """), {
                "id_karyawan": id_karyawan,
                "bulan": bulan,
                "tahun": tahun
            }).mappings().fetchall()

            hasil = []

            total_menit_terlambat = 0
            total_potongan = 0.0

            total_alpha = 0
            total_izin = 0
            total_sakit = 0
            
            total_potong_gaji_harian = 0.0
            total_potong_tunjangan_makan = 0.0
            total_potong_tunjangan_transport = 0.0

            # =====================================================
            # 3️⃣ Loop per hari
            # =====================================================

            for tanggal in hari_kerja:

                potongan_hari = {
                    "tanggal": tanggal.isoformat(),
                    "potongan": []
                }

                row = next((r for r in absensi if r["tanggal"] == tanggal), None)
                # if row:
                #     jenis_izin = row["jenis_izin"].lower()

                #     if jenis_izin == "izin":
                #         total_izin += 1
                #     elif jenis_izin == "sakit":
                #         total_sakit += 1

                # =========================================
                # KHUSUS PEGAWAI HARIAN:
                # IZIN / SAKIT / ALPHA = TIDAK DIBAYAR
                # =========================================

                if jenis_pegawai == "harian":

                    # Status ALPHA (tidak ada absensi)
                    if not row:
                        total_alpha += 1

                        total_potongan += gaji_harian + base_makan + base_transport

                        total_potong_gaji_harian += gaji_harian
                        total_potong_tunjangan_makan += base_makan
                        total_potong_tunjangan_transport += base_transport

                        potongan_hari["potongan"].append({
                            "jenis": "alpha",
                            "target": "gaji_harian",
                            "nominal": round(gaji_harian, 2)
                        })
                        potongan_hari["potongan"].append({
                            "jenis": "alpha",
                            "target": "tunjangan_makan",
                            "nominal": round(base_makan, 2)
                        })
                        potongan_hari["potongan"].append({
                            "jenis": "alpha",
                            "target": "tunjangan_transport",
                            "nominal": round(base_transport, 2)
                        })

                        hasil.append(potongan_hari)
                        continue  # ⛔ STOP ke hari berikutnya

                    # Status IZIN / SAKIT
                    jenis_izin = row["jenis_izin"].lower()
                    if jenis_izin in ("izin", "sakit"):
                        if jenis_izin == "izin":
                            total_izin += 1
                        else:
                            total_sakit += 1

                        total_potongan += gaji_harian + base_makan + base_transport

                        total_potong_gaji_harian += gaji_harian
                        total_potong_tunjangan_makan += base_makan
                        total_potong_tunjangan_transport += base_transport

                        potongan_hari["potongan"].append({
                            "jenis": jenis_izin,
                            "target": "gaji_harian",
                            "nominal": round(gaji_harian, 2)
                        })
                        potongan_hari["potongan"].append({
                            "jenis": jenis_izin,
                            "target": "tunjangan_makan",
                            "nominal": round(base_makan, 2)
                        })
                        potongan_hari["potongan"].append({
                            "jenis": jenis_izin,
                            "target": "tunjangan_transport",
                            "nominal": round(base_transport, 2)
                        })

                        hasil.append(potongan_hari)
                        continue  # ⛔ STOP ke hari berikutnya

                # =====================================================
                # KASUS 1: ADA ABSENSI
                # =====================================================
                if row:
                    jam_terlambat = row["jam_terlambat"]
                    jenis_izin = row["jenis_izin"].lower()

                    # ---- TERLAMBAT ----
                    if jam_terlambat and jam_terlambat > 0:
                        total_menit_terlambat += jam_terlambat

                        rule = conn.execute(text("""
                            SELECT *
                            FROM aturan_potongan_kedisiplinan
                            WHERE jenis = 'terlambat'
                            AND level_potongan = 'harian'
                            AND satuan = 'menit'
                            AND :durasi BETWEEN durasi_min AND durasi_max
                            AND berlaku_untuk IN ('all', :jenis_pegawai)
                            AND status = 1
                        """), {
                            "durasi": jam_terlambat,
                            "jenis_pegawai": jenis_pegawai
                        }).mappings().first()

                        if rule:
                            base_harian = (
                                float(base_transport) / len(hari_kerja)
                                if jenis_pegawai != "harian"
                                else float(base_transport)
                            )

                            nominal = base_harian * float(rule["potong_persen"]) / 100
                            total_potong_tunjangan_transport += round(nominal, 2)
                            total_potongan += round(nominal, 2)

                            potongan_hari["potongan"].append({
                                "jenis": "terlambat",
                                "menit_terlambat": jam_terlambat,
                                "target": "tunjangan_transport",
                                "persen": rule["potong_persen"],
                                "nominal": round(nominal, 2)
                            })

                    # ---- IZIN / SAKIT ----
                    if jenis_izin in ("izin", "sakit"):
                        rules = conn.execute(text("""
                            SELECT *
                            FROM aturan_potongan_kedisiplinan
                            WHERE jenis = :jenis
                            AND level_potongan = 'harian'
                            AND berlaku_untuk IN ('all', :jenis_pegawai)
                            AND status = 1
                        """), {
                            "jenis": jenis_izin,
                            "jenis_pegawai": jenis_pegawai
                        }).mappings().fetchall()

                        for r in rules:
                            base = base_makan if r["target_potongan"] == "tunjangan_makan" else base_transport
                            base_harian = (
                                float(base) / len(hari_kerja)
                                if jenis_pegawai != "harian"
                                else float(base)
                            )

                            nominal = base_harian * float(r["potong_persen"]) / 100
                            total_potongan += round(nominal, 2)

                            potongan_hari["potongan"].append({
                                "jenis": jenis_izin,
                                "target": r["target_potongan"],
                                "persen": r["potong_persen"],
                                "nominal": round(nominal, 2)
                            })

                # =====================================================
                # KASUS 2: TIDAK ADA ABSENSI → ALPHA HARIAN
                # =====================================================
                else:
                    total_alpha += 1
                    rules = conn.execute(text("""
                        SELECT *
                        FROM aturan_potongan_kedisiplinan
                        WHERE jenis = 'alpha'
                        AND level_potongan = 'harian'
                        AND berlaku_untuk IN ('all', :jenis_pegawai)
                        AND status = 1
                    """), {
                        "jenis_pegawai": jenis_pegawai
                    }).mappings().fetchall()

                    for r in rules:
                        base = base_makan if r["target_potongan"] == "tunjangan_makan" else base_transport
                        base_harian = (
                            float(base) / len(hari_kerja)
                            if jenis_pegawai != "harian"
                            else float(base)
                        )

                        nominal = base_harian * float(r["potong_persen"]) / 100
                        total_potongan += round(nominal, 2)

                        if r["target_potongan"] == "tunjangan_makan":
                            total_potong_tunjangan_makan += round(nominal, 2)
                        elif r["target_potongan"] == "tunjangan_transport":
                            total_potong_tunjangan_transport += round(nominal, 2)

                        potongan_hari["potongan"].append({
                            "jenis": "alpha",
                            "target": r["target_potongan"],
                            "persen": r["potong_persen"],
                            "nominal": round(nominal, 2)
                        })

                if potongan_hari["potongan"]:
                    hasil.append(potongan_hari)


            return {
                "jenis_pegawai": jenis_pegawai,
                "total_menit_terlambat": total_menit_terlambat,
                "total_alpha": total_alpha,
                "total_izin": total_izin,
                "total_sakit": total_sakit,
                "total_potongan": round(total_potongan, 2),
                "ringkasan_potongan": {
                    "gaji_harian": round(total_potong_gaji_harian, 2) if jenis_pegawai == "harian" else 0,
                    "tunjangan_makan": round(total_potong_tunjangan_makan, 2),
                    "tunjangan_transport": round(total_potong_tunjangan_transport, 2)
                },
                "data": hasil
            }

    except Exception as e:
        print("ERROR hitung_potongan_harian:", e)
        return None


def hitung_potongan_bulanan(
    id_karyawan,
    bulan,
    tahun,
    jenis_pegawai,
    total_alpha,
    total_izin,
    total_sakit,
    potongan_makan_harian
):
    engine = get_connection()
    hari_kerja = get_hari_kerja_efektif_bulanan(tahun, bulan)
    jumlah_hari_kerja = len(hari_kerja)

    try:
        with engine.connect() as conn:

            # =========================================
            # 1️⃣ Ambil tunjangan makan BULANAN
            # =========================================
            if jenis_pegawai == "harian":
                master = conn.execute(text("""
                    SELECT tunjangan_makan_harian
                    FROM master_gaji_harian
                    WHERE id_karyawan = :id_karyawan
                      AND status = 1
                """), {"id_karyawan": id_karyawan}).mappings().first()

                if not master:
                    return None

                tunjangan_makan_bulanan = (
                    float(master["tunjangan_makan_harian"]) * jumlah_hari_kerja
                )
            else:
                master = conn.execute(text("""
                    SELECT tunjangan_makan
                    FROM master_gaji_karyawan
                    WHERE id_karyawan = :id_karyawan
                      AND status = 1
                """), {"id_karyawan": id_karyawan}).mappings().first()

                if not master:
                    return None

                tunjangan_makan_bulanan = float(master["tunjangan_makan"])

            # =========================================
            # 2️⃣ Tentukan jenis & jumlah pelanggaran
            # =========================================
            total_izin_sakit = total_izin + total_sakit

            if total_alpha > 0:
                jenis_rule = "alpha"
                jumlah = total_alpha
            elif total_izin_sakit > 0:
                jenis_rule = "izin"
                jumlah = total_izin_sakit
            else:
                return {
                    "jenis": None,
                    "jumlah": 0,
                    "persen": 0,
                    "nominal": 0.0
                }

            # =========================================
            # 3️⃣ Ambil rule bulanan
            # =========================================
            rule = conn.execute(text("""
                SELECT *
                FROM aturan_potongan_kedisiplinan
                WHERE
                    jenis = :jenis
                    AND level_potongan = 'bulanan'
                    AND :jumlah BETWEEN durasi_min AND durasi_max
                    AND berlaku_untuk IN ('all', :jenis_pegawai)
                    AND status = 1
            """), {
                "jenis": jenis_rule,
                "jumlah": jumlah,
                "jenis_pegawai": jenis_pegawai
            }).mappings().first()

            if not rule:
                return {
                    "jenis": jenis_rule,
                    "jumlah": jumlah,
                    "persen": 0,
                    "nominal": 0.0
                }

            persen = float(rule["potong_persen"])
            sisa_tunjangan_makan = max(
                    tunjangan_makan_bulanan - float(potongan_makan_harian),
                    0
                )
            nominal = sisa_tunjangan_makan * persen / 100
            # ⛔ SAFETY CAP: tidak boleh melebihi sisa
            nominal = min(nominal, sisa_tunjangan_makan)

            return {
                "jenis": jenis_rule,
                "jumlah": jumlah,
                "persen": persen,
                "nominal": round(nominal, 2),
                "target": "tunjangan_makan",
                # "basis": round(sisa_tunjangan_makan, 2)
            }

    except Exception as e:
        print("ERROR hitung_potongan_bulanan:", e)
        return None