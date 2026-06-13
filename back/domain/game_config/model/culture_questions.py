from __future__ import annotations

import random
from typing import Optional

# Banque de questions de culture générale (FR). Chaque entrée : question, réponse, explication, difficulté.
# difficulté ∈ {"facile", "moyen", "difficile"}.
CULTURE_QUESTIONS: list[dict[str, str]] = [
    # --- Facile ---
    {"question": "Quelle est la capitale de la France ?", "answer": "Paris", "explanation": "Paris est la capitale de la France depuis le Moyen Âge.", "difficulty": "facile"},
    {"question": "Combien y a-t-il de jours dans une année non bissextile ?", "answer": "365", "explanation": "Une année bissextile en compte 366 (29 février).", "difficulty": "facile"},
    {"question": "De quelle couleur est le ciel par temps clair ?", "answer": "Bleu", "explanation": "La diffusion de Rayleigh disperse surtout la lumière bleue.", "difficulty": "facile"},
    {"question": "Quel animal est le meilleur ami de l'homme ?", "answer": "Le chien", "explanation": "Le chien est domestiqué depuis plus de 15 000 ans.", "difficulty": "facile"},
    {"question": "Combien de pattes a une araignée ?", "answer": "8", "explanation": "Les araignées sont des arachnides à 8 pattes, contrairement aux insectes (6).", "difficulty": "facile"},
    {"question": "Quel est le premier nombre premier ?", "answer": "2", "explanation": "2 est le seul nombre premier pair.", "difficulty": "facile"},
    {"question": "Quelle planète habitons-nous ?", "answer": "La Terre", "explanation": "La Terre est la 3e planète du système solaire.", "difficulty": "facile"},
    {"question": "Quel sport pratique-t-on à Roland-Garros ?", "answer": "Le tennis", "explanation": "Roland-Garros est le tournoi du Grand Chelem sur terre battue.", "difficulty": "facile"},
    {"question": "Combien de joueurs composent une équipe de football sur le terrain ?", "answer": "11", "explanation": "Onze joueurs par équipe, dont un gardien.", "difficulty": "facile"},
    {"question": "Quelle est la couleur obtenue en mélangeant le bleu et le jaune ?", "answer": "Le vert", "explanation": "Bleu + jaune donne du vert en synthèse soustractive.", "difficulty": "facile"},
    {"question": "Quel est l'astre qui éclaire la Terre le jour ?", "answer": "Le Soleil", "explanation": "Le Soleil est l'étoile au centre de notre système.", "difficulty": "facile"},
    {"question": "Dans quel pays se trouve la tour Eiffel ?", "answer": "La France", "explanation": "Construite à Paris pour l'Exposition universelle de 1889.", "difficulty": "facile"},
    # --- Moyen ---
    {"question": "Qui a peint la Joconde ?", "answer": "Léonard de Vinci", "explanation": "Œuvre du début du XVIe siècle, exposée au Louvre.", "difficulty": "moyen"},
    {"question": "Quel est le plus grand océan du monde ?", "answer": "L'océan Pacifique", "explanation": "Il couvre environ un tiers de la surface du globe.", "difficulty": "moyen"},
    {"question": "En quelle année a eu lieu la Révolution française ?", "answer": "1789", "explanation": "La prise de la Bastille a lieu le 14 juillet 1789.", "difficulty": "moyen"},
    {"question": "Quel gaz les plantes absorbent-elles pour la photosynthèse ?", "answer": "Le dioxyde de carbone (CO2)", "explanation": "Elles rejettent de l'oxygène en retour.", "difficulty": "moyen"},
    {"question": "Quelle est la monnaie du Japon ?", "answer": "Le yen", "explanation": "Le yen est la 3e monnaie la plus échangée au monde.", "difficulty": "moyen"},
    {"question": "Combien de côtés possède un hexagone ?", "answer": "6", "explanation": "« Hexa » signifie six en grec.", "difficulty": "moyen"},
    {"question": "Qui a écrit « Les Misérables » ?", "answer": "Victor Hugo", "explanation": "Roman publié en 1862.", "difficulty": "moyen"},
    {"question": "Quel est le plus haut sommet du monde ?", "answer": "L'Everest", "explanation": "Culmine à 8 849 m dans l'Himalaya.", "difficulty": "moyen"},
    {"question": "Quel organe pompe le sang dans le corps ?", "answer": "Le cœur", "explanation": "Il bat environ 100 000 fois par jour.", "difficulty": "moyen"},
    {"question": "Quel pays a remporté la Coupe du monde de football 2018 ?", "answer": "La France", "explanation": "Victoire 4-2 contre la Croatie en finale.", "difficulty": "moyen"},
    {"question": "Quelle est la capitale de l'Australie ?", "answer": "Canberra", "explanation": "Et non Sydney, souvent confondue.", "difficulty": "moyen"},
    {"question": "Combien de continents y a-t-il sur Terre ?", "answer": "7", "explanation": "Afrique, Amérique du Nord, Amérique du Sud, Antarctique, Asie, Europe, Océanie.", "difficulty": "moyen"},
    # --- Difficile ---
    {"question": "Quel est l'élément chimique de symbole « Au » ?", "answer": "L'or", "explanation": "De son nom latin « aurum ».", "difficulty": "difficile"},
    {"question": "En quelle année est tombé le mur de Berlin ?", "answer": "1989", "explanation": "Le 9 novembre 1989, symbole de la fin de la guerre froide.", "difficulty": "difficile"},
    {"question": "Qui a formulé la théorie de la relativité générale ?", "answer": "Albert Einstein", "explanation": "Publiée en 1915.", "difficulty": "difficile"},
    {"question": "Quelle est la plus longue rivière du monde ?", "answer": "L'Amazone (ou le Nil)", "explanation": "Le débat Amazone/Nil dépend de la méthode de mesure.", "difficulty": "difficile"},
    {"question": "Combien d'os compte le corps humain adulte ?", "answer": "206", "explanation": "Un nouveau-né en a environ 270, certains fusionnent.", "difficulty": "difficile"},
    {"question": "Quel philosophe grec fut le maître d'Alexandre le Grand ?", "answer": "Aristote", "explanation": "Aristote, élève de Platon, précepteur d'Alexandre.", "difficulty": "difficile"},
    {"question": "Quelle est la vitesse de la lumière dans le vide (ordre de grandeur) ?", "answer": "300 000 km/s", "explanation": "Précisément 299 792 458 m/s.", "difficulty": "difficile"},
    {"question": "Quel pays compte le plus d'habitants au monde ?", "answer": "L'Inde", "explanation": "L'Inde a dépassé la Chine en 2023.", "difficulty": "difficile"},
    {"question": "Qui a peint « La Nuit étoilée » ?", "answer": "Vincent van Gogh", "explanation": "Peinte en 1889 à Saint-Rémy-de-Provence.", "difficulty": "difficile"},
    {"question": "Quel est le plus petit pays du monde ?", "answer": "Le Vatican", "explanation": "Environ 44 hectares.", "difficulty": "difficile"},
    {"question": "En quelle année l'homme a-t-il marché sur la Lune pour la première fois ?", "answer": "1969", "explanation": "Mission Apollo 11, le 21 juillet 1969.", "difficulty": "difficile"},
    {"question": "Quelle est la formule chimique de l'eau ?", "answer": "H2O", "explanation": "Deux atomes d'hydrogène, un d'oxygène.", "difficulty": "difficile"},
]

CULTURE_DIFFICULTIES = {"facile", "moyen", "difficile"}


def pick_culture_questions(difficulty: str, count: int) -> list[dict[str, str]]:
    """Tire `count` questions au hasard, filtrées par difficulté ('toutes' = sans filtre)."""
    normalized = (difficulty or "toutes").strip().lower()
    pool = [q for q in CULTURE_QUESTIONS if normalized == "toutes" or q["difficulty"] == normalized]
    if not pool:
        pool = list(CULTURE_QUESTIONS)
    chosen = random.sample(pool, min(count, len(pool)))
    return [dict(q) for q in chosen]


def pick_one_culture_question(difficulty: str, exclude_questions: set[str]) -> Optional[dict[str, str]]:
    """Tire UNE question au hasard de la difficulté donnée, en évitant celles déjà posées.

    Si toutes les questions de la difficulté ont déjà été posées, on autorise la répétition.
    """
    normalized = (difficulty or "toutes").strip().lower()
    pool = [q for q in CULTURE_QUESTIONS if normalized == "toutes" or q["difficulty"] == normalized]
    if not pool:
        pool = list(CULTURE_QUESTIONS)
    available = [q for q in pool if q["question"] not in exclude_questions] or pool
    if not available:
        return None
    return dict(random.choice(available))
