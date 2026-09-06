#!/usr/bin/env python3
"""Génère automatiquement une paire WebP avec exactement sept différences connues."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import tempfile
import time
from typing import Any
from urllib.parse import urlparse
import warnings

import httpx
from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "app-presentateur" / "public" / "seven-differences"
CATALOG_PATH = ROOT / "back" / "domain" / "game_config" / "model" / "seven_differences_catalog.json"
DOTENV_PATH = ROOT / "back" / ".env"
MAX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 30_000_000
OUTPUT_SIZE = (1600, 900)
OPENAI_API_URL = "https://api.openai.com/v1"
OPENAI_MAX_ATTEMPTS = 5
OPENAI_MAX_RETRY_SECONDS = 30.0

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class OpenAIQuotaError(ValueError):
    """Le projet OpenAI ne dispose pas de crédits API utilisables."""


class OpenAIRateLimitError(ValueError):
    """La limitation temporaire persiste après toutes les tentatives."""


def _slugify(value: str) -> str:
    normalized = value.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized[:45] or "puzzle"


def _dotenv_value(name: str) -> str:
    """Lit une valeur simple du .env sans l’exécuter dans un shell."""
    try:
        lines = DOTENV_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            return value
    return ""


def _download_limited(client: httpx.Client, url: str, limit: int, headers: dict[str, str] | None = None) -> bytes:
    with client.stream("GET", url, headers=headers) as response:
        response.raise_for_status()
        content = bytearray()
        for chunk in response.iter_bytes():
            content.extend(chunk)
            if len(content) > limit:
                raise ValueError(f"Le fichier dépasse la limite de {limit // (1024 * 1024)} Mo.")
    return bytes(content)


def _download_pexels(query: str, api_key: str, seed: int) -> tuple[bytes, dict[str, str]]:
    headers = {"Authorization": api_key, "User-Agent": "GameBattlePuzzleGenerator/1.0"}
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "orientation": "landscape", "per_page": 30},
                headers=headers,
            )
            response.raise_for_status()
            if len(response.content) > 2 * 1024 * 1024:
                raise ValueError("La réponse Pexels est anormalement volumineuse.")
            payload = response.json()
            photos = payload.get("photos")
            if not isinstance(photos, list) or not photos:
                raise ValueError("Pexels n’a retourné aucune photographie pour cette recherche.")
            photo = random.Random(seed).choice(photos)
            source_url = str(photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large") or "")
            parsed = urlparse(source_url)
            if parsed.scheme != "https" or not (parsed.hostname or "").endswith("pexels.com"):
                raise ValueError("Pexels a retourné une URL d’image inattendue.")
            image_bytes = _download_limited(client, source_url, MAX_SOURCE_BYTES)
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise ValueError("Impossible de télécharger une image depuis Pexels en HTTPS.") from exc
    return image_bytes, {
        "provider": "Pexels",
        "author": str(photo.get("photographer", "")),
        "source_url": str(photo.get("url", "")),
    }


def _load_source(path: Path) -> tuple[bytes, dict[str, str]]:
    expanded = path.expanduser()
    if expanded.is_symlink():
        raise ValueError("L’image source locale est introuvable ou invalide.")
    resolved = expanded.resolve()
    if not resolved.is_file():
        raise ValueError("L’image source locale est introuvable ou invalide.")
    if resolved.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("L’image source dépasse la limite de 20 Mo.")
    return resolved.read_bytes(), {"provider": "local", "source_file": resolved.name}


def _prepare_image(image_bytes: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(image_bytes)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Seuls les fichiers JPEG, PNG et WebP sont acceptés.")
                source.load()
                normalized = ImageOps.exif_transpose(source).convert("RGB")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError) as exc:
        raise ValueError("Le fichier fourni n’est pas une image valide.") from exc
    if normalized.width * normalized.height > MAX_PIXELS:
        raise ValueError("L’image source contient trop de pixels.")
    return ImageOps.fit(normalized, OUTPUT_SIZE, method=Image.Resampling.LANCZOS)


def _image_bytes(image: Image.Image, image_format: str = "PNG") -> bytes:
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def _image_data_url(image: Image.Image) -> str:
    preview = image.copy()
    preview.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
    return f"data:image/jpeg;base64,{base64.b64encode(_image_bytes(preview, 'JPEG')).decode()}"


def _openai_error(response: httpx.Response) -> tuple[str, str]:
    try:
        error = response.json().get("error", {})
    except (json.JSONDecodeError, TypeError, AttributeError):
        return "", ""
    return str(error.get("code") or error.get("type") or ""), str(error.get("message") or "")


def _openai_request(client: httpx.Client, method: str, url: str, **kwargs: Any) -> httpx.Response:
    for attempt in range(OPENAI_MAX_ATTEMPTS):
        response = client.request(method, url, **kwargs)
        if response.status_code != 429:
            response.raise_for_status()
            return response

        error_code, error_message = _openai_error(response)
        normalized_error = f"{error_code} {error_message}".lower()
        if "insufficient_quota" in normalized_error or "billing" in normalized_error or "quota" in normalized_error:
            raise OpenAIQuotaError(
                "Le crédit API OpenAI est épuisé ou la facturation API n’est pas activée. "
                "ChatGPT et l’API sont facturés séparément. Vérifie le projet sur "
                "https://platform.openai.com/settings/organization/billing."
            )
        if attempt == OPENAI_MAX_ATTEMPTS - 1:
            raise OpenAIRateLimitError(
                "OpenAI limite encore les requêtes après plusieurs tentatives. Attends quelques minutes puis relance la commande."
            )
        retry_after = response.headers.get("Retry-After", "")
        try:
            delay = float(retry_after)
        except ValueError:
            delay = float(2 ** attempt)
        time.sleep(max(0.5, min(delay, OPENAI_MAX_RETRY_SECONDS)))
    raise AssertionError("Boucle de retry OpenAI invalide.")


def _openai_json(client: httpx.Client, api_key: str, prompt: str, image: Image.Image) -> dict[str, Any]:
    response = _openai_request(
        client,
        "POST",
        f"{OPENAI_API_URL}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": os.environ.get("OPENAI_VISION_MODEL", "gpt-4.1-mini"),
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _image_data_url(image), "detail": "high"}},
                ],
            }],
        },
    )
    return json.loads(response.json()["choices"][0]["message"]["content"])


def _intersection_ratio(first: dict[str, float], second: dict[str, float]) -> float:
    left = max(first["x"], second["x"])
    top = max(first["y"], second["y"])
    right = min(first["x"] + first["width"], second["x"] + second["width"])
    bottom = min(first["y"] + first["height"], second["y"] + second["height"])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    smallest = min(first["width"] * first["height"], second["width"] * second["height"])
    return intersection / smallest if smallest else 1.0


def _validate_edit_plans(payload: dict[str, Any]) -> list[dict[str, Any]]:
    changes = payload.get("changes")
    if not isinstance(changes, list) or len(changes) != 7:
        raise ValueError("Le modèle n’a pas proposé exactement sept modifications.")
    plans: list[dict[str, Any]] = []
    for index, change in enumerate(changes, start=1):
        region = change.get("region")
        if not isinstance(region, dict):
            raise ValueError("Une zone de modification est manquante.")
        try:
            normalized = {key: float(region[key]) for key in ("x", "y", "width", "height")}
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Une zone de modification est invalide.") from exc
        if (
            normalized["x"] < 0
            or normalized["y"] < 0
            or not 0.06 <= normalized["width"] <= 0.32
            or not 0.06 <= normalized["height"] <= 0.32
            or normalized["x"] + normalized["width"] > 1
            or normalized["y"] + normalized["height"] > 1
        ):
            raise ValueError("Une zone proposée est hors de l’image ou de taille incorrecte.")
        label = str(change.get("label", "")).strip()
        edit_prompt = str(change.get("edit_prompt", "")).strip()
        if not 8 <= len(label) <= 160 or not 12 <= len(edit_prompt) <= 300:
            raise ValueError("Une description de modification est invalide.")
        plan = {"id": f"d{index:02d}", "label": label, "edit_prompt": edit_prompt, "region": normalized}
        if any(_intersection_ratio(normalized, previous["region"]) > 0.15 for previous in plans):
            raise ValueError("Deux zones de modification se chevauchent trop.")
        plans.append(plan)
    return plans


def _plan_photo_edits(source: Image.Image, api_key: str, seed: int) -> list[dict[str, Any]]:
    prompt = f"""Analyse cette photographie pour créer un jeu des 7 différences (graine {seed}).
Retourne uniquement du JSON avec la clé changes contenant exactement 7 objets.
Choisis sept objets RÉELS, clairement visibles, distincts et éloignés dans l’image.
Pour chaque objet :
- label : description française exacte de la différence future ;
- edit_prompt : instruction anglaise locale et photoréaliste pour supprimer, déplacer, recolorer ou modifier cet objet ;
- region : x, y, width, height normalisés entre 0 et 1, englobant l’objet avec une marge.
Les zones mesurent entre 0.06 et 0.32 dans chaque dimension et se chevauchent au maximum de 15 %.
Interdictions : formes géométriques ajoutées, flèches, panneaux, texte décoratif, symboles, nouveaux objets sans rapport avec la scène.
Exemple de structure : {{"changes":[{{"label":"Le ballon blanc a disparu","edit_prompt":"Remove the white football and naturally reconstruct the grass behind it.","region":{{"x":0.1,"y":0.2,"width":0.12,"height":0.15}}}}]}}"""
    with httpx.Client(timeout=120) as client:
        for _ in range(3):
            try:
                return _validate_edit_plans(_openai_json(client, api_key, prompt, source))
            except (OpenAIQuotaError, OpenAIRateLimitError):
                raise
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue
    raise ValueError("Impossible d’identifier sept objets réels suffisamment distincts dans cette photographie.")


def _pixel_box(region: dict[str, float], size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = size
    return (
        max(0, round(region["x"] * width)),
        max(0, round(region["y"] * height)),
        min(width, round((region["x"] + region["width"]) * width)),
        min(height, round((region["y"] + region["height"]) * height)),
    )


def _edit_photo_region(client: httpx.Client, api_key: str, source: Image.Image, plan: dict[str, Any]) -> Image.Image:
    box = _pixel_box(plan["region"], source.size)
    patch = source.crop(box).convert("RGBA")
    request_size = (1024, 1024)
    editable = ImageOps.fit(patch, request_size, method=Image.Resampling.LANCZOS)
    mask = Image.new("RGBA", request_size, (255, 255, 255, 255))
    inset = 100
    mask.paste((255, 255, 255, 0), (inset, inset, request_size[0] - inset, request_size[1] - inset))
    response = _openai_request(
        client,
        "POST",
        f"{OPENAI_API_URL}/images/edits",
        headers={"Authorization": f"Bearer {api_key}"},
        data={
            "model": os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1"),
            "prompt": (
                f"Edit only the requested real object: {plan['edit_prompt']} "
                "Keep the scene photorealistic, preserve perspective and lighting, and add no text, symbols, borders or panels."
            ),
            "size": "1024x1024",
            "quality": "medium",
            "output_format": "png",
        },
        files={
            "image": ("image.png", _image_bytes(editable), "image/png"),
            "mask": ("mask.png", _image_bytes(mask), "image/png"),
        },
        timeout=180,
    )
    edited_bytes = base64.b64decode(response.json()["data"][0]["b64_json"], validate=True)
    with Image.open(io.BytesIO(edited_bytes)) as edited:
        result = edited.convert("RGB").resize(patch.size, Image.Resampling.LANCZOS)
    blend_mask = Image.new("L", patch.size, 0)
    inner = max(3, round(min(patch.size) * 0.08))
    blend_mask.paste(255, (inner, inner, patch.width - inner, patch.height - inner))
    blend_mask = blend_mask.filter(ImageFilter.GaussianBlur(max(2, inner // 2)))
    return Image.composite(result, patch.convert("RGB"), blend_mask)


def _validate_verification(payload: dict[str, Any], expected_ids: set[str]) -> None:
    confirmed = payload.get("confirmed_ids")
    if (
        payload.get("valid") is not True
        or not isinstance(confirmed, list)
        or {str(item) for item in confirmed} != expected_ids
        or payload.get("unexpected_changes") not in (False, [], None)
    ):
        reason = str(payload.get("reason", "validation visuelle incomplète"))[:240]
        raise ValueError(f"La paire générée a été refusée : {reason}")


def _verify_photo_pair(
    client: httpx.Client,
    api_key: str,
    original: Image.Image,
    modified: Image.Image,
    plans: list[dict[str, Any]],
) -> None:
    comparison = Image.new("RGB", (original.width * 2, original.height), "white")
    comparison.paste(original, (0, 0))
    comparison.paste(modified, (original.width, 0))
    expected = [{"id": plan["id"], "label": plan["label"], "region": plan["region"]} for plan in plans]
    prompt = f"""Compare les deux photographies côte à côte : originale à gauche, modifiée à droite.
Vérifie visuellement chacune des sept différences attendues suivantes : {json.dumps(expected, ensure_ascii=False)}
Retourne uniquement un JSON :
{{"valid": true ou false, "confirmed_ids": [identifiants réellement visibles], "unexpected_changes": false ou [descriptions], "reason": "explication courte"}}.
`valid` vaut true uniquement si les sept changements décrits sont réellement visibles, naturels, localisés dans leurs régions et si aucun autre changement important n’apparaît."""
    _validate_verification(_openai_json(client, api_key, prompt, comparison), {plan["id"] for plan in plans})


def _build_pair(source: Image.Image, seed: int, api_key: str) -> tuple[Image.Image, Image.Image, list[dict[str, Any]]]:
    original = source.convert("RGB")
    modified = original.copy()
    plans = _plan_photo_edits(original, api_key, seed)
    with httpx.Client(timeout=180) as client:
        for plan in plans:
            box = _pixel_box(plan["region"], original.size)
            edited_patch = _edit_photo_region(client, api_key, modified, plan)
            before_patch = modified.crop(box)
            difference = ImageChops.difference(before_patch, edited_patch).convert("L")
            if ImageStat.Stat(difference).mean[0] < 2.0:
                raise ValueError(f"La retouche n’est pas assez visible : {plan['label']}")
            modified.paste(edited_patch, box)
        _verify_photo_pair(client, api_key, original, modified, plans)
    differences = [
        {"id": plan["id"], "label": plan["label"], "region": plan["region"]}
        for plan in plans
    ]
    return original, modified, differences


def _write_webp_atomic(image: Image.Image, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".webp", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        image.save(temporary_path, format="WEBP", quality=88, method=6)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)


def _load_manifest() -> dict[str, Any]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("puzzles"), list):
        raise ValueError("Le manifeste existant est invalide.")
    return payload


def _write_manifest_atomic(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile("w", dir=CATALOG_PATH.parent, encoding="utf-8", delete=False) as temporary:
        temporary.write(serialized)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, CATALOG_PATH)


def generate_puzzle(
    *,
    image_bytes: bytes,
    title: str,
    seed: int,
    openai_api_key: str,
    requested_id: str | None,
    attribution: dict[str, str],
    replace_existing: bool,
) -> dict[str, Any]:
    if not 2 <= len(title.strip()) <= 80:
        raise ValueError("Le titre doit contenir entre 2 et 80 caractères.")
    digest = hashlib.sha256(image_bytes + str(seed).encode()).hexdigest()[:10]
    puzzle_id = requested_id or f"{_slugify(title)}-{digest[:6]}"
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", puzzle_id):
        raise ValueError("L’identifiant doit contenir 3 à 64 caractères minuscules, chiffres ou tirets.")

    source = _prepare_image(image_bytes)
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY est requis pour créer de vraies retouches photographiques.")
    original, modified, differences = _build_pair(source, seed, openai_api_key)
    original_name = f"{puzzle_id}-{digest}-original.webp"
    modified_name = f"{puzzle_id}-{digest}-modified.webp"
    original_path = PUBLIC_DIR / original_name
    modified_path = PUBLIC_DIR / modified_name
    manifest = _load_manifest()
    existing_index = next((index for index, item in enumerate(manifest["puzzles"]) if item.get("id") == puzzle_id), None)
    if existing_index is not None and not replace_existing:
        raise ValueError(f"Le puzzle {puzzle_id!r} existe déjà. Utilise --replace pour le remplacer.")

    entry = {
        "id": puzzle_id,
        "title": title.strip(),
        "original_image_url": f"/seven-differences/{original_name}",
        "modified_image_url": f"/seven-differences/{modified_name}",
        "differences": differences,
        "generation": {"seed": seed, "width": OUTPUT_SIZE[0], "height": OUTPUT_SIZE[1]},
        "attribution": attribution,
    }
    _write_webp_atomic(original, original_path)
    _write_webp_atomic(modified, modified_path)
    if existing_index is None:
        manifest["puzzles"].append(entry)
    else:
        previous = manifest["puzzles"][existing_index]
        manifest["puzzles"][existing_index] = entry
        for key in ("original_image_url", "modified_image_url"):
            previous_name = Path(str(previous.get(key, ""))).name
            if previous_name and previous_name not in {original_name, modified_name}:
                (PUBLIC_DIR / previous_name).unlink(missing_ok=True)
    _write_manifest_atomic(manifest)
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Image JPEG, PNG ou WebP locale")
    source.add_argument("--pexels-query", help="Recherche automatique d’une photographie horizontale sur Pexels")
    parser.add_argument("--title", required=True, help="Titre affiché pour le puzzle")
    parser.add_argument("--id", dest="puzzle_id", help="Identifiant stable facultatif")
    parser.add_argument("--seed", type=int, default=1, help="Graine déterministe des transformations")
    parser.add_argument("--replace", action="store_true", help="Remplacer un puzzle portant le même identifiant")
    args = parser.parse_args()

    openai_api_key = (os.environ.get("OPENAI_API_KEY") or _dotenv_value("OPENAI_API_KEY")).strip()
    if not openai_api_key:
        parser.error("OPENAI_API_KEY est requis dans l’environnement ou dans back/.env pour éditer la photographie.")

    try:
        if args.input:
            image_bytes, attribution = _load_source(args.input)
        else:
            pexels_api_key = (os.environ.get("PEXELS_API_KEY") or _dotenv_value("PEXELS_API_KEY")).strip()
            if not pexels_api_key:
                raise ValueError("PEXELS_API_KEY est requis dans l’environnement ou dans back/.env avec --pexels-query.")
            image_bytes, attribution = _download_pexels(args.pexels_query, pexels_api_key, args.seed)
        entry = generate_puzzle(
            image_bytes=image_bytes,
            title=args.title,
            seed=args.seed,
            openai_api_key=openai_api_key,
            requested_id=args.puzzle_id,
            attribution=attribution,
            replace_existing=args.replace,
        )
    except (ValueError, httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(f"Puzzle créé : {entry['id']}")
    print(f"Originale : {entry['original_image_url']}")
    print(f"Modifiée  : {entry['modified_image_url']}")
    print("Les 7 descriptions ont été ajoutées automatiquement au catalogue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
