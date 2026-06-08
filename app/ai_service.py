import json
import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)

TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")

_SYSTEM = "너는 사내 식단을 분석하는 영양사야. 항상 유효한 JSON만 출력해."
_USER_TEMPLATE = (
    "오늘 점심 메뉴는 다음과 같아: {menus}.\n"
    "아래 키를 가진 JSON 으로만 답해.\n"
    "- summary: 메뉴를 아우르는 친근한 한줄평 (한국어, 40자 이내)\n"
    "- calories: 1인분 전체 예상 칼로리 (정수, kcal)\n"
    '- tags: 특징 태그 3~4개 (예: "고단백", "든든한", "한식")\n'
    "- recommendation: 누구에게/언제 좋은지 한 줄 추천"
)

_FALLBACK = {
    "summary": "오늘도 든든한 한 끼!",
    "calories": 750,
    "tags": ["한식", "균형잡힌", "든든한"],
    "recommendation": "점심 거르지 말고 든든하게 드세요.",
}


def analyze_menu(menus, client=None):
    try:
        client = client or OpenAI()
        resp = client.chat.completions.create(
            model=TEXT_MODEL,
            response_format={"type": "json_object"},
            temperature=0.7,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _USER_TEMPLATE.format(menus=", ".join(menus))},
            ],
        )
        return _normalize(json.loads(resp.choices[0].message.content))
    except Exception as exc:
        # 분석이 실패해도 화면은 떠야 하니 기본값으로 떨군다
        logger.warning("메뉴 분석 실패(%s) → 기본값", exc)
        return dict(_FALLBACK)


def _normalize(data):
    tags = data.get("tags") or _FALLBACK["tags"]
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return {
        "summary": str(data.get("summary") or _FALLBACK["summary"]).strip()[:60],
        "calories": _coerce_int(data.get("calories"), _FALLBACK["calories"]),
        "tags": [str(t).strip() for t in tags][:4],
        "recommendation": str(data.get("recommendation") or _FALLBACK["recommendation"]).strip(),
    }


def _coerce_int(value, default):
    if isinstance(value, (int, float)):
        return int(value)
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())  # "750 kcal" 대비
    return int(digits) if digits else default
