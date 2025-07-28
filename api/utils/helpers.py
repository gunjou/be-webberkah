from datetime import datetime, time, date, timedelta
from decimal import Decimal
from PIL import Image, UnidentifiedImageError
import pytz

def compress_image(file, save_path, max_width=1280, quality=80):
    """Resize dan kompres gambar"""
    img = Image.open(file)
    img = img.convert('RGB')
    
    # Resize jika terlalu besar
    if img.width > max_width:
        ratio = max_width / float(img.width)
        height = int((float(img.height) * float(ratio)))
        img = img.resize((max_width, height), Image.ANTIALIAS)

    # Simpan ke file
    img.save(save_path, optimize=True, quality=quality)

def is_image(file):
    """Cek apakah file adalah gambar"""
    try:
        Image.open(file).verify()
        file.seek(0)  # reset pointer karena verify() menggeser
        return True
    except (UnidentifiedImageError, IOError):
        file.seek(0)
        return False

def hitung_waktu_kerja(jam_masuk, jam_keluar):
    if jam_keluar is None:
        return 0
    total_masuk = jam_masuk.hour * 60 + jam_masuk.minute
    total_keluar = jam_keluar.hour * 60 + jam_keluar.minute
    return max(total_keluar - total_masuk, 0)

def hitung_keterlambatan(jam_masuk):
    jam_batas = time(8, 0)
    
    if isinstance(jam_masuk, str):
        try:
            jam_masuk_obj = datetime.strptime(jam_masuk, "%H:%M:%S").time()
        except ValueError:
            try:
                jam_masuk_obj = datetime.strptime(jam_masuk, "%H:%M").time()
            except ValueError:
                return None
    elif isinstance(jam_masuk, datetime):
        # Konversi ke WITA jika ada tzinfo
        if jam_masuk.tzinfo is not None:
            wita = pytz.timezone("Asia/Makassar")
            jam_masuk = jam_masuk.astimezone(wita)
        jam_masuk_obj = jam_masuk.time().replace(second=0, microsecond=0)
    elif isinstance(jam_masuk, time):
        jam_masuk_obj = jam_masuk.replace(second=0, microsecond=0)
    else:
        return None

    # Bandingkan dengan jam batas
    if jam_masuk_obj <= jam_batas:
        return None  # Tidak terlambat
    delta = datetime.combine(date.today(), jam_masuk_obj) - datetime.combine(date.today(), jam_batas)
    return int(delta.total_seconds() // 60)  # Durasi keterlambatan dalam menit

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

def format_jam_menit(menit):
    if menit is None:
        return ""
    jam = menit // 60
    menit_sisa = menit % 60
    parts = []
    if jam > 0:
        parts.append(f"{jam} jam")
    if menit_sisa > 0:
        parts.append(f"{menit_sisa} menit")
    return " ".join(parts) if parts else "0 menit"

def time_to_str(value):
    return value.strftime('%H:%M:%S') if isinstance(value, time) else None

def daterange(start_date, end_date):
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(days=n)

def decimal_to_float(row):
    return {
        key: float(value) if isinstance(value, Decimal) else value
        for key, value in row.items()
    }

def serialize_time(obj):
    """Mengubah objek time ke string, dan juga mengubah float Decimal."""
    if isinstance(obj, time):
        return obj.strftime("%H:%M:%S")
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj