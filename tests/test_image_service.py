import base64
import types

from app import image_service


def _client(b64=None, url=None, exc=None):
    def generate(**kwargs):
        if exc is not None:
            raise exc
        item = types.SimpleNamespace(b64_json=b64, url=url)
        return types.SimpleNamespace(data=[item])

    return types.SimpleNamespace(images=types.SimpleNamespace(generate=generate))


def test_saves_bytes_and_returns_rel_url(tmp_path):
    raw = b"\x89PNG fake-image-bytes"
    client = _client(b64=base64.b64encode(raw).decode())
    rel = image_service.generate_image(["치즈닭갈비"], "hash123", client=client, images_dir=tmp_path)
    assert rel == "/static/images/hash123.png"
    assert (tmp_path / "hash123.png").read_bytes() == raw


def test_failure_returns_default_image(tmp_path):
    client = _client(exc=RuntimeError("image api down"))
    rel = image_service.generate_image(["치즈닭갈비"], "h", client=client, images_dir=tmp_path)
    assert rel == image_service.DEFAULT_IMAGE_URL
    assert not (tmp_path / "h.png").exists()


def test_cache_hit_does_not_call_api(tmp_path):
    (tmp_path / "cached.png").write_bytes(b"old-bytes")

    def boom(**kwargs):
        raise AssertionError("캐시 히트면 API 를 부르면 안 된다")

    client = types.SimpleNamespace(images=types.SimpleNamespace(generate=boom))
    rel = image_service.generate_image(["x"], "cached", client=client, images_dir=tmp_path)
    assert rel == "/static/images/cached.png"
    assert (tmp_path / "cached.png").read_bytes() == b"old-bytes"


def test_url_style_response_is_downloaded(tmp_path, monkeypatch):
    client = _client(url="http://img.example/x.png")

    def fake_get(url, timeout=30):
        return types.SimpleNamespace(content=b"downloaded-bytes", raise_for_status=lambda: None)

    monkeypatch.setattr(image_service.requests, "get", fake_get)
    image_service.generate_image(["x"], "urlhash", client=client, images_dir=tmp_path)
    assert (tmp_path / "urlhash.png").read_bytes() == b"downloaded-bytes"
