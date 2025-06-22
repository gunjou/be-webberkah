from datetime import datetime, time, date
import pytz

def hitung_waktu_kerja(jam_masuk, jam_keluar):
    if jam_keluar is None:
        return 0
    total_masuk = jam_masuk.hour * 60 + jam_masuk.minute
    total_keluar = jam_keluar.hour * 60 + jam_keluar.minute
    return max(total_keluar - total_masuk, 0)

def hitung_keterlambatan(jam_masuk):
    wita = pytz.timezone("Asia/Makassar")
    if jam_masuk.tzinfo is not None:
        jam_masuk = jam_masuk.astimezone(wita)
    # Buang detik dan mikrodetik
    jam_masuk = jam_masuk.replace(second=0, microsecond=0)
    jam_masuk_batas = time(8, 0)
    if jam_masuk <= jam_masuk_batas:
        return None  # Tidak terlambat
    # Hitung keterlambatan dalam menit
    return (jam_masuk.hour * 60 + jam_masuk.minute) - (jam_masuk_batas.hour * 60 + jam_masuk_batas.minute)

def hitung_jam_kurang(jam_keluar):
    waktu_ideal = time(17, 0)
    if isinstance(jam_keluar, str):
        try:
            jam_keluar_obj = datetime.strptime(jam_keluar, "%H:%M:%S").time()
        except ValueError:
            return None
    elif isinstance(jam_keluar, time):
        # Buang detik dan mikrodetik jika bertipe time
        jam_keluar_obj = jam_keluar.replace(second=0, microsecond=0)
    else:
        return None

    if jam_keluar_obj < waktu_ideal:
        delta = datetime.combine(date.today(), waktu_ideal) - datetime.combine(date.today(), jam_keluar_obj)
        return int(delta.total_seconds() // 60)
    return None
