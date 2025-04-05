from math import radians, sin, cos, sqrt, atan2


# Daftar lokasi kantor dengan nama
OFFICE_LOCATIONS = [
    {"name": "Kantor Perampuan", "lat": -8.639211414577346, "lon": 116.08763439302037},
    {"name": "Gudang GM", "lat": -8.674641, "lon": 116.086079},
    {"name": "Rumah", "lat": -8.639975671029253, "lon": 116.0940286392315},
    {"name": "PLTG Jeranjang", "lat": -8.659710078427981, "lon": 116.07416334995118}
]

RADIUS_ALLOWED = 50  # Radius dalam meter

def calculate_distance(lat1, lon1, lat2, lon2):
    """Menghitung jarak antara dua titik koordinat menggunakan Haversine Formula"""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    R = 6371000  # Radius bumi dalam meter
    return R * c