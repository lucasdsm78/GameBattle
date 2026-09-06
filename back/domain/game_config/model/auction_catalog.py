from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True, slots=True)
class AuctionTheme:
    id: str
    prompt: str
    answers: tuple[str, ...]


AUCTION_THEMES: tuple[AuctionTheme, ...] = (
    AuctionTheme("countries-a", "Citez des pays qui commencent par la lettre A", ("Afghanistan", "Afrique du Sud", "Albanie", "Algérie", "Allemagne", "Andorre", "Angola", "Antigua-et-Barbuda", "Arabie saoudite", "Argentine", "Arménie", "Australie", "Autriche", "Azerbaïdjan")),
    AuctionTheme("countries-b", "Citez des pays qui commencent par la lettre B", ("Bahamas", "Bahreïn", "Bangladesh", "Barbade", "Belgique", "Belize", "Bénin", "Bhoutan", "Biélorussie", "Birmanie", "Bolivie", "Bosnie-Herzégovine", "Botswana", "Brésil", "Brunei", "Bulgarie", "Burkina Faso", "Burundi")),
    AuctionTheme("countries-c", "Citez des pays qui commencent par la lettre C", ("Cambodge", "Cameroun", "Canada", "Cap-Vert", "Chili", "Chine", "Chypre", "Colombie", "Comores", "Congo", "Corée du Nord", "Corée du Sud", "Costa Rica", "Côte d’Ivoire", "Croatie", "Cuba")),
    AuctionTheme("european-capitals", "Citez des capitales de pays de l’Union européenne", ("Amsterdam", "Athènes", "Berlin", "Bratislava", "Bruxelles", "Bucarest", "Budapest", "Copenhague", "Dublin", "Helsinki", "La Valette", "Lisbonne", "Ljubljana", "Luxembourg", "Madrid", "Nicosie", "Paris", "Prague", "Riga", "Rome", "Sofia", "Stockholm", "Tallinn", "Varsovie", "Vienne", "Vilnius", "Zagreb")),
    AuctionTheme("french-regions", "Citez les régions administratives de France métropolitaine", ("Auvergne-Rhône-Alpes", "Bourgogne-Franche-Comté", "Bretagne", "Centre-Val de Loire", "Corse", "Grand Est", "Hauts-de-France", "Île-de-France", "Normandie", "Nouvelle-Aquitaine", "Occitanie", "Pays de la Loire", "Provence-Alpes-Côte d’Azur")),
    AuctionTheme("french-neighbours", "Citez les pays ayant une frontière terrestre avec la France métropolitaine", ("Allemagne", "Andorre", "Belgique", "Espagne", "Italie", "Luxembourg", "Monaco", "Suisse")),
    AuctionTheme("continents", "Citez les continents selon le modèle à sept continents", ("Afrique", "Amérique du Nord", "Amérique du Sud", "Antarctique", "Asie", "Europe", "Océanie")),
    AuctionTheme("oceans", "Citez les cinq océans", ("Arctique", "Atlantique", "Austral", "Indien", "Pacifique")),
    AuctionTheme("solar-planets", "Citez les planètes du Système solaire", ("Mercure", "Vénus", "Terre", "Mars", "Jupiter", "Saturne", "Uranus", "Neptune")),
    AuctionTheme("zodiac", "Citez les douze signes du zodiaque", ("Bélier", "Taureau", "Gémeaux", "Cancer", "Lion", "Vierge", "Balance", "Scorpion", "Sagittaire", "Capricorne", "Verseau", "Poissons")),
    AuctionTheme("months", "Citez les douze mois de l’année", ("Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre")),
    AuctionTheme("greek-letters", "Citez des lettres de l’alphabet grec", ("Alpha", "Bêta", "Gamma", "Delta", "Epsilon", "Zêta", "Êta", "Thêta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rhô", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Oméga")),
    AuctionTheme("chemical-elements-c", "Citez des éléments chimiques dont le symbole commence par C", ("Cadmium", "Calcium", "Californium", "Carbone", "Cérium", "Césium", "Chlore", "Chrome", "Cobalt", "Copernicium", "Cuivre", "Curium")),
    AuctionTheme("body-organs", "Citez des organes du corps humain", ("Cerveau", "Cœur", "Estomac", "Foie", "Intestin grêle", "Gros intestin", "Pancréas", "Poumons", "Reins", "Rate", "Thyroïde", "Vessie")),
    AuctionTheme("bones", "Citez des os du squelette humain", ("Crâne", "Mandibule", "Clavicule", "Omoplate", "Sternum", "Côte", "Humérus", "Radius", "Ulna", "Carpe", "Métacarpe", "Phalange", "Bassin", "Fémur", "Rotule", "Tibia", "Fibula", "Tarse", "Métatarse", "Vertèbre")),
    AuctionTheme("animals-c", "Citez des animaux qui commencent par la lettre C", ("Cachalot", "Caïman", "Canard", "Caribou", "Castor", "Cerf", "Chacal", "Chameau", "Chamois", "Chat", "Chauve-souris", "Chenille", "Cheval", "Chèvre", "Chien", "Chimpanzé", "Chouette", "Cigale", "Cigogne", "Cobra", "Coccinelle", "Cochon", "Colibri", "Coq", "Corbeau", "Couleuvre", "Crabe", "Crocodile", "Cygne")),
    AuctionTheme("fruits-p", "Citez des fruits qui commencent par la lettre P", ("Papaye", "Pastèque", "Pêche", "Physalis", "Pistache", "Pitaya", "Poire", "Pomelo", "Pomme", "Prune")),
    AuctionTheme("vegetables-c", "Citez des légumes qui commencent par la lettre C", ("Carotte", "Céleri", "Champignon", "Chou", "Chou-fleur", "Chou-rave", "Citrouille", "Concombre", "Courge", "Courgette", "Cresson")),
    AuctionTheme("cheeses", "Citez des fromages français", ("Abondance", "Beaufort", "Bleu d’Auvergne", "Brie de Meaux", "Camembert de Normandie", "Cantal", "Chaource", "Comté", "Crottin de Chavignol", "Époisses", "Fourme d’Ambert", "Livarot", "Maroilles", "Mimolette", "Morbier", "Munster", "Neufchâtel", "Pont-l’Évêque", "Reblochon", "Roquefort", "Saint-Nectaire", "Tomme de Savoie")),
    AuctionTheme("pasta", "Citez des formes de pâtes", ("Cannelloni", "Coquillettes", "Farfalle", "Fettuccine", "Fusilli", "Lasagnes", "Linguine", "Macaroni", "Orzo", "Penne", "Ravioli", "Rigatoni", "Spaghetti", "Tagliatelles", "Tortellini")),
    AuctionTheme("sports-ball", "Citez des sports qui se jouent avec un ballon ou une balle", ("Baseball", "Basket-ball", "Cricket", "Football", "Football américain", "Golf", "Handball", "Hockey sur gazon", "Pelote basque", "Pétanque", "Rugby", "Softball", "Squash", "Tennis", "Tennis de table", "Volley-ball", "Water-polo")),
    AuctionTheme("olympic-combat", "Citez des sports de combat présents aux Jeux olympiques d’été", ("Boxe", "Escrime", "Judo", "Lutte", "Taekwondo")),
    AuctionTheme("football-world-cup", "Citez des pays ayant remporté la Coupe du monde masculine de football", ("Allemagne", "Angleterre", "Argentine", "Brésil", "Espagne", "France", "Italie", "Uruguay")),
    AuctionTheme("disney-princesses", "Citez des héroïnes de la franchise officielle Disney Princesses", ("Ariel", "Aurore", "Belle", "Blanche-Neige", "Cendrillon", "Jasmine", "Mérida", "Mulan", "Pocahontas", "Raiponce", "Raya", "Tiana", "Vaiana")),
    AuctionTheme("harry-potter-films", "Citez les huit films de la saga Harry Potter", ("Harry Potter à l’école des sorciers", "Harry Potter et la Chambre des secrets", "Harry Potter et le Prisonnier d’Azkaban", "Harry Potter et la Coupe de feu", "Harry Potter et l’Ordre du Phénix", "Harry Potter et le Prince de sang-mêlé", "Harry Potter et les Reliques de la Mort – partie 1", "Harry Potter et les Reliques de la Mort – partie 2")),
    AuctionTheme("bond-actors", "Citez les acteurs ayant incarné James Bond dans les films officiels EON", ("Sean Connery", "George Lazenby", "Roger Moore", "Timothy Dalton", "Pierce Brosnan", "Daniel Craig")),
    AuctionTheme("musical-instruments", "Citez des instruments de musique à cordes", ("Alto", "Banjo", "Basse", "Contrebasse", "Guitare", "Harpe", "Luth", "Mandoline", "Piano", "Ukulélé", "Violon", "Violoncelle")),
    AuctionTheme("colors-c", "Citez des couleurs qui commencent par la lettre C", ("Café", "Cannelle", "Caramel", "Carmin", "Céladon", "Cerise", "Chair", "Chamois", "Chocolat", "Cinabre", "Citron", "Corail", "Crème", "Cuivre", "Cyan")),
    AuctionTheme("jobs-b", "Citez des métiers qui commencent par la lettre B", ("Barman", "Bibliothécaire", "Bijoutier", "Biologiste", "Boucher", "Boulanger", "Brasseur", "Brocanteur", "Bûcheron")),
    AuctionTheme("things-kitchen", "Citez des objets que l’on trouve couramment dans une cuisine", ("Assiette", "Balance", "Bol", "Bouilloire", "Casserole", "Couteau", "Cuillère", "Économe", "Égouttoir", "Four", "Fourchette", "Fouet", "Grille-pain", "Louche", "Micro-ondes", "Mixeur", "Moule", "Ouvre-boîte", "Passoire", "Planche à découper", "Poêle", "Réfrigérateur", "Saladier", "Spatule", "Tasse", "Verre")),
)


def pick_auction_theme(excluded_ids: list[str] | set[str] | None = None) -> AuctionTheme:
    excluded = set(excluded_ids or ())
    available = [theme for theme in AUCTION_THEMES if theme.id not in excluded]
    if not available:
        available = list(AUCTION_THEMES)
    return random.choice(available)
