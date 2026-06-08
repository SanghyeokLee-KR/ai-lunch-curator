from datetime import date

from app.utils import korean_date, menu_hash, this_week_monday


def test_menu_hash_is_order_independent():
    assert menu_hash(["된장국", "제육볶음"]) == menu_hash(["제육볶음", "된장국"])


def test_menu_hash_ignores_surrounding_whitespace():
    assert menu_hash([" 제육볶음 ", "된장국"]) == menu_hash(["제육볶음", "된장국"])


def test_menu_hash_differs_for_different_menus():
    assert menu_hash(["제육볶음"]) != menu_hash(["김치찌개"])


def test_korean_date_formats_with_weekday():
    assert korean_date("2026-06-08") == "2026년 6월 8일 월요일"


def test_this_week_monday_returns_monday():
    monday = this_week_monday(date(2026, 6, 10))
    assert monday == date(2026, 6, 8)
    assert monday.weekday() == 0
