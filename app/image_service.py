import base64
import logging
import os
from pathlib import Path

import requests
from openai import OpenAI

logger = logging.getLogger(__name__)

IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
IMAGES_DIR = Path(__file__).resolve().parent / "static" / "images"
DEFAULT_IMAGE_URL = "/static/images/default.png"


def generate_image(menus, menu_hash, client=None, images_dir=None,
                   get_cached=None, save_cached=None):
    images_dir = Path(images_dir) if images_dir else IMAGES_DIR
    images_dir.mkdir(parents=True, exist_ok=True)
    out_path = images_dir / f"{menu_hash}.png"
    rel_url = f"/static/images/{menu_hash}.png"

    # 같은 메뉴면 다시 안 만든다. 로컬 파일 먼저, 그 다음 DB 캐시.
    if out_path.exists():
        logger.info("이미지 캐시 히트. %s", out_path.name)
        return rel_url
    if get_cached is not None:
        cached = get_cached(menu_hash)
        if cached:
            return cached

    try:
        client = client or OpenAI()
        result = client.images.generate(
            model=IMAGE_MODEL, prompt=_build_prompt(menus), size="1024x1024", n=1
        )
        out_path.write_bytes(_extract_image_bytes(result.data[0]))
        if save_cached is not None:
            save_cached(menu_hash, rel_url)
        logger.info("이미지 생성. %s", rel_url)
        return rel_url
    except Exception as exc:
        logger.warning("이미지 생성 실패(%s) → 기본 이미지", exc)
        return DEFAULT_IMAGE_URL


def _build_prompt(menus):
    return (
        "한국 구내식당의 정갈한 점심 한 상을 위에서 내려다본 음식 사진. "
        f"메뉴: {', '.join(menus)}. 따뜻한 자연광, 깔끔한 우드 테이블, 식욕 돋는 색감. "
        "메뉴판이나 글자는 넣지 말 것."
    )


def _extract_image_bytes(item):
    # gpt-image-1 은 b64_json, dall-e 계열은 url 로 준다
    b64 = getattr(item, "b64_json", None)
    if b64:
        return base64.b64decode(b64)
    url = getattr(item, "url", None)
    if url:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
    raise RuntimeError("이미지 응답에 b64_json/url 둘 다 없음")
