from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from domain.fair_price.services.fair_price_catalog import PRICE_ITEMS_BY_ID

MEDIA_DIR = Path(__file__).resolve().parents[2] / "media"
# Liste fermée : seules les images du catalogue sont servies (aucun chemin construit depuis la requête).
FAIR_PRICE_IMAGES: dict[str, Path] = {item.image: MEDIA_DIR / "fair_price" / item.image for item in PRICE_ITEMS_BY_ID.values()}
# Images publiques et immuables : cache long, et lisibles par l'écran public même s'il n'a pas la même origine.
_MEDIA_HEADERS = {"Cache-Control": "public, max-age=604800, immutable", "Cross-Origin-Resource-Policy": "cross-origin"}

router = APIRouter(prefix="/media", tags=["media"])


_MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg"}


@router.get("/fair-price/{image_name}", summary="Image d’un objet du Juste prix", response_class=FileResponse)
async def fair_price_image(image_name: str) -> FileResponse:
    path = FAIR_PRICE_IMAGES.get(image_name)
    if path is None or not path.is_file() or path.suffix not in _MEDIA_TYPES:
        raise HTTPException(status_code=404, detail="Image introuvable.")
    return FileResponse(path, media_type=_MEDIA_TYPES[path.suffix], headers=_MEDIA_HEADERS)
