import math

def haversine_distance(lat1, lng1, lat2, lng2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

test_data = [
    {'id': '1001', 'name': '서면대찬', 'category': '한식', 'lat': 35.1654, 'lng': 129.1701},
    {'id': '1002', 'name': '돌돌이국수', 'category': '한식', 'lat': 35.1642, 'lng': 129.1715},
]

lat, lng = 35.1650, 129.1700
print(f"User location: {lat}, {lng}")
print(f"Radius: 1000m\n")

for r in test_data:
    distance = haversine_distance(lat, lng, r['lat'], r['lng'])
    print(f"{r['name']}: {distance:.2f}m")
