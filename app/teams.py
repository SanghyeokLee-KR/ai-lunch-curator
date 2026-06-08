import logging
import os

import requests

from .utils import korean_date

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


def build_card(menu, base_url):
    analysis = menu.get("analysis", {})
    menus = menu.get("menus", [])
    tags = analysis.get("tags", [])
    calories = analysis.get("calories")

    body = []

    # 카드 이미지는 공개 https 만 렌더된다. http 면 그냥 텍스트.
    image_url = menu.get("image_url")
    if base_url.startswith("https://") and image_url:
        body.append({"type": "Image", "url": f"{base_url.rstrip('/')}{image_url}",
                     "size": "Stretch", "altText": "오늘의 점심"})

    body.append({"type": "TextBlock", "text": f"🍱 오늘의 점심 · {korean_date(menu['date'])}",
                 "size": "Large", "weight": "Bolder", "wrap": True})
    body.append({"type": "TextBlock", "text": "\n".join(f"• {m}" for m in menus),
                 "wrap": True, "spacing": "Small"})
    if analysis.get("summary"):
        body.append({"type": "Container", "style": "emphasis", "spacing": "Medium",
                     "items": [{"type": "TextBlock", "text": f"“{analysis['summary']}”", "wrap": True}]})
    if calories:
        body.append({"type": "TextBlock", "text": f"예상 칼로리 · 약 {calories:,} kcal",
                     "weight": "Bolder", "wrap": True, "spacing": "Medium"})
    if tags:
        body.append({"type": "TextBlock", "text": "  ".join(f"#{t}" for t in tags),
                     "color": "Accent", "wrap": True, "spacing": "Small"})
    if analysis.get("recommendation"):
        body.append({"type": "TextBlock", "text": f"추천 · {analysis['recommendation']}",
                     "isSubtle": True, "wrap": True, "spacing": "Small"})

    card = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard", "version": "1.4", "body": body,
        "actions": [{"type": "Action.OpenUrl", "title": "상세보기", "url": base_url}],
    }
    return {"type": "message", "attachments": [
        {"contentType": "application/vnd.microsoft.card.adaptive", "contentUrl": None, "content": card}
    ]}


def send_today_card(menu, base_url, webhook_url=None):
    webhook_url = webhook_url or os.getenv("WEBHOOK_URL")
    if not webhook_url:
        logger.error("WEBHOOK_URL 없음 → 발송 생략")
        return False
    try:
        resp = requests.post(webhook_url, json=build_card(menu, base_url),
                             headers={"Content-Type": "application/json"}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        logger.info("Teams 카드 발송 성공 (HTTP %s)", resp.status_code)
        return True
    except Exception as exc:
        # 발송 실패로 스케줄러까지 죽으면 안 되니 예외는 삼킨다
        logger.error("Teams 카드 발송 실패: %s", exc)
        return False
