from __future__ import annotations

import random

from domain.golden_family.models.family_question import FamilyAnswer, FamilyQuestion

# Scores estimés (pas un vrai sondage) : de la réponse la plus citée à la moins citée, 100 au plus.
_CATALOG: tuple[tuple[str, str, tuple[tuple[str, int], ...]], ...] = (
    # Vie quotidienne, maison, loisirs, nature et culture : des questions que toute la famille peut jouer.
    ("dimanche-matin", "Citez une chose que l’on fait le dimanche matin", (
        ("Grasse matinée", 35), ("Petit-déjeuner", 20), ("Marché", 14), ("Footing", 10), ("Messe", 8),
        ("Ménage", 6),
    )),
    ("fruit-rouge", "Citez un fruit rouge", (
        ("Fraise", 40), ("Framboise", 22), ("Cerise", 18), ("Groseille", 8), ("Pomme", 5), ("Grenade", 3),
    )),
    ("animal-maison", "Citez un animal que l’on peut avoir à la maison", (
        ("Chat", 38), ("Chien", 35), ("Poisson rouge", 9), ("Lapin", 7), ("Hamster", 5), ("Oiseau", 3),
    )),
    ("pizza", "Citez quelque chose que l’on met sur une pizza", (
        ("Fromage", 30), ("Jambon", 20), ("Tomate", 18), ("Champignons", 12), ("Chorizo", 7), ("Olives", 6),
        ("Ananas", 3),
    )),
    ("piece-maison", "Citez une pièce de la maison", (
        ("Cuisine", 30), ("Salon", 25), ("Chambre", 22), ("Salle de bain", 12), ("Toilettes", 5), ("Garage", 3),
    )),
    ("plage", "Citez quelque chose que l’on emporte à la plage", (
        ("Serviette", 30), ("Crème solaire", 25), ("Parasol", 15), ("Maillot de bain", 12),
        ("Lunettes de soleil", 8), ("Ballon", 5),
    )),
    ("uniforme", "Citez un métier où l’on porte un uniforme", (
        ("Policier", 35), ("Pompier", 25), ("Militaire", 15), ("Infirmier", 10), ("Pilote", 7), ("Facteur", 4),
    )),
    ("sonne", "Citez quelque chose qui sonne", (
        ("Téléphone", 40), ("Réveil", 25), ("Sonnette", 15), ("Cloche", 10), ("Alarme", 6),
    )),
    ("legume-vert", "Citez un légume vert", (
        ("Haricot vert", 25), ("Brocoli", 22), ("Salade", 18), ("Courgette", 14), ("Épinards", 10),
        ("Petits pois", 7),
    )),
    ("avant-dormir", "Citez une chose que l’on fait avant de se coucher", (
        ("Se brosser les dents", 40), ("Lire", 20), ("Regarder son téléphone", 15), ("Mettre son pyjama", 10),
        ("Régler le réveil", 8), ("Prendre une douche", 5),
    )),
    ("dessert-francais", "Citez un dessert français", (
        ("Crème brûlée", 22), ("Tarte Tatin", 18), ("Mousse au chocolat", 16), ("Éclair", 12), ("Crêpe", 10),
        ("Macaron", 8), ("Île flottante", 6),
    )),
    ("transport", "Citez un moyen de transport", (
        ("Voiture", 35), ("Train", 20), ("Avion", 15), ("Vélo", 12), ("Bus", 8), ("Métro", 6),
    )),
    ("trousse", "Citez une chose que l’on trouve dans une trousse", (
        ("Stylo", 35), ("Crayon", 20), ("Gomme", 15), ("Règle", 10), ("Taille-crayon", 8), ("Ciseaux", 5),
        ("Colle", 4),
    )),
    ("super-heros", "Citez un super-héros", (
        ("Spider-Man", 30), ("Superman", 25), ("Batman", 22), ("Iron Man", 10), ("Wonder Woman", 6), ("Hulk", 5),
    )),
    ("jaune", "Citez quelque chose de jaune", (
        ("Soleil", 35), ("Banane", 25), ("Citron", 15), ("Poussin", 10), ("Canari", 6), ("La Poste", 5),
    )),
    ("instrument", "Citez un instrument de musique", (
        ("Piano", 35), ("Guitare", 30), ("Violon", 12), ("Batterie", 10), ("Flûte", 6), ("Trompette", 4),
    )),
    ("frigo", "Citez une chose que l’on trouve dans un frigo", (
        ("Lait", 25), ("Beurre", 20), ("Fromage", 18), ("Yaourts", 15), ("Œufs", 10), ("Légumes", 7),
    )),
    ("jeu-societe", "Citez un jeu de société", (
        ("Monopoly", 35), ("Scrabble", 18), ("Uno", 15), ("Trivial Pursuit", 10), ("Cluedo", 8), ("Dobble", 6),
        ("Échecs", 4),
    )),
    ("retard", "Citez une raison d’être en retard", (
        ("Embouteillages", 35), ("Réveil pas sonné", 25), ("Grève", 12), ("Panne", 10), ("Enfants", 8),
        ("Oubli", 5),
    )),
    ("fete", "Citez quelque chose que l’on fête", (
        ("Anniversaire", 40), ("Noël", 25), ("Nouvel an", 15), ("Mariage", 10), ("Diplôme", 5),
        ("Fête des mères", 3),
    )),
    ("vacances", "Citez une chose que l’on fait en vacances", (
        ("Se reposer", 25), ("Se baigner", 22), ("Visiter", 18), ("Bronzer", 15), ("Aller au restaurant", 10),
        ("Faire la fête", 6),
    )),
    ("dessin-anime", "Citez un dessin animé culte", (
        ("Le Roi lion", 25), ("Dragon Ball", 15), ("Les Simpson", 15), ("Pokémon", 12), ("Astérix", 10),
        ("Tom et Jerry", 8), ("Bob l’éponge", 6),
    )),
    ("boisson-chaude", "Citez une boisson chaude", (
        ("Café", 45), ("Thé", 30), ("Chocolat chaud", 15), ("Infusion", 5), ("Vin chaud", 3),
    )),
    ("francophone", "Citez un pays où l’on parle français", (
        ("France", 35), ("Belgique", 25), ("Suisse", 18), ("Canada", 12), ("Sénégal", 4), ("Luxembourg", 3),
    )),
    ("roues", "Citez quelque chose qui a des roues", (
        ("Voiture", 35), ("Vélo", 25), ("Camion", 12), ("Poussette", 8), ("Skateboard", 7), ("Valise", 6),
        ("Train", 4),
    )),
    ("objet-perdu", "Citez un objet que l’on perd souvent", (
        ("Clés", 45), ("Téléphone", 18), ("Lunettes", 12), ("Télécommande", 10), ("Chaussettes", 8),
        ("Portefeuille", 4),
    )),
    ("pique", "Citez quelque chose qui pique", (
        ("Ortie", 20), ("Hérisson", 18), ("Abeille", 17), ("Piment", 15), ("Cactus", 14), ("Moustique", 8),
        ("Aiguille", 5),
    )),
    ("crepe", "Citez un ingrédient de la pâte à crêpes", (
        ("Farine", 30), ("Œufs", 28), ("Lait", 25), ("Sucre", 8), ("Beurre", 5),
    )),
    ("reveil", "Citez une chose que l’on fait au réveil", (
        ("Boire un café", 22), ("S’étirer", 22), ("Regarder son téléphone", 18), ("Aller aux toilettes", 14),
        ("Se doucher", 12), ("Bâiller", 6),
    )),
    ("ferme", "Citez un animal de la ferme", (
        ("Vache", 30), ("Cochon", 22), ("Poule", 20), ("Mouton", 12), ("Cheval", 8), ("Chèvre", 5),
    )),
    ("queue", "Citez un endroit où l’on fait la queue", (
        ("Supermarché", 35), ("Poste", 18), ("Parc d’attractions", 15), ("Boulangerie", 10), ("Médecin", 8),
        ("Toilettes", 6), ("Aéroport", 4),
    )),
    ("pas-preter", "Citez une chose que l’on ne prête jamais", (
        ("Brosse à dents", 40), ("Voiture", 20), ("Argent", 15), ("Son amoureux", 10), ("Téléphone", 8),
        ("Son lit", 3),
    )),
    ("froid", "Citez quelque chose de froid", (
        ("Glace", 35), ("Neige", 25), ("Frigo", 15), ("Hiver", 10), ("Pôle Nord", 8), ("Pingouin", 4),
    )),
    ("plat-hiver", "Citez un plat que l’on mange en hiver", (
        ("Raclette", 35), ("Fondue", 22), ("Pot-au-feu", 12), ("Tartiflette", 12), ("Soupe", 10),
        ("Choucroute", 5),
    )),
    ("conte", "Citez un personnage de conte", (
        ("Cendrillon", 25), ("Blanche-Neige", 22), ("Le Petit Chaperon rouge", 20),
        ("La Belle au bois dormant", 10), ("Pinocchio", 8), ("Le Petit Poucet", 6),
    )),
    ("reseau-social", "Citez un réseau social", (
        ("Instagram", 30), ("Facebook", 25), ("TikTok", 22), ("Snapchat", 10), ("X (Twitter)", 6), ("LinkedIn", 4),
    )),
    ("vole", "Citez quelque chose qui vole", (
        ("Oiseau", 40), ("Avion", 30), ("Hélicoptère", 8), ("Papillon", 8), ("Cerf-volant", 5), ("Fusée", 4),
    )),
    ("voiture-francaise", "Citez une marque de voiture française", (
        ("Peugeot", 40), ("Renault", 35), ("Citroën", 18), ("Bugatti", 3), ("Alpine", 2),
    )),
    ("mariage", "Citez une chose que l’on fait à un mariage", (
        ("Danser", 30), ("Manger", 20), ("Pleurer", 12), ("Trinquer", 12), ("Lancer le bouquet", 10),
        ("Prendre des photos", 8), ("Dire oui", 5),
    )),
    ("sandwich", "Citez quelque chose que l’on met dans un sandwich", (
        ("Jambon", 30), ("Beurre", 22), ("Fromage", 18), ("Salade", 12), ("Tomate", 8), ("Mayonnaise", 6),
    )),
    ("cadeaux", "Citez une fête où l’on offre des cadeaux", (
        ("Noël", 50), ("Anniversaire", 30), ("Fête des mères", 8), ("Saint-Valentin", 6), ("Fête des pères", 3),
    )),
    ("gagner-loto", "Citez ce que l’on fait quand on gagne au loto", (
        ("Acheter une maison", 25), ("Crier", 20), ("Voyager", 18), ("Démissionner", 15), ("Faire la fête", 10),
        ("Aider sa famille", 8),
    )),
    ("douche", "Citez quelque chose que l’on fait sous la douche", (
        ("Se laver", 45), ("Chanter", 20), ("Réfléchir", 18), ("Se raser", 9), ("Pleurer", 6),
    )),
    ("metier-reve", "Citez un métier dont rêvent les enfants", (
        ("Pompier", 30), ("Vétérinaire", 20), ("Footballeur", 15), ("Astronaute", 12), ("Policier", 10),
        ("Maîtresse d’école", 6),
    )),
    ("salle-de-bain", "Citez quelque chose que l’on trouve dans une salle de bain", (
        ("Brosse à dents", 28), ("Savon", 22), ("Serviette", 18), ("Miroir", 14), ("Shampoing", 10),
        ("Baignoire", 6),
    )),
    ("bureau", "Citez un objet que l’on trouve sur un bureau", (
        ("Ordinateur", 35), ("Stylo", 22), ("Lampe", 15), ("Téléphone", 12), ("Agenda", 8), ("Tasse", 5),
    )),
    ("ustensile", "Citez un ustensile de cuisine", (
        ("Couteau", 28), ("Casserole", 22), ("Poêle", 18), ("Cuillère en bois", 12), ("Fouet", 10), ("Louche", 6),
    )),
    ("fruit-exotique", "Citez un fruit exotique", (
        ("Ananas", 30), ("Mangue", 25), ("Banane", 15), ("Noix de coco", 12), ("Kiwi", 8), ("Papaye", 5),
    )),
    ("savane", "Citez un animal de la savane", (
        ("Lion", 35), ("Girafe", 22), ("Éléphant", 18), ("Zèbre", 12), ("Hyène", 5), ("Rhinocéros", 4),
    )),
    ("chuchoter", "Citez un endroit où l’on doit chuchoter", (
        ("Bibliothèque", 40), ("Église", 22), ("Hôpital", 12), ("Cinéma", 10), ("Musée", 8),
        ("Chambre d’un bébé", 5),
    )),
    ("oubli-vacances", "Citez une chose que l’on oublie en partant en vacances", (
        ("Brosse à dents", 30), ("Chargeur", 25), ("Maillot de bain", 12), ("Crème solaire", 10), ("Passeport", 10),
        ("Lunettes de soleil", 6),
    )),
    ("telephone", "Citez un mot que l’on dit au téléphone", (
        ("Allô", 50), ("Au revoir", 18), ("Oui", 10), ("Tu m’entends ?", 8), ("Bisous", 6), ("Attends", 4),
    )),
    ("excuse-travail", "Citez une excuse pour ne pas aller travailler", (
        ("Être malade", 45), ("Panne de voiture", 18), ("Enfant malade", 12), ("Grève", 10),
        ("Rendez-vous médical", 8), ("Dégât des eaux", 4),
    )),
    ("pluie", "Citez quelque chose que l’on fait quand il pleut", (
        ("Prendre un parapluie", 30), ("Rester à la maison", 25), ("Regarder un film", 15),
        ("Sauter dans les flaques", 10), ("Lire", 8), ("Dormir", 6),
    )),
    ("arc-en-ciel", "Citez une couleur de l’arc-en-ciel", (
        ("Rouge", 25), ("Bleu", 20), ("Jaune", 18), ("Vert", 15), ("Orange", 10), ("Violet", 7), ("Indigo", 3),
    )),
    ("disney", "Citez un personnage de Disney", (
        ("Mickey", 35), ("Blanche-Neige", 15), ("Cendrillon", 12), ("Simba", 12), ("Elsa", 10), ("Donald", 8),
        ("Ariel", 5),
    )),
    ("cinema", "Citez une chose que l’on fait au cinéma", (
        ("Regarder un film", 30), ("Manger du pop-corn", 30), ("Dormir", 10), ("Pleurer", 10), ("Rire", 8),
        ("Chuchoter", 5),
    )),
    ("peur-enfants", "Citez quelque chose qui fait peur aux enfants", (
        ("Le noir", 35), ("Les monstres", 20), ("Les araignées", 15), ("Le loup", 12), ("Les clowns", 8),
        ("L’orage", 6),
    )),
    ("camping", "Citez un objet que l’on emporte en camping", (
        ("Tente", 40), ("Sac de couchage", 22), ("Lampe de poche", 15), ("Réchaud", 10), ("Glacière", 6),
        ("Matelas gonflable", 4),
    )),
    ("noel", "Citez une chose que l’on fait à Noël", (
        ("Ouvrir les cadeaux", 35), ("Décorer le sapin", 22), ("Faire un grand repas", 18), ("Chanter", 8),
        ("Aller à la messe", 8), ("Voir la famille", 6),
    )),
    ("enfants-detestent", "Citez un aliment que les enfants détestent", (
        ("Épinards", 30), ("Brocoli", 22), ("Endives", 15), ("Choux de Bruxelles", 15), ("Poisson", 8), ("Foie", 5),
    )),
    ("destination-reve", "Citez une destination de rêve", (
        ("Maldives", 25), ("Bali", 18), ("New York", 15), ("Japon", 14), ("Bora-Bora", 12), ("Australie", 8),
    )),
    ("recharge", "Citez quelque chose qui se recharge", (
        ("Téléphone", 50), ("Voiture électrique", 15), ("Ordinateur", 12), ("Batterie", 10), ("Montre", 6),
        ("Brosse à dents électrique", 4),
    )),
    ("sac-a-main", "Citez une chose que l’on met dans un sac à main", (
        ("Portefeuille", 30), ("Clés", 22), ("Téléphone", 18), ("Maquillage", 12), ("Mouchoirs", 8), ("Lunettes", 5),
    )),
    ("parc-attractions", "Citez une chose que l’on fait dans un parc d’attractions", (
        ("Faire des manèges", 40), ("Faire la queue", 25), ("Crier", 12), ("Manger une barbe à papa", 10),
        ("Prendre des photos", 6), ("Avoir peur", 4),
    )),
    ("insecte", "Citez un insecte", (
        ("Mouche", 30), ("Abeille", 20), ("Fourmi", 18), ("Moustique", 15), ("Papillon", 8), ("Coccinelle", 6),
    )),
    ("bonjour", "Citez une façon de dire bonjour", (
        ("Salut", 40), ("Coucou", 25), ("Hello", 15), ("Bonsoir", 8), ("Yo", 5), ("Wesh", 3),
    )),
    ("plat-italien", "Citez un plat italien", (
        ("Pizza", 35), ("Lasagnes", 25), ("Spaghetti bolognaise", 15), ("Risotto", 10), ("Tiramisu", 8),
        ("Carbonara", 4),
    )),
)

FAMILY_QUESTIONS: tuple[FamilyQuestion, ...] = tuple(
    FamilyQuestion(id=question_id, text=text, answers=[FamilyAnswer(text=answer, points=points) for answer, points in answers])
    for question_id, text, answers in _CATALOG
)
FAMILY_QUESTIONS_BY_ID: dict[str, FamilyQuestion] = {question.id: question for question in FAMILY_QUESTIONS}


def pick_family_question(used_ids: list[str]) -> tuple[FamilyQuestion, bool]:
    """Une question inédite de la manche ; renvoie (question, catalogue_recommencé)."""
    fresh = [question for question in FAMILY_QUESTIONS if question.id not in used_ids]
    return random.choice(fresh or FAMILY_QUESTIONS), not fresh
