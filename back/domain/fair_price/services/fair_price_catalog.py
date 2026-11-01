from __future__ import annotations

import random

from domain.fair_price.models.price_item import PriceBand, PriceItem

# Vrais produits, prix publics TTC relevés sur le site de la marque ou d'un grand distributeur français, arrondis à
# l'euro. Photos libres de Wikimedia Commons : auteur, licence et source de chaque prix dans `media/fair_price/CREDITS.md`.
PRICES_CHECKED_ON = "octobre 2026"


def _items(*rows: tuple[str, str, int, str]) -> tuple[PriceItem, ...]:
    """(fichier image, nom, prix en euros, « auteur · licence » de la photo) ; l'id est le fichier sans extension."""
    return tuple(
        PriceItem(id=image.rsplit(".", 1)[0], name=name, image=image, price=price, credit=f"Photo : {credit}")
        for image, name, price, credit in rows
    )


# Prix tous différents au sein d'une gamme : deux équipes ne cherchent jamais le même nombre.
PRICE_BANDS: tuple[PriceBand, ...] = (
    PriceBand("petits-prix", "Moins de 30 €", _items(
        ("ikea-frakta.jpg", "Le grand sac FRAKTA d’IKEA", 1, "Andrea014 · CC BY-SA 3.0 DE"),
        ("savon-marseille-marius-fabre.jpg", "Le savon de Marseille Marius Fabre 400 g", 5, "Soapgrandmama · CC BY-SA 4.0"),
        ("rubiks-cube-3x3.jpg", "Le Rubik’s Cube 3x3", 9, "Lars Karlsson (Keqs) · CC BY-SA 3.0"),
        ("uno-mattel.jpg", "Le jeu de cartes UNO de Mattel", 10, "Cburnett · Domaine public"),
        ("puissance-4-hasbro.jpg", "Le jeu Puissance 4 de Hasbro", 11, "Popperipopp · CC BY 3.0"),
        ("opinel-n8-inox.jpg", "Le couteau Opinel n°8 inox", 12, "fitm · CC BY-SA 3.0"),
        ("duralex-picardie-lot-de-6.jpg", "Le lot de 6 verres Duralex Picardie 25 cl", 15, "Denkhenk · CC BY-SA 3.0"),
        ("jungle-speed.jpg", "Le jeu Jungle Speed d’Asmodee", 19, "Nicosmos · CC BY-SA 3.0"),
    )),
    PriceBand("moyens", "De 30 à 150 €", _items(
        ("bialetti-moka-express.png", "La cafetière Bialetti Moka Express (6 tasses)", 46, "Bialetti Industrie · CC BY-SA 4.0"),
        ("crocs-classic-clog.jpg", "Les sabots Crocs Classic Clog", 55, "Skyeyemx · CC BY-SA 4.0"),
        ("manette-xbox-sans-fil.jpg", "La manette sans fil Xbox", 65, "uKER · CC BY-SA 4.0"),
        ("manette-playstation-dualsense.png", "La manette PlayStation DualSense", 75, "Alex Cochrane · CC BY-SA 4.0"),
        ("fujifilm-instax-mini-12.jpg", "L’appareil photo Fujifilm Instax Mini 12", 79, "Tony Webster · CC BY 2.0"),
        ("polaroid-now-gen-3.jpg", "L’appareil photo Polaroid Now (3e génération)", 110, "TaurusEmerald · CC BY-SA 4.0"),
        ("nike-air-force-1.jpg", "Les baskets Nike Air Force 1 blanches", 120, "HI 622 · CC BY-SA 4.0"),
        ("apple-airpods-5.jpg", "Les écouteurs Apple AirPods 5", 149, "Cheeseburgahhh · CC BY-SA 4.0"),
    )),
    PriceBand("gros-achats", "De 150 à 900 €", _items(
        ("kindle-paperwhite.jpg", "La liseuse Kindle Paperwhite (16 Go)", 210, "Kyu3a · CC BY-SA 4.0"),
        ("dyson-supersonic.jpg", "Le sèche-cheveux Dyson Supersonic", 299, "FASTILY · CC BY-SA 4.0"),
        ("nintendo-switch-2.jpg", "La console Nintendo Switch 2", 470, "Crisco 1492 · CC BY-SA 4.0"),
        ("kitchenaid-artisan.jpg", "Le robot pâtissier KitchenAid Artisan", 500, "BenFrantzDale · CC BY-SA 2.0"),
        ("meta-quest-3.jpg", "Le casque Meta Quest 3 (512 Go)", 620, "Roy.wonder.cohen · CC BY-SA 4.0"),
        ("dji-mini-5-pro.jpg", "Le drone DJI Mini 5 Pro", 718, "ZLEA · CC BY-SA 4.0"),
        ("apple-iphone-17e.jpg", "L’iPhone 17e d’Apple (256 Go)", 869, "Kyu3a · CC BY-SA 4.0"),
    )),
    PriceBand("grands-lots", "Plus de 900 €", _items(
        ("macbook-air-13-m5.jpg", "Le MacBook Air 13 pouces d’Apple", 1_399, "AzureSaturn · CC0"),
        ("honda-sh125i.jpg", "Le scooter Honda SH125i", 3_999, "Corvettec6r · CC BY 4.0"),
        ("dacia-sandero.jpg", "La Dacia Sandero", 13_990, "Alexander Migl · CC BY-SA 4.0"),
        ("renault-clio.jpg", "La Renault Clio", 19_900, "Alexander Migl · CC BY-SA 4.0"),
        ("renault-5-e-tech.jpg", "La Renault 5 E-Tech électrique", 28_490, "Alexander Migl · CC BY-SA 4.0"),
        ("volkswagen-golf.jpg", "La Volkswagen Golf", 31_000, "Alexander-93 · CC BY-SA 4.0"),
        ("honda-gold-wing-tour.jpg", "La moto Honda Gold Wing Tour", 37_999, "Tarrakaner · CC BY-SA 4.0"),
        ("renault-espace.jpg", "Le Renault Espace", 46_500, "Alexander Migl · CC BY-SA 4.0"),
    )),
)
PRICE_ITEMS_BY_ID: dict[str, PriceItem] = {item.id: item for band in PRICE_BANDS for item in band.items}
PRICE_BANDS_BY_ID: dict[str, PriceBand] = {band.id: band for band in PRICE_BANDS}


def pick_round_items(team_count: int, rng: random.Random | None = None) -> tuple[PriceBand, list[PriceItem]]:
    """Une gamme de prix, puis un objet différent de cette gamme pour chaque équipe."""
    rng = rng or random.SystemRandom()
    band = rng.choice([band for band in PRICE_BANDS if len(band.items) >= team_count])
    return band, rng.sample(band.items, team_count)
