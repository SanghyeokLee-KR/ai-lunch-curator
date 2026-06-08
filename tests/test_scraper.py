from datetime import date, timedelta

from app import scraper
from app.utils import this_week_monday

KOPO_HTML = """
<table class="tbl_table menu">
  <thead><tr><th>구분</th><th>조식</th><th>중식</th><th>석식</th></tr></thead>
  <tbody>
    <tr>
      <td><script>document.write(getDay2('2026-06-08 00:00:00.0'));</script><br/>월요일</td>
      <td><span class="kcal"></span><span></span></td>
      <td><span>치즈닭갈비, 흑미밥, 청양된장찌개</span></td>
      <td><span class="kcal"></span><span></span></td>
    </tr>
    <tr>
      <td><script>document.write(getDay2('2026-06-13 00:00:00.0'));</script><br/>토요일</td>
      <td><span class="kcal"></span><span></span></td>
      <td><span></span></td>
      <td><span class="kcal"></span><span></span></td>
    </tr>
  </tbody>
</table>
"""


class _FakeResp:
    def __init__(self, text):
        self.text = text
        self.apparent_encoding = "utf-8"
        self.encoding = "utf-8"
        self.status_code = 200

    def raise_for_status(self):
        return None


def test_parse_extracts_lunch_and_skips_empty():
    days = scraper._parse_menu_html(KOPO_HTML)
    assert len(days) == 1
    assert days[0]["date"] == "2026-06-08"
    assert days[0]["menus"] == ["치즈닭갈비", "흑미밥", "청양된장찌개"]


def test_fetch_returns_parsed_when_source_ok(monkeypatch):
    monkeypatch.setattr(scraper.requests, "get", lambda *a, **k: _FakeResp(KOPO_HTML))
    week = scraper.fetch_weekly_menu("http://fake.kopo")
    assert len(week) == 1
    assert week[0]["date"] == "2026-06-08"


def test_fetch_falls_back_on_network_error(monkeypatch):
    def boom(*a, **k):
        raise scraper.requests.RequestException("network down")

    monkeypatch.setattr(scraper.requests, "get", boom)
    assert len(scraper.fetch_weekly_menu("http://fake.kopo")) == 5


def test_no_source_url_uses_sample():
    assert len(scraper.fetch_weekly_menu(None)) == 5


def test_sample_dates_are_relative_to_this_monday():
    week = scraper._sample_weekly_menu()
    assert len(week) == 5
    assert week[0]["date"] == this_week_monday().isoformat()
    first = date.fromisoformat(week[0]["date"])
    for offset, day in enumerate(week):
        assert day["date"] == (first + timedelta(days=offset)).isoformat()
        assert day["menus"]
