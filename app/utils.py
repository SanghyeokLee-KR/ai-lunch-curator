import hashlib
from datetime import date, timedelta

_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def menu_hash(menus):
    # 순서가 달라도 같은 구성이면 같은 키가 나오게 정렬 후 해시 (이미지 캐시용)
    normalized = sorted(m.strip() for m in menus if m and m.strip())
    return hashlib.sha256("|".join(normalized).encode("utf-8")).hexdigest()


def korean_date(value):
    d = date.fromisoformat(value) if isinstance(value, str) else value
    return f"{d.year}년 {d.month}월 {d.day}일 {_WEEKDAYS[d.weekday()]}요일"


def this_week_monday(today=None):
    today = today or date.today()
    return today - timedelta(days=today.weekday())
