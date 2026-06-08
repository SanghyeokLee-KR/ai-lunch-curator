import logging
import re
from datetime import timedelta

import requests
from bs4 import BeautifulSoup

from .utils import this_week_monday

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def fetch_weekly_menu(source_url=None):
    """이번 주 점심 메뉴를 가져온다. 못 가져오면 샘플로."""
    if source_url:
        try:
            resp = requests.get(source_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": _USER_AGENT})
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding
            days = _parse_menu_html(resp.text)
            if days:
                logger.info("식단표 %d일치 수집", len(days))
                return days
            logger.warning("파싱 결과가 비어 샘플로 폴백")
        except Exception as exc:
            logger.warning("크롤링 실패(%s) → 샘플", exc)
    else:
        logger.warning("MENU_SOURCE_URL 없음 → 샘플")
    return _sample_weekly_menu()


def _parse_menu_html(html):
    # KOPO 표: 한 행이 하루, 점심은 중식(td 3번째)만. 날짜는 getDay2('YYYY-MM-DD ...') 안에 박혀 있다.
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.menu")
    if table is None:
        return []

    days = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 3:
            continue
        m = _DATE_RE.search(str(cells[0]))
        if not m:
            continue
        spans = [
            sp.get_text(strip=True)
            for sp in cells[2].find_all("span")
            if "kcal" not in (sp.get("class") or [])
        ]
        text = (" ".join(s for s in spans if s) or cells[2].get_text(strip=True)).replace("\xa0", " ")
        dishes = [d.strip() for d in text.split(",") if d.strip()]
        if dishes:
            days.append({"date": m.group(0), "menus": dishes})
    return days


def _sample_weekly_menu():
    monday = this_week_monday()
    week_dishes = [
        ["제육볶음", "된장국", "계란말이", "시금치나물", "배추김치"],
        ["김치찌개", "고등어구이", "콩나물무침", "메추리알장조림", "깍두기"],
        ["소불고기", "미역국", "감자조림", "도라지무침", "총각김치"],
        ["등심돈까스", "가락우동", "양배추샐러드", "단무지", "오이피클"],
        ["전주비빔밥", "유부장국", "잡채", "어묵볶음", "열무김치"],
    ]
    return [
        {"date": (monday + timedelta(days=i)).isoformat(), "menus": dishes}
        for i, dishes in enumerate(week_dishes)
    ]
