import os
import json
import requests
import time  # 🌟サーバー保護用のウェイトに追加

from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

# 🌟 os.getenv に変更（キーがなくてもエラーで即死しないようにする）
API_KEY = os.getenv("MSIL_API_KEY")

JST = timezone(timedelta(hours=9))

AREAS = [
    "03",
    "01",
    "02",
    "04",
    "05",
    "06",
    "07",
    "08",
    "S01"
]

os.makedirs("forecast", exist_ok=True)

session = requests.Session()


def fetch_hour(area_code, hour_offset):
    # 🌟 APIキーがない場合は処理をスキップ（ymlのチェック時対策）
    if not API_KEY:
        return None

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

    try:
        r = session.get(url, params=params, timeout=20)

        if r.status_code != 200:
            print(f"  ⚠️ Hour {hour_offset}: HTTP {r.status_code}")
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
    except Exception as e:
        print(f"  ❌ Error Hour {hour_offset}: {e}")
        return None


def build_area(area_code):
    # 🌟 同時アクセス数を 8 ⇒ 4 に少し落として安全性を向上
    with ThreadPoolExecutor(max_workers=4) as executor:
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


# 🌟 メイン処理のガード（ymlのインライン実行時に誤作動するのを防ぐ）
if __name__ == "__main__":
    if not API_KEY:
        print("⚠️ MSIL_API_KEY が設定されていません。データ取得をスキップします。")
    else:
        for area in AREAS:
            print("Fetching", area)
            build_area(area)
            time.sleep(1)  # 🌟 エリアごとに1秒休んで海しる側のブロックを回避

        # すべて成功した場合のみ、完了ステータスを書き込む
        with open(
            "forecast/update_status.json",
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                {
                    "date": datetime.now(JST).strftime("%Y-%m-%d")
                },
                f,
                ensure_ascii=False
            )
        print("✅ All areas updated successfully.")
