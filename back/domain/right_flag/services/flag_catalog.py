from __future__ import annotations

import random

from domain.right_flag.models.country import Country

# Tirage imprévisible : personne ne peut anticiper la position du bon drapeau.
_SYSTEM_RANDOM = random.SystemRandom()

FLAGS_PER_ROUND = 7
LOOKALIKES_PER_ROUND = 4

_FAMILIES: dict[str, tuple[tuple[str, str], ...]] = {
    "Tricolores verticaux": (
        ("FR", "France"), ("IT", "Italie"), ("IE", "Irlande"), ("BE", "Belgique"), ("RO", "Roumanie"), ("TD", "Tchad"),
        ("ML", "Mali"), ("GN", "Guinée"), ("CI", "Côte d’Ivoire"), ("NG", "Nigeria"), ("MX", "Mexique"), ("PE", "Pérou"),
    ),
    "Tricolores horizontaux": (
        ("DE", "Allemagne"), ("NL", "Pays-Bas"), ("RU", "Russie"), ("LU", "Luxembourg"), ("AT", "Autriche"),
        ("HU", "Hongrie"), ("BG", "Bulgarie"), ("LT", "Lituanie"), ("EE", "Estonie"), ("AM", "Arménie"), ("GA", "Gabon"),
        ("SL", "Sierra Leone"), ("YE", "Yémen"), ("EG", "Égypte"),
    ),
    "Croix nordiques": (("SE", "Suède"), ("NO", "Norvège"), ("DK", "Danemark"), ("FI", "Finlande"), ("IS", "Islande")),
    "Rouge et blanc": (
        ("PL", "Pologne"), ("ID", "Indonésie"), ("MC", "Monaco"), ("SG", "Singapour"), ("JP", "Japon"), ("CH", "Suisse"),
        ("CA", "Canada"), ("LV", "Lettonie"), ("GE", "Géorgie"), ("MT", "Malte"),
    ),
    "Croissants et étoiles": (
        ("TR", "Turquie"), ("TN", "Tunisie"), ("DZ", "Algérie"), ("PK", "Pakistan"), ("AZ", "Azerbaïdjan"),
        ("MA", "Maroc"), ("MR", "Mauritanie"), ("LY", "Libye"),
    ),
    "Union Jack": (("GB", "Royaume-Uni"), ("AU", "Australie"), ("NZ", "Nouvelle-Zélande"), ("FJ", "Fidji"), ("TV", "Tuvalu")),
    "Étoiles et bandes": (
        ("US", "États-Unis"), ("LR", "Libéria"), ("MY", "Malaisie"), ("CL", "Chili"), ("CU", "Cuba"), ("UY", "Uruguay"),
        ("GR", "Grèce"), ("TG", "Togo"),
    ),
    "Bleu ciel et blanc": (
        ("AR", "Argentine"), ("IL", "Israël"), ("HN", "Honduras"), ("NI", "Nicaragua"), ("SV", "Salvador"),
        ("GT", "Guatemala"), ("SO", "Somalie"), ("BW", "Botswana"),
    ),
    "Vert, jaune et rouge": (
        ("SN", "Sénégal"), ("CM", "Cameroun"), ("GH", "Ghana"), ("ET", "Éthiopie"), ("BO", "Bolivie"), ("BJ", "Bénin"),
        ("BF", "Burkina Faso"), ("GW", "Guinée-Bissau"),
    ),
    "Vert et jaune": (
        ("BR", "Brésil"), ("JM", "Jamaïque"), ("ZA", "Afrique du Sud"), ("TZ", "Tanzanie"), ("KE", "Kenya"),
        ("UG", "Ouganda"), ("ZM", "Zambie"), ("CG", "Congo"),
    ),
    "Bleu et jaune": (
        ("CO", "Colombie"), ("EC", "Équateur"), ("VE", "Venezuela"), ("UA", "Ukraine"), ("KZ", "Kazakhstan"),
        ("BA", "Bosnie-Herzégovine"),
    ),
    "Rouge et jaune": (
        ("ES", "Espagne"), ("CN", "Chine"), ("VN", "Vietnam"), ("MK", "Macédoine du Nord"), ("KG", "Kirghizistan"),
        ("ME", "Monténégro"),
    ),
    "Rouge, blanc et bleu": (
        ("HR", "Croatie"), ("RS", "Serbie"), ("SK", "Slovaquie"), ("SI", "Slovénie"), ("CZ", "Tchéquie"),
        ("CR", "Costa Rica"), ("TH", "Thaïlande"), ("PA", "Panama"), ("DO", "République dominicaine"),
        ("PH", "Philippines"),
    ),
    "Moyen-Orient": (
        ("SA", "Arabie saoudite"), ("AE", "Émirats arabes unis"), ("QA", "Qatar"), ("KW", "Koweït"), ("JO", "Jordanie"),
        ("IQ", "Irak"), ("SY", "Syrie"), ("IR", "Iran"), ("LB", "Liban"), ("OM", "Oman"), ("BH", "Bahreïn"),
    ),
    "Asie": (
        ("IN", "Inde"), ("KR", "Corée du Sud"), ("KP", "Corée du Nord"), ("NP", "Népal"), ("BD", "Bangladesh"),
        ("LK", "Sri Lanka"), ("MN", "Mongolie"), ("KH", "Cambodge"), ("LA", "Laos"),
    ),
}

COUNTRIES: tuple[Country, ...] = tuple(
    Country(code=code, name=name, family=family) for family, members in _FAMILIES.items() for code, name in members
)
COUNTRIES_BY_CODE: dict[str, Country] = {country.code: country for country in COUNTRIES}


def pick_round(used_codes: list[str], rng: random.Random | None = None) -> tuple[Country, list[str], bool]:
    """Un pays inédit et sa série de drapeaux : surtout des sosies, le bon jamais en premier.

    Renvoie (pays, drapeaux, catalogue_recommencé).
    """
    rng = rng or _SYSTEM_RANDOM
    fresh = [country for country in COUNTRIES if country.code not in used_codes]
    restarted = not fresh
    target = rng.choice(fresh or COUNTRIES)
    lookalikes = [country.code for country in COUNTRIES if country.family == target.family and country is not target]
    decoys = rng.sample(lookalikes, min(LOOKALIKES_PER_ROUND, len(lookalikes)))
    others = [country.code for country in COUNTRIES if country is not target and country.code not in decoys]
    decoys += rng.sample(others, FLAGS_PER_ROUND - 1 - len(decoys))
    rng.shuffle(decoys)
    decoys.insert(rng.randint(1, len(decoys)), target.code)
    return target, decoys, restarted
