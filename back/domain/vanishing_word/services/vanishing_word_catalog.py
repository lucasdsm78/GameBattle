from __future__ import annotations

import random

# Mots courts et faciles à visualiser : on retient mieux une image qu'une idée abstraite.
VANISHING_WORDS: tuple[str, ...] = (
    # Sport & paris
    "Ballon", "Stade", "Arbitre", "Sifflet", "Maillot", "Trophée", "Médaille", "Podium", "Raquette", "Filet",
    "Panier", "Penalty", "Gardien", "Coach", "Tribune", "Pari", "Cote", "Jackpot", "Ticket", "Champion",
    "Vélo", "Ski", "Surf", "Judo", "Boxe", "Golf", "Rugby", "Tennis", "Piscine", "Chrono",
    # Animaux
    "Lion", "Tigre", "Zèbre", "Girafe", "Éléphant", "Panda", "Koala", "Dauphin", "Requin", "Baleine",
    "Pingouin", "Hibou", "Aigle", "Perroquet", "Serpent", "Tortue", "Grenouille", "Lapin", "Renard", "Loup",
    "Cheval", "Vache", "Cochon", "Mouton", "Chat", "Chien", "Souris", "Abeille", "Papillon", "Escargot",
    # Cuisine
    "Pizza", "Burger", "Frites", "Crêpe", "Croissant", "Baguette", "Fromage", "Chocolat", "Glace", "Gâteau",
    "Pomme", "Banane", "Fraise", "Cerise", "Citron", "Ananas", "Carotte", "Tomate", "Popcorn", "Café",
    # Objets
    "Parapluie", "Lunettes", "Montre", "Clé", "Bougie", "Valise", "Miroir", "Ciseaux", "Téléphone", "Casque",
    "Guitare", "Piano", "Tambour", "Micro", "Caméra", "Lampe", "Échelle", "Boussole", "Bouteille", "Cadenas",
    "Chapeau", "Écharpe", "Basket", "Gant", "Sac", "Livre", "Crayon", "Gomme", "Tableau", "Horloge",
    # Lieux & nature
    "Plage", "Montagne", "Volcan", "Désert", "Forêt", "Île", "Rivière", "Cascade", "Château", "Phare",
    "Soleil", "Lune", "Étoile", "Nuage", "Orage", "Neige", "Arc-en-ciel", "Fusée", "Planète", "Comète",
    # Transports
    "Avion", "Train", "Bateau", "Voiture", "Moto", "Bus", "Taxi", "Tracteur", "Hélicoptère", "Montgolfière",
    # Personnages
    "Pirate", "Robot", "Fantôme", "Sorcière", "Dragon", "Licorne", "Chevalier", "Magicien", "Clown", "Astronaute",
)

WORDS_PER_LIST = 8


def pick_vanishing_words(excluded: list[str] | set[str]) -> tuple[list[str], bool]:
    """Tire une liste de mots jamais joués dans la manche ; recommence un cycle si le catalogue est épuisé.

    Renvoie la liste et `True` si un nouveau cycle a commencé.
    """
    excluded_set = set(excluded)
    available = [word for word in VANISHING_WORDS if word not in excluded_set]
    restarted = len(available) < WORDS_PER_LIST
    pool = list(VANISHING_WORDS) if restarted else available
    return random.sample(pool, WORDS_PER_LIST), restarted
