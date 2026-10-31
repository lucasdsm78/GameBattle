# GameBattle

Monorepo pour une plateforme multi-jeux orientée plateau / animation live, avec :

- un **backend FastAPI**
- une **app mobile React Native** pour le présentateur
- une **app React web** affichée sur l'écran principal

Le backend suit une architecture DDD inspirée de `BetLeague`.

---

## État actuel du projet

Cette version fournit un moteur multi-jeux synchronisé : **Blindtest**, **Stop Chrono**,
**Culture générale**, **La Bombe**, **Mémoire en chaîne**, **Les 7 différences**, **L’Enchère**,
**Le mot interdit**, **Le mot qui disparaît**, **Calcul flash**, **Le bon drapeau** et **Une famille en or**.

### Déjà implémenté

- vraie persistance base de données via **SQLAlchemy async**
- configuration de partie simplifiée
- équipes configurables
- touches buzzer configurables par équipe
- manches blindtest configurables
- mode **ordre aléatoire** des manches
- synchronisation temps réel via **WebSocket**
- import réel de playlist **Spotify publique** via l'API Spotify
- lecteur preview intégré dans l'app mobile (play / pause / reprise / stop)
- synchronisation fine de la lecture blindtest (état, position, durée)
- fallback d'ouverture directe de la piste dans Spotify quand aucune preview n'est disponible
- authentification utilisateur Spotify sur mobile (PKCE)
- contrôle de lecture complète Spotify via Spotify Premium + appareil actif
- app écran blindtest live avec score, progression et révélation
- jeu **Les 7 différences** avec mémorisation de 25 secondes, premier buzz, prise de main,
  blocage temporaire après une faute, score et égalité
- app mobile de régie pour :
  - valider la partie
  - charger une playlist blindtest
  - importer une playlist Spotify
  - lancer le jeu
  - enregistrer un buzz
  - valider vrai / faux
  - passer à la musique suivante
- test buzzer au clavier sur Mac / PC
- support des buzzers USB reconnus comme clavier (HID) via mapping de touches configurable
- bridge local dédié pour buzzers USB avancés non vus comme simple clavier

### Encore perfectible / à compléter

- vrai SDK Spotify natif (aujourd'hui : Web API Spotify + appareil Spotify actif + abstraction prête pour SDK)
- auto-détection ergonomique des périphériques HID USB sans config manuelle
- catalogue extensible de puzzles pour **Les 7 différences**

---

## Structure

- `back/` : backend FastAPI (`domain` / `application` / `infrastructure` / `presentation`)
- `app-presentateur/` : app React TypeScript affichée à l'écran
- `mobile/` : app React Native Expo pour le présentateur
- `scripts/` : scripts simples de démarrage et de validation

---

## Architecture backend

Le backend suit l'architecture DDD décrite dans
[Implementing Domain-Driven Design with FastAPI](https://medium.com/delivus/implementing-domain-driven-design-with-fastapi-6aed788779af).
Chaque couche ne dépend que des couches internes (vérifié par `tests/test_architecture.py`) :

```text
back/
├── domain/                  # Métier pur, un dossier par domaine
│   ├── shared/              # Noyau partagé : GameState, DomainEvent, buzz et réponse jugée,
│   │                        # questions de culture (Culture + Mémoire), scores, horloge
│   ├── game_night/          # La soirée : racine d'agrégat GameConfig, session, réglages, registre des jeux,
│   │                        # séquence des manches, dépôt (repositories/) et événements de soirée
│   ├── forbidden_word/      # models/ (état, carte), services/ (catalogue), events/ (un fichier par événement)
│   ├── seven_differences/   # models/, services/ (catalogue + JSON), events/
│   ├── auction/             # models/, services/ (catalogue), events/
│   ├── vanishing_word/      # models/, services/ (catalogue), events/
│   ├── flash_calc/          # models/ (état, calcul, verdict), services/ (générateur par niveau), events/
│   ├── right_flag/          # models/ (état, pays, verdict), services/ (catalogue de drapeaux), events/
│   ├── golden_family/       # models/ (état, question, tableau), services/ (catalogue), events/
│   ├── bombe/  memory/  stopchrono/   # models/, events/
│   └── blindtest/  culture/           # models/ (leurs événements sont ceux du noyau partagé)
├── application/             # Un dossier par domaine
│   ├── shared/              # CommandUseCase et GamePresenter (bases), Unit of Work, instantanés diffusés, schémas communs
│   ├── game_night/          # Soirée : configuration, lancement, manches, classement, lecture de l'état
│   │                        # et presenter de la soirée (vues régie / écran public)
│   ├── blindtest/           # Use case, schémas, service de playlist et port Spotify
│   ├── stopchrono/ culture/ bombe/ memory/ seven_differences/ auction/ forbidden_word/
│   │   vanishing_word/ flash_calc/ right_flag/ golden_family/
│   │                        # <jeu>_command_usecase.py, <jeu>_presenter.py (+ <jeu>_commands.py pour ses schémas)
│   └── use_cases.py         # GameUseCases : regroupe les use cases d'écriture
├── infrastructure/
│   ├── database/            # Moteur SQLAlchemy et tables
│   ├── repositories/        # Unit of Work, dépôt PostgreSQL, cache mémoire, mapper de persistance
│   └── extern/              # Spotify, bridge buzzers USB
├── interface/
│   ├── api/                 # Routeurs HTTP et WebSocket
│   ├── schemas/             # Schémas de réponse et enveloppe des messages WebSocket
│   ├── dependencies/        # Composition racine (container) et authentification
│   └── realtime/            # Hub WebSocket, routes et dispatcher des messages, worker des chronos
├── exceptions.py            # DomainError / ApplicationError
└── main.py                  # Application factory FastAPI
```

- Les dépendances entre modules du domaine sont vérifiées par les tests : un jeu n'importe que `shared/`,
  `shared/` n'importe aucun autre module, seule `game_night/` orchestre les jeux.
- Un jeu = un dossier `domain/<jeu>/`. Ses actions (`models/<jeu>_actions.py`) sont composées dans la racine
  d'agrégat `GameConfig`, qui ne garde que l'orchestration ; son état (`models/<jeu>_state.py`) porte ses
  règles et ses invariants. Le domaine ignore tout des clients : ni sérialisation, ni vues.
- Ce que voit chaque client est une règle de diffusion, rangée dans la couche application : chaque jeu a son
  presenter (`application/<jeu>/<jeu>_presenter.py`) qui retire les données internes de la vue régie
  (`internal_fields`), ajoute les valeurs calculées (`extras`) et masque les secrets de l'écran public
  (`display_view`). `application/game_night/game_config_presenter.py` assemble la soirée complète.
- La forme persistée est produite par l'infrastructure (`game_config_to_payload` /
  `game_config_from_payload` dans `infrastructure/repositories/game_config_mapper.py`) : l'état brut de
  l'agrégat, sans vue client ni événement.
- Chaque jeu a son use case d'écriture (`application/<jeu>/<jeu>_command_usecase.py`), avec une méthode typée par
  action (`await auction.select_bid(command)`). La classe de base `CommandUseCase` applique la
  transition sous verrou, persiste puis diffuse ; une action sans effet n'écrit ni ne diffuse rien.
- Les routes HTTP appellent directement ces méthodes. Côté WebSocket, `interface/realtime/routes.py`
  associe chaque message à sa méthode, avec son schéma et les rôles autorisés.
- Ajouter une action = une méthode sur l'état du jeu, une méthode sur `GameConfig`, une méthode sur le
  use case et, si elle est pilotée en WebSocket, une ligne dans `interface/realtime/routes.py`.
- Les modèles du domaine sont des dataclasses (plus rapides et sans dépendance) ; Pydantic est réservé
  aux frontières (`application/<domaine>/<domaine>_commands.py`, `interface/schemas/`).

### Événements de domaine et Unit of Work

- Chaque transition produit des **événements de domaine** (`domain/<domaine>/events/<événement>.py`) : chaque jeu décrit ce
  qui s'est passé dans `events_since`, l'agrégat y ajoute l'orchestration (début et fin de manche, fin
  de soirée, révélation du classement). Ils s'accumulent dans `GameConfig.pending_events`, ne sont
  jamais persistés et ne transportent aucun secret.
- L'**Unit of Work** (`application/shared/unit_of_work.py`, implémentée dans
  `infrastructure/repositories/unit_of_work.py`) encadre chaque commande : transaction exclusive,
  `add()` puis `commit()` qui persiste l'agrégat et remet ses événements ; sans `commit()` (ou sur
  exception), rien n'est écrit.
- Les événements ne sont publiés qu'après une écriture réussie, avec le nouvel état :
  `{"type": "game.config.updated", "payload": {...}, "events": [{"type": "forbidden_word.word_found", "team": "Rouges", "word": "Paris"}]}`.
  Un client lent peut sauter des états intermédiaires, mais jamais d'événement : idéal pour déclencher
  animations et sons sur l'écran public.

### Sécurité

- Toutes les écritures HTTP exigent l'en-tête `X-GameBattle-Controller-Token` ; le WebSocket exige
  le jeton du rôle (`controller` ou `display`), comparé en temps constant.
- L'écran public ne peut déclencher que les buzzers, les chronos et l'envoi du jeton Spotify ; il ne
  reçoit jamais les réponses, mots secrets ni descriptions de différences.
- Messages WebSocket limités à 64 Ko, débit limité par connexion, entrées validées strictement.
- Les jetons passés en query string sont masqués dans les logs uvicorn.
- L'API tourne en un seul processus (verrou, cache et hub en mémoire) : ne pas lancer plusieurs workers.

---

## Configuration d'environnement

### Backend

Copier `back/.env.example` vers `back/.env`.

Variables principales :

- `GAMEBATTLE_CONTROLLER_TOKEN`
- `GAMEBATTLE_DISPLAY_TOKEN`
- `GAMEBATTLE_HARDWARE_TOKEN`
- `GAMEBATTLE_ALLOWED_ORIGINS`
- `GAMEBATTLE_DATABASE_URL`
- `GAMEBATTLE_BLINDTEST_PLAYLIST_URL` (playlist importée automatiquement en blindtest)
- `PEXELS_API_KEY` pour rechercher automatiquement les photos sources
- `OPENAI_API_KEY` pour analyser et retoucher les objets réels

Exemple PostgreSQL local :

```dotenv
GAMEBATTLE_DATABASE_URL=postgresql+asyncpg://gamebattle:gamebattle@localhost:5432/gamebattle
```

### App écran React

Copier `app-presentateur/.env.example` vers `app-presentateur/.env`.

```dotenv
VITE_GAMEBATTLE_WS_URL=ws://localhost:8000
VITE_GAMEBATTLE_DISPLAY_TOKEN=change-me-display
```

### Mobile Expo

Configurer `mobile/app.json` dans `expo.extra` :

- `backendWsUrl`
- `backendHttpUrl`
- `controllerToken`
- `spotifyClientId`
- `spotifyRedirectScheme`

Exemple :

```json
{
  "spotifyClientId": "ton-client-id-spotify",
  "spotifyRedirectScheme": "gamebattlecontroller"
}
```

Dans le dashboard Spotify Developer, ajoute aussi ce redirect URI :

```text
gamebattlecontroller://spotify-auth
```

---

## Démarrage rapide

### Backend

```bash
cd /Users/lucasdasilvamarques/GameBattle
bash scripts/dev-back.sh
```

### Web écran

```bash
cd /Users/lucasdasilvamarques/GameBattle
bash scripts/dev-web.sh
```

### Mobile

```bash
cd /Users/lucasdasilvamarques/GameBattle
bash scripts/dev-mobile.sh
```

Aujourd'hui, l'app mobile sait :

- lire une `preview_url` directement dans l'app
- synchroniser play / pause / reprise / stop avec le backend
- ouvrir la piste dans Spotify si la preview n'est pas disponible
- connecter un utilisateur Spotify
- piloter la lecture complète via Spotify Web API sur un appareil Spotify actif

Demain, la même abstraction pourra accueillir un vrai provider Spotify SDK natif.

> Note : la lecture complète Spotify actuelle nécessite en pratique un compte **Spotify Premium** et un appareil Spotify actif (téléphone, desktop Spotify, enceinte Connect, etc.).

### Bridge buzzers USB avancés

```bash
cd /Users/lucasdasilvamarques/GameBattle
GAMEBATTLE_HARDWARE_TOKEN=change-me-hardware bash scripts/dev-buzzers.sh
```

Le bridge lit les périphériques HID définis dans `scripts/hardware-buzzers.example.json` et pousse les buzz vers `POST /api/hardware/buzzer-events`.

---

## Vérification complète

```bash
cd /Users/lucasdasilvamarques/GameBattle
bash scripts/check-all.sh
```

Ce script lance :

- les tests backend
- le build web
- la vérification TypeScript mobile

---

## Contrôles clavier / buzzers USB

Sur l'app écran React, chaque équipe utilise la touche configurée depuis l'app mobile.

Par défaut :

- `1` → équipe 1
- `2` → équipe 2
- `3` → équipe 3
- `4` → équipe 4
- `5` → équipe 5
- `6` → équipe 6

Tu peux aussi mapper des touches comme `A`, `L`, `Space`, `Enter`, `ArrowUp`, etc.
Si ton buzzer USB agit comme un clavier, il suffit d'assigner la touche qu'il émet à l'équipe correspondante.

Pour **Les 7 différences**, le présentateur démarre l’observation depuis le mobile. L’écran public
affiche l’image originale pendant 25 secondes puis passe automatiquement à l’image modifiée. Le
premier buzzer valide prend la main. Le présentateur sélectionne ensuite une différence correcte sur
le mobile, ou choisit « Mauvaise réponse » pour libérer la main et bloquer temporairement l’équipe
fautive. Les descriptions des différences ne sont jamais envoyées à l’écran public.

Pour **Stop Chrono**, la manche se joue en 3 tours, avec une nouvelle cible à chaque tour, de plus en plus
longue (7 à 12 s, puis 13 à 18 s, puis 19 à 25 s). Chaque équipe démarre puis arrête le chrono à l’aveugle ;
les écarts à la cible s’additionnent et la plus petite erreur totale remporte la manche. À chaque tour,
l’équipe qui commence change, pour que personne ne joue toujours en dernier.

Pour **Le mot interdit**, chaque équipe joue une minute, dans un ordre de passage tiré au sort.
Le présentateur passe le téléphone à l’orateur de l’équipe, qui lance le chrono : l’app mobile
affiche le mot à faire deviner et ses 3 à 5 mots interdits. Quand son équipe trouve, l’orateur appuie
sur **TROUVÉ** (ou **Volume +**) ; **Passer** (ou **Volume −**) change de mot sans point. Le chrono est
arbitré par le serveur, l’écran public n’affiche jamais le mot en cours (seulement l’équipe, le temps
et les mots déjà trouvés) et l’équipe qui a fait deviner le plus de mots remporte la manche. En cas d’égalité en tête, les équipes
concernées rejouent 20 secondes chacune (mort subite), autant de fois qu’il le faut pour les départager. L’écran
du téléphone reste allumé pendant le tour. Le catalogue de cartes se trouve dans
`back/domain/forbidden_word/services/forbidden_word_catalog.py`.

Pour **Le mot qui disparaît**, une liste de 8 mots s’affiche sur l’écran et sur le mobile pendant
7 secondes, puis le serveur fait disparaître un mot. L’écran public montre les 7 mots restants,
remélangés, sans jamais recevoir le mot disparu ; la régie le voit mis en évidence. La première équipe
qui buzze prend la main, le présentateur valide **TROUVÉ** (+1, ou Volume +) ou **FAUX** (Volume −) :
une équipe qui se trompe ne peut plus buzzer sur cette liste. Le mot est ensuite révélé et le
présentateur lance la liste suivante. La première équipe à 5 mots trouvés remporte la manche. Le
catalogue se trouve dans `back/domain/vanishing_word/services/vanishing_word_catalog.py`.

Pour **Calcul flash**, aucun présentateur n’est nécessaire : la régie lance le défilement et le serveur
arbitre tout. Des calculs (« 7 × 8 = 54 ») défilent sur l’écran public ; les équipes buzzent uniquement
quand le résultat affiché est juste. Buzz juste : +1 ; buzz faux : −1, sans jamais descendre sous 0.
Chaque buzz affiche un retour d’1,5 s (avec la correction si c’était faux), puis le défilement reprend
sur un nouveau calcul ; un calcul sans buzz passe tout seul. Tous les 6 calculs, le niveau monte (5
niveaux, de 4,5 s à 2,6 s par calcul) : additions et tables simples, puis soustractions, tables
complètes, divisions et 2 chiffres × 1 chiffre. Les faux résultats sont crédibles (±1, ±2, ligne de
table voisine, chiffres inversés). Le résultat exact n’est jamais envoyé aux clients avant un buzz, et un
buzz reçu dans les 250 ms qui suivent l’apparition d’un calcul (réflexe sur le précédent) est ignoré. La
régie peut mettre en pause. La première équipe à 5 points remporte la manche. Le générateur se trouve
dans `back/domain/flash_calc/services/flash_calc_generator.py`.

Pour **Le bon drapeau**, un pays s’affiche (« Brésil ») et 7 drapeaux défilent, dont surtout des sosies
(drapeaux de la même famille : tricolores, croix nordiques, Union Jack…), le bon n’étant jamais le premier.
Les équipes buzzent sur le bon drapeau : +1 si c’est lui, −1 sinon (jamais sous 0). Après un mauvais buzz,
le défilement continue sur le même pays ; après le bon (ou s’il passe sans buzz, il est alors révélé), un
nouveau pays arrive, un peu plus vite que le précédent. La régie voit en permanence le bon drapeau ; l’écran
public ne le reçoit qu’une fois trouvé ou révélé, et la série à venir ne quitte jamais le serveur. La
première équipe à 5 points remporte la manche. Le catalogue (environ 130 pays) se trouve dans
`back/domain/right_flag/services/flag_catalog.py` ; l’écran affiche des drapeaux SVG livrés avec l’app
(`country-flag-icons`), le mobile des drapeaux emoji natifs.

Pour **Une famille en or**, la question s’affiche sur l’écran et sur le mobile, qui liste toutes les
réponses et leurs points. Face-à-face : la première équipe à buzzer répond ; si c’est la réponse la plus
citée, elle prend la main, sinon chaque équipe donne une réponse et la mieux classée prend la main. Le
présentateur touche la réponse donnée si elle figure au tableau (elle se retourne et rapporte ses points à
l’équipe qui l’a trouvée), sinon il appuie sur **FAUTE** (ou Volume −). Après 3 fautes, les autres équipes
donnent une réponse chacune et la meilleure reprend la main ; si toutes échouent, la main revient à
l’équipe fautive pour une réponse, et ainsi de suite jusqu’à une bonne réponse. La question se termine
quand le tableau est complet (ou quand le présentateur révèle les réponses restantes, sans points). La
première équipe à 300 points remporte la manche. L’écran public ne reçoit ni le texte ni les points d’une
réponse avant qu’elle soit retournée ; chaque décision du présentateur porte le numéro du tour, si bien
qu’un double appui n’est compté qu’une fois. Le catalogue (68 questions grand public, scores **estimés**,
pas issus d’un vrai sondage) se trouve dans `back/domain/golden_family/services/golden_family_catalog.py`.

Calcul flash et Le bon drapeau partagent la même mécanique « buzze seulement si… » :
`back/domain/shared/models/buzz_stream_state.py` (défilement, fenêtre de buzz, +1 / −1, retour, pause,
victoire). Un nouveau jeu de ce type n’a qu’à décrire ce qui défile. Après 15 éléments d’affilée sans
aucun buzz, le défilement se met en pause tout seul (« ⏸ Pause : personne ne joue ? ») : le serveur cesse
alors d’écrire en base et de diffuser, et la régie relance d’un appui.

### Générer automatiquement un puzzle

Le générateur transforme une image JPEG, PNG ou WebP en deux images WebP 16:9. Un modèle vision
sélectionne sept objets réels suffisamment visibles et éloignés, puis chaque objet est retouché
séparément par masque : suppression, déplacement, recoloration ou modification naturelle. Les
descriptions et coordonnées sont produites automatiquement et le puzzle est enregistré dans le
catalogue backend. Aucune flèche, forme géométrique ou vignette artificielle n’est ajoutée.

Ajouter d’abord la clé du service d’édition dans `back/.env` :

```dotenv
OPENAI_API_KEY=ta-cle-openai
```

Depuis une image locale :

```bash
cd /Users/lucasdasilvamarques/GameBattle
back/.venv/bin/python scripts/generate-seven-differences.py \
  --input "$HOME/Downloads/stade.jpg" \
  --title "Finale au stade" \
  --seed 42
```

Recherche et téléchargement automatiques depuis Pexels :

```bash
cd /Users/lucasdasilvamarques/GameBattle
back/.venv/bin/python scripts/generate-seven-differences.py \
  --pexels-query "football stadium" \
  --title "Soir de championnat" \
  --seed 42
```

`PEXELS_API_KEY` doit également être présent dans `back/.env` pour la recherche automatique. La
graine stabilise le choix de la photographie Pexels, mais une édition générative peut varier entre
deux exécutions. Les images générées sont placées dans
`app-presentateur/public/seven-differences/` et le manifeste
`back/domain/seven_differences/services/seven_differences_catalog.json` est mis à jour atomiquement. Pour
remplacer volontairement un identifiant existant, ajouter `--id mon-puzzle --replace`. Redémarrer
ensuite le backend pour charger le catalogue actualisé.

Pour Pexels, créer une clé sur <https://www.pexels.com/api/> et respecter leurs conditions
d’utilisation et d’attribution. Les images locales restent la solution recommandée pour un usage
entièrement hors ligne.

Si OpenAI retourne `429 Too Many Requests`, le générateur respecte automatiquement `Retry-After`
et effectue jusqu’à cinq tentatives avec attente progressive. Un message distinct indique si le
problème vient d’un quota ou de la facturation : dans ce cas, vérifier les crédits et les limites du
projet sur <https://platform.openai.com/settings/organization/billing> avant de relancer. Aucun
puzzle partiel n’est ajouté au catalogue lorsque l’édition échoue.

Pour un buzzer USB plus avancé qui n'émule pas un clavier, utilise le bridge local :

- fichier d'exemple : `scripts/hardware-buzzers.example.json`
- runner : `scripts/dev-buzzers.sh`
- module Python : `back/infrastructure/extern/usb_buzzer_bridge.py`

---

## Validations exécutées

Backend :

```bash
cd /Users/lucasdasilvamarques/GameBattle/back
./.venv/bin/python -m pytest -q
```

Web :

```bash
cd /Users/lucasdasilvamarques/GameBattle/app-presentateur
npm run build
```

Mobile :

```bash
cd /Users/lucasdasilvamarques/GameBattle/mobile
npx tsc --noEmit
```

Bridge USB local :

```bash
cd /Users/lucasdasilvamarques/GameBattle/back
./.venv/bin/python -m infrastructure.extern.usb_buzzer_bridge --help
```

---

## Suite recommandée

Ensuite, je recommande cet ordre :

1. **Lecture blindtest native complète** : remplacer le provider Spotify Web API par un provider SDK natif dans la même abstraction
2. **Buzzers USB avancés** : auto-détection + UI de calibration des périphériques HID
3. **Catalogue de contenus** : ajouter de nouveaux puzzles et banques de questions

