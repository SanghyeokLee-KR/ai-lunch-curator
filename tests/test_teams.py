import types

from app import teams

MENU = {
    "date": "2026-06-08",
    "menus": ["치즈닭갈비", "흑미밥"],
    "analysis": {"summary": "맛있어요", "calories": 700, "tags": ["고단백", "한식"], "recommendation": "추천!"},
    "image_url": "/static/images/abc.png",
}


def _body(card):
    return card["attachments"][0]["content"]["body"]


def test_envelope_and_card_structure():
    card = teams.build_card(MENU, "http://localhost:8000")
    assert card["type"] == "message"
    attachment = card["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"
    content = attachment["content"]
    assert content["type"] == "AdaptiveCard"
    assert content["version"] == "1.4"
    assert isinstance(content["body"], list) and content["body"]
    action = content["actions"][0]
    assert action["type"] == "Action.OpenUrl"
    assert action["url"] == "http://localhost:8000"


def test_https_base_url_includes_image():
    card = teams.build_card(MENU, "https://lunch.example.com")
    images = [item for item in _body(card) if item.get("type") == "Image"]
    assert len(images) == 1
    assert images[0]["url"] == "https://lunch.example.com/static/images/abc.png"


def test_http_base_url_excludes_image():
    card = teams.build_card(MENU, "http://localhost:8000")
    assert all(item.get("type") != "Image" for item in _body(card))


def test_send_success_returns_true(monkeypatch):
    def fake_post(url, json=None, headers=None, timeout=None):
        return types.SimpleNamespace(status_code=202, raise_for_status=lambda: None)

    monkeypatch.setattr(teams.requests, "post", fake_post)
    assert teams.send_today_card(MENU, "http://x", webhook_url="https://hook") is True


def test_send_failure_is_swallowed(monkeypatch):
    def boom(*a, **k):
        raise teams.requests.RequestException("webhook down")

    monkeypatch.setattr(teams.requests, "post", boom)
    assert teams.send_today_card(MENU, "http://x", webhook_url="https://hook") is False


def test_send_without_webhook_returns_false(monkeypatch):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    assert teams.send_today_card(MENU, "http://x", webhook_url=None) is False
