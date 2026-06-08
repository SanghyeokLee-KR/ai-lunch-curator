import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from .ai_service import analyze_menu
from .image_service import generate_image
from .scraper import fetch_weekly_menu
from .teams import send_today_card
from .utils import korean_date, menu_hash

logger = logging.getLogger("lunch")

# DB 붙기 전까지 collect -> notify 사이를 이 파일로 주고받는다
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "weekly_menu.json"


def cmd_collect():
    week = fetch_weekly_menu(os.getenv("MENU_SOURCE_URL"))
    enriched = []
    for day in week:
        menus = day["menus"]
        digest = menu_hash(menus)
        logger.info("- %s  %s", korean_date(day["date"]), ", ".join(menus))
        analysis = analyze_menu(menus)
        logger.info("   분석 -> %s", json.dumps(analysis, ensure_ascii=False))
        image_url = generate_image(menus, digest)
        logger.info("   이미지 -> %s", image_url)
        enriched.append({**day, "menu_hash": digest, "analysis": analysis, "image_url": image_url})

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("OK %d일치 저장 -> %s", len(enriched), DATA_FILE)


def cmd_notify():
    if not DATA_FILE.exists():
        logger.error("%s 없음. collect 먼저 돌려라.", DATA_FILE)
        return

    week = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    menu = next((d for d in week if d["date"] == today), None)
    if menu is None:
        menu = week[0] if week else None  # 주말 등 오늘 게 없으면 첫 날로
        if menu is None:
            logger.error("발송할 메뉴가 없다.")
            return
        logger.warning("오늘(%s) 메뉴가 없어 %s 로 대체", today, menu["date"])

    base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
    logger.info("발송 — %s", korean_date(menu["date"]))
    ok = send_today_card(menu, base_url)
    logger.info("발송 결과 — %s", "성공" if ok else "실패")


def _enable_utf8_output():
    # 윈도우 콘솔에서 한글 안 깨지게
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    _enable_utf8_output()
    load_dotenv(override=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
    for noisy in ("httpx", "httpcore", "openai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(prog="run_bot")
    parser.add_argument("mode", choices=["collect", "notify"])
    args = parser.parse_args(argv)
    (cmd_collect if args.mode == "collect" else cmd_notify)()


if __name__ == "__main__":
    main()
