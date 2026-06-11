import os
import json
import requests

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

API_KEY = os.environ[“MSIL_API_KEY”]

JST = timezone(timedelta(hours=9))

AREAS = [
“03”,
“01”,
“02”,
“04”,
“05”,
“06”,
“07”,
“08”,
“S01”
]

os.makedirs(“forecast”, exist_ok=True)

session = requests.Session()

def fetch_hour(area_code, hour_offset):

base_jst = datetime.now(JST).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)
target = base_jst + timedelta(hours=hour_offset)
url = "https://api.msil.go.jp/tidal-current-prediction/v3/data"
params = {
    "areaCode": area_code,
    "time": target.strftime("%Y%m%d%H%M"),
    "key": API_KEY
}
r = session.get(url, params=params, timeout=20)
if r.status_code != 200:
    return None
data = r.json()
features = data.get("features", [])
if not features:
    return None
p = features[0]["properties"]
return {
    "time": hour_offset,
    "speed": float(p.get("currentSpeedKt", 0) or 0),
    "direction": float(p.get("currentDirection", 0) or 0)
}

def build_area(area_code):

with ThreadPoolExecutor(max_workers=8) as executor:
    results = list(
        executor.map(
            lambda h: fetch_hour(area_code, h),
            range(48)
        )
    )
results = [r for r in results if r]
results.sort(key=lambda x: x["time"])
payload = {
    "status": "success",
    "generated_at": datetime.now(JST).isoformat(),
    "data": results
}
with open(
    f"forecast/{area_code}.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(payload, f, ensure_ascii=False)

for area in AREAS:
print(“Fetching”, area)
build_area(area)

with open(
“forecast/update_status.json”,
“w”,
encoding=“utf-8”
) as f:
json.dump(
{
“date”: datetime.now(JST).strftime(”%Y-%m-%d”)
},
f,
ensure_ascii=False
)
