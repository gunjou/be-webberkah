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
            harian = hitung_potongan_harian(id_karyawan, bulan, tahun)

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
                total_sakit=harian["total_sakit"]
            )

            total_potongan = (
                harian["total_potongan"] +
                bulanan["nominal"]
            )

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
                    "total_potongan": round(total_potongan, 2)
                },

                "gaji_bersih": round(gaji_bersih, 2)
            })

    except Exception as e:
        print("ERROR preview_payroll_final:", e)
        return None
    
    
def get_rekap_absensi_masal(bulan, tahun):
    engine = get_connection()

    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT
                a.id_karyawan,
                COALESCE(SUM(a.jam_terlambat), 0) AS total_menit_terlambat,
                COUNT(*) FILTER (WHERE s.nama_status = 'Izin') AS total_izin,
                COUNT(*) FILTER (WHERE s.nama_status = 'Sakit') AS total_sakit,
                COUNT(*) FILTER (WHERE s.nama_status = 'Hadir') AS total_hadir
            FROM absensi a
            JOIN statuspresensi s
                ON a.id_status = s.id_status
            WHERE
                EXTRACT(MONTH FROM a.tanggal) = :bulan
                AND EXTRACT(YEAR FROM a.tanggal) = :tahun
                AND a.status = 1
                -- ❌ EXCLUDE HARI MINGGU
                AND EXTRACT(DOW FROM a.tanggal) != 0
                -- ❌ EXCLUDE LIBUR NASIONAL
                AND NOT EXISTS (
                    SELECT 1
                    FROM liburnasional l
                    WHERE l.tanggal = a.tanggal
                      AND l.status = 1
                )
            GROUP BY a.id_karyawan
        """), {
            "bulan": bulan,
            "tahun": tahun
        }).mappings().all()

        
def get_master_gaji_masal():
    engine = get_connection()

    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT
                k.id_karyawan,
                k.nama,

                mgk.gaji_pokok,
                mgk.tunjangan_jabatan,
                mgk.tunjangan_makan,
                mgk.tunjangan_transport,
                mgk.jenis_penggajian,

                mgh.gaji_harian,
                mgh.tunjangan_makan_harian,
                mgh.tunjangan_transport_harian
            FROM karyawan k
            LEFT JOIN master_gaji_karyawan mgk
                ON k.id_karyawan = mgk.id_karyawan AND mgk.status = 1
            LEFT JOIN master_gaji_harian mgh
                ON k.id_karyawan = mgh.id_karyawan AND mgh.status = 1
            WHERE k.status = 1
            ORDER BY k.nama
        """)).mappings().all()


def preview_payroll_masal_fast(bulan, tahun):
    hari_kerja = get_hari_kerja_efektif_bulanan(tahun, bulan)
    jumlah_hari_kerja = len(hari_kerja)

    rekap_absensi = {
        r["id_karyawan"]: r for r in get_rekap_absensi_masal(bulan, tahun)
    }

    masters = get_master_gaji_masal()

    data = []
    total_gaji_kotor = 0.0
    total_potongan = 0.0
    total_gaji_bersih = 0.0

    for m in masters:
        id_karyawan = m["id_karyawan"]
        rekap = rekap_absensi.get(id_karyawan, {
            "total_menit_terlambat": 0,
            "total_izin": 0,
            "total_sakit": 0,
            "total_hadir": 0
        })

        # =============================
        # Tentukan jenis pegawai
        # =============================
        if m["gaji_harian"]:
            jenis = "harian"
            gaji_pokok = safe_num(m["gaji_harian"]) * jumlah_hari_kerja
            tunjangan_makan = safe_num(m["tunjangan_makan_harian"]) * jumlah_hari_kerja
            tunjangan_transport = safe_num(m["tunjangan_transport_harian"]) * jumlah_hari_kerja
            tunjangan_jabatan = 0
        else:
            jenis = m["jenis_penggajian"]
            gaji_pokok = safe_num(m["gaji_pokok"])
            tunjangan_makan = safe_num(m["tunjangan_makan"])
            tunjangan_transport = safe_num(m["tunjangan_transport"])
            tunjangan_jabatan = safe_num(m["tunjangan_jabatan"])

        gaji_kotor = (
            gaji_pokok +
            tunjangan_jabatan +
            tunjangan_makan +
            tunjangan_transport
        )

        # =============================
        # Potongan BULANAN (estimasi)
        # =============================
        total_alpha = jumlah_hari_kerja - rekap["total_hadir"] - rekap["total_izin"] - rekap["total_sakit"]
        total_izin_sakit = rekap["total_izin"] + rekap["total_sakit"]

        potongan_bulanan = 0.0
        catatan_parts = []

        if total_alpha > 0:
            persen = 25 if total_alpha == 1 else 50 if total_alpha == 2 else 100
            potongan_bulanan = tunjangan_makan * persen / 100
            catatan_parts.append(f"Alpha {total_alpha}x")
        if total_izin_sakit > 0:
            persen = 10 if total_izin_sakit == 1 else 25 if total_izin_sakit == 2 else 50
            potongan_bulanan = tunjangan_makan * persen / 100
            catatan_parts.append(f"Izin/Sakit {total_izin_sakit}x")
        if rekap["total_menit_terlambat"] > 0:
            catatan_parts.append(f"Terlambat {rekap['total_menit_terlambat']} menit")
            
        catatan = ", ".join(catatan_parts) if catatan_parts else "-"

        # =============================
        # POTONGAN HARIAN (ESTIMASI)
        # =============================
        hari_absen = rekap["total_izin"] + rekap["total_sakit"] + total_alpha

        potongan_harian = 0.0

        if hari_absen > 0:
            potongan_harian += (tunjangan_makan / jumlah_hari_kerja) * hari_absen
            potongan_harian += (tunjangan_transport / jumlah_hari_kerja) * hari_absen

        # estimasi keterlambatan
        if rekap["total_menit_terlambat"] > 0:
            potongan_telat = (
                rekap["total_menit_terlambat"] / (jumlah_hari_kerja * 60)
            ) * tunjangan_transport
            potongan_harian += potongan_telat
            
        total_potongan = potongan_bulanan + potongan_harian
        gaji_bersih = gaji_kotor - total_potongan

        data.append({
            "id_karyawan": id_karyawan,
            "nama": m["nama"],
            "jenis_pegawai": jenis,
            "gaji_kotor": round(gaji_kotor, 2),
            "total_potongan_estimasi": round(total_potongan, 2),
            "gaji_bersih": round(gaji_bersih, 2),
            "rekap_disiplin": catatan,
            "has_detail": True
        })

        total_gaji_kotor += gaji_kotor
        total_potongan = total_potongan
        gaji_bersih = gaji_kotor - total_potongan

    return {
        "bulan": bulan,
        "tahun": tahun,
        "jumlah_karyawan": len(data),
        "total_gaji_kotor": round(total_gaji_kotor, 2),
        "total_potongan_estimasi": round(total_potongan, 2),
        "total_gaji_bersih": round(total_gaji_bersih, 2),
        "data": data
    }