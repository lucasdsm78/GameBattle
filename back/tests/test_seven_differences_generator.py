from __future__ import annotations

import importlib.util
from io import BytesIO
import json
from pathlib import Path

import httpx
from PIL import Image, ImageChops

from domain.game_config.model.seven_differences_catalog import load_seven_differences_catalog

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "generate-seven-differences.py"
SPEC = importlib.util.spec_from_file_location("generate_seven_differences", SCRIPT_PATH)
assert SPEC and SPEC.loader
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def _source_bytes() -> bytes:
    image = Image.new("RGB", (1200, 800), "#184d35")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _plans() -> list[dict]:
    return [
        {
            "label": f"L’objet réel numéro {index} a changé de couleur",
            "edit_prompt": f"Change only the color of real object number {index} while preserving the scene.",
            "region": {"x": 0.02 + ((index - 1) % 4) * 0.24, "y": 0.05 + ((index - 1) // 4) * 0.48, "width": 0.12, "height": 0.16},
        }
        for index in range(1, 8)
    ]


def _fake_build_pair(source, seed, api_key):
    del seed, api_key
    original = source.convert("RGB")
    modified = original.copy()
    modified.putpixel((10, 10), (255, 0, 0))
    differences = GENERATOR._validate_edit_plans({"changes": _plans()})
    return original, modified, [
        {"id": item["id"], "label": item["label"], "region": item["region"]}
        for item in differences
    ]


def test_generator_creates_two_valid_webp_files_and_catalog_entry(tmp_path, monkeypatch) -> None:
    public_dir = tmp_path / "public"
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text('{"version": 1, "puzzles": []}\n', encoding="utf-8")
    monkeypatch.setattr(GENERATOR, "PUBLIC_DIR", public_dir)
    monkeypatch.setattr(GENERATOR, "CATALOG_PATH", catalog_path)
    monkeypatch.setattr(GENERATOR, "_build_pair", _fake_build_pair)

    entry = GENERATOR.generate_puzzle(
        image_bytes=_source_bytes(),
        title="Match automatisé",
        seed=17,
        openai_api_key="openai-test-key",
        requested_id="match-automatise",
        attribution={"provider": "test"},
        replace_existing=False,
    )

    assert len(entry["differences"]) == 7
    assert [item["id"] for item in entry["differences"]] == [f"d{index:02d}" for index in range(1, 8)]
    assert all(item["label"] and set(item["region"]) == {"x", "y", "width", "height"} for item in entry["differences"])
    assert all(0 <= value <= 1 for item in entry["differences"] for value in item["region"].values())

    original_path = public_dir / Path(entry["original_image_url"]).name
    modified_path = public_dir / Path(entry["modified_image_url"]).name
    with Image.open(original_path) as original, Image.open(modified_path) as modified:
        assert original.format == modified.format == "WEBP"
        assert original.size == modified.size == (1600, 900)
        assert ImageChops.difference(original.convert("RGB"), modified.convert("RGB")).getbbox() is not None

    loaded = load_seven_differences_catalog(catalog_path)
    assert len(loaded) == 1
    assert loaded[0].id == "match-automatise"
    assert len(loaded[0].differences) == 7


def test_edit_plan_accepts_seven_real_non_overlapping_objects() -> None:
    plans = GENERATOR._validate_edit_plans({"changes": _plans()})

    assert [plan["id"] for plan in plans] == [f"d{index:02d}" for index in range(1, 8)]
    assert all("objet réel" in plan["label"] for plan in plans)


def test_edit_plan_rejects_overlapping_objects() -> None:
    plans = _plans()
    plans[1]["region"] = dict(plans[0]["region"])

    try:
        GENERATOR._validate_edit_plans({"changes": plans})
    except ValueError as exc:
        assert "chevauchent" in str(exc)
    else:
        raise AssertionError("Des zones superposées auraient dû être refusées.")


def test_visual_verification_requires_all_seven_expected_changes() -> None:
    expected = {f"d{index:02d}" for index in range(1, 8)}
    GENERATOR._validate_verification(
        {"valid": True, "confirmed_ids": sorted(expected), "unexpected_changes": False},
        expected,
    )

    try:
        GENERATOR._validate_verification(
            {"valid": False, "confirmed_ids": sorted(expected - {"d07"}), "unexpected_changes": False, "reason": "d07 absent"},
            expected,
        )
    except ValueError as exc:
        assert "d07 absent" in str(exc)
    else:
        raise AssertionError("Une retouche non confirmée aurait dû invalider le puzzle.")


def test_generator_refuses_duplicate_identifier_without_replace(tmp_path, monkeypatch) -> None:
    public_dir = tmp_path / "public"
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps({"version": 1, "puzzles": []}), encoding="utf-8")
    monkeypatch.setattr(GENERATOR, "PUBLIC_DIR", public_dir)
    monkeypatch.setattr(GENERATOR, "CATALOG_PATH", catalog_path)
    monkeypatch.setattr(GENERATOR, "_build_pair", _fake_build_pair)
    arguments = {
        "image_bytes": _source_bytes(),
        "title": "Match automatisé",
        "seed": 1,
        "openai_api_key": "openai-test-key",
        "requested_id": "match-automatise",
        "attribution": {"provider": "test"},
        "replace_existing": False,
    }

    GENERATOR.generate_puzzle(**arguments)

    try:
        GENERATOR.generate_puzzle(**arguments)
    except ValueError as exc:
        assert "existe déjà" in str(exc)
    else:
        raise AssertionError("Un identifiant dupliqué aurait dû être refusé.")


def test_generator_reads_pexels_key_from_dotenv_without_shell_evaluation(tmp_path, monkeypatch) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        'GAMEBATTLE_BLINDTEST_PLAYLIST_URL="https://example.test/list?a=1&b=2"\n'
        'PEXELS_API_KEY="pexels-test-key"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(GENERATOR, "DOTENV_PATH", dotenv_path)

    assert GENERATOR._dotenv_value("PEXELS_API_KEY") == "pexels-test-key"


def test_openai_request_retries_temporary_rate_limit(monkeypatch) -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0.1"}, json={"error": {"code": "rate_limit_exceeded"}})
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(GENERATOR.time, "sleep", delays.append)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = GENERATOR._openai_request(client, "POST", "https://api.openai.test/v1/test")

    assert response.status_code == 200
    assert attempts == 2
    assert delays == [0.5]


def test_openai_request_does_not_retry_exhausted_quota(monkeypatch) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, json={"error": {"code": "insufficient_quota", "message": "quota exceeded"}})

    monkeypatch.setattr(GENERATOR.time, "sleep", lambda _: None)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        try:
            GENERATOR._openai_request(client, "POST", "https://api.openai.test/v1/test")
        except ValueError as exc:
            assert "facturation" in str(exc)
        else:
            raise AssertionError("Un quota épuisé aurait dû arrêter immédiatement la génération.")

    assert attempts == 1


def test_planner_preserves_quota_error(monkeypatch) -> None:
    attempts = 0

    def fail_with_quota(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        raise GENERATOR.OpenAIQuotaError("Crédit API épuisé")

    monkeypatch.setattr(GENERATOR, "_openai_json", fail_with_quota)

    try:
        GENERATOR._plan_photo_edits(Image.new("RGB", (1600, 900)), "openai-test-key", 1)
    except GENERATOR.OpenAIQuotaError as exc:
        assert "Crédit API épuisé" in str(exc)
    else:
        raise AssertionError("L’erreur de quota aurait dû être conservée.")

    assert attempts == 1
