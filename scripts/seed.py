import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from app import db  # noqa: E402
from app.scraper import _sample_weekly_menu  # noqa: E402
from app.utils import menu_hash  # noqa: E402

DATA_FILE = ROOT / "data" / "weekly_menu.json"

_SAMPLE_ANALYSIS = {
    "summary": "오늘도 든든한 한 끼!",
    "calories": 720,
    "tags": ["한식", "균형잡힌", "든든한"],
    "recommendation": "점심 든든하게 드세요.",
}


def _load_days():
    # 실제 수집 결과가 있으면 그걸로, 없으면 샘플
    if DATA_FILE.exists():
        days = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        print(f"[seed] weekly_menu.json 에서 {len(days)}일치 로드")
        return days
    print("[seed] data 파일이 없어 샘플로 생성")
    return [
        {**day, "menu_hash": menu_hash(day["menus"]),
         "analysis": dict(_SAMPLE_ANALYSIS), "image_url": "/static/images/default.png"}
        for day in _sample_weekly_menu()
    ]


def main():
    load_dotenv()
    db.init_schema()
    for day in _load_days():
        db.upsert_menu(day["date"], day["menu_hash"], day["menus"], day["analysis"], day["image_url"])
        db.save_cached_image(day["menu_hash"], day["image_url"])
        print(f"[seed] {day['date']}  {len(day['menus'])}개 메뉴")

    stats = db.get_stats()
    print(f"\n저장 메뉴 {stats['total_menus']} / 이미지 캐시 {stats['cached_images']}")
    print("TOP5:", ", ".join(f"{r['dish']}({r['count']})" for r in stats["top_dishes"]))


if __name__ == "__main__":
    main()
