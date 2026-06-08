import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from app import db  # noqa: E402


def main():
    load_dotenv()
    print("=== LUNCH_MENU (최근 30일) ===")
    for m in db.get_history(30):
        print(f"{m['date']} | {m['analysis']['calories']:>4} kcal | {', '.join(m['menus'])}")

    stats = db.get_stats()
    print(f"\n저장 메뉴 수: {stats['total_menus']}   이미지 캐시: {stats['cached_images']}")
    print("자주 나온 메뉴 TOP5:")
    for r in stats["top_dishes"]:
        print(f"  {r['dish']}  x{r['count']}")


if __name__ == "__main__":
    main()
