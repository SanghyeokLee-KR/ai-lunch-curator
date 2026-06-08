import types

from app import ai_service


def _client(content=None, exc=None):
    def create(**kwargs):
        if exc is not None:
            raise exc
        message = types.SimpleNamespace(content=content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    completions = types.SimpleNamespace(create=create)
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))


def test_parses_valid_json_and_normalizes():
    client = _client(content='{"summary":"맛있어요","calories":"700 kcal","tags":"고단백, 한식","recommendation":"추천!"}')
    out = ai_service.analyze_menu(["치즈닭갈비"], client=client)
    assert out["summary"] == "맛있어요"
    assert out["calories"] == 700
    assert out["tags"] == ["고단백", "한식"]
    assert out["recommendation"] == "추천!"


def test_non_json_response_falls_back():
    out = ai_service.analyze_menu(["치즈닭갈비"], client=_client(content="이건 JSON이 아니야"))
    assert out == dict(ai_service._FALLBACK)


def test_api_exception_falls_back():
    out = ai_service.analyze_menu(["치즈닭갈비"], client=_client(exc=RuntimeError("api down")))
    assert out == dict(ai_service._FALLBACK)
