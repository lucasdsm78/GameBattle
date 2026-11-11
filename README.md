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
**Le mot interdit**, **Le mot qui disparaît**, **Calcul flash**, **Le bon drapeau**, **Une famille en or** et
**Le juste prix**.

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
- `app-joueur/` : app React TypeScript des joueurs en ligne (compte, création et entrée dans un salon, salle d'attente en direct)
- `mobile/` : app React Native Expo pour le présentateur
- `scripts/` : scripts simples de démarrage et de validation

---

## Architecture backend

Le backend suit l'architecture DDD décrite dans
[Implementing Domain-Driven Design with FastAPI](https://medium.com/delivus/implementing-domain-driven-design-with-fastapi-6aed788779af).
Chaque couche ne dépend que des couches internes (vérifié par `tests/architecture/`) :

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
│   ├── fair_price/          # models/ (état, objet, gamme, résultat), services/ (catalogue), events/
│   ├── bombe/  memory/  stopchrono/   # models/, events/
│   └── blindtest/  culture/           # models/ (leurs événements sont ceux du noyau partagé)
├── application/             # Un dossier par domaine
│   ├── shared/              # CommandUseCase et GamePresenter (bases), Unit of Work, instantanés diffusés, schémas communs
│   ├── game_night/          # Soirée : configuration, lancement, manches, classement, lecture de l'état
│   │                        # et presenter de la soirée (vues régie / écran public)
│   ├── blindtest/           # Use case, schémas, service de playlist et port Spotify
│   ├── stopchrono/ culture/ bombe/ memory/ seven_differences/ auction/ forbidden_word/
│   │   vanishing_word/ flash_calc/ right_flag/ golden_family/ fair_price/
│   │                        # <jeu>_command_usecase.py, <jeu>_presenter.py, <jeu>_rules.py
│   │                        # (+ <jeu>_commands.py pour ses schémas)
│   └── use_cases.py         # GameUseCases : regroupe les use cases d'écriture
├── infrastructure/
│   ├── database/            # Moteur SQLAlchemy, verrou d'instance unique
│   │   ├── accounts/        # Tables des comptes joueurs : comptes et sessions
│   │   ├── rooms/           # Salons en ligne et leurs membres
│   │   ├── rate_limiting/   # Compteurs d'essais (partagés : comptes, invitations, créations de salons)
│   │   ├── outbox/          # Outbox transactionnelle : écriture, lecture par le relais, purge
│   │   ├── sql_unit_of_work.py  # Base des unités de travail SQL (une session, rollback par défaut)
│   │   ├── game_sessions/   # game_session_model.py : la table commune des parties
│   │   ├── games/           # Un dossier par jeu : <jeu>_game_model.py, <jeu>_mapper.py, <jeu>_repository.py
│   │   │   └── shared/      # Colonnes communes, mapper versionné, dépôt à verrouillage optimiste
│   │   └── all_models.py    # Agrégat de toutes les tables, réservé au schéma (Alembic, create_all)
│   ├── repositories/        # Un dossier par domaine, comme domain/ :
│   │   ├── game_night/      # Unit of Work de la partie, dépôt qui compose les jeux, cache mémoire, mapper
│   │   ├── accounts/        # Unit of Work des comptes, dépôts comptes et sessions
│   │   └── rooms/           # Unit of Work des salons (salon + outbox + compteurs), dépôt à verrou optimiste
│   └── extern/              # Spotify, bridge buzzers USB
├── interface/
│   ├── api/                 # Routeurs HTTP et WebSocket
│   ├── schemas/             # Schémas de réponse et enveloppe des messages WebSocket
│   ├── dependencies/        # Composition racine (container) et authentification
│   ├── realtime/            # Hub WebSocket, routes et dispatcher des messages ; hub et diffusion des salons
│   └── workers/             # Tâches de fond : chronos, ménage des comptes et des salons, relais de l'outbox
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
  `game_config_from_payload` dans `infrastructure/repositories/game_night/game_config_mapper.py`) : l'état brut de
  l'agrégat, sans vue client ni événement.
- En base, la partie suit les bounded contexts :
  - **`game_sessions`** porte le cycle de vie commun en colonnes : statut, jeu de la manche en cours
    (`active_game_key`), manches, vainqueurs, ouverture, configuration, dates de création et d'écriture.
  - **Une table par jeu** (`blindtest_games`, `fair_price_games`…) contient `session_id`, l'état en JSONB,
    `schema_version` et `version`. Chaque jeu possède son dossier `infrastructure/database/games/<jeu>/` : sa
    table, son mapper (document JSONB vers état typé ; le domaine ne voit jamais le dictionnaire) et son dépôt.
  - **Versions de document :** une règle de jeu modifiée ne demande aucune migration Alembic. Si le format d'un
    document change, on monte `schema_version` dans le mapper et on ajoute `migrations[n]` (de `n` à `n + 1`) :
    les anciens documents sont mis à niveau étape par étape au chargement. `repair` corrige les données encore au
    bon format mais devenues invalides (objet retiré d'un catalogue…).
  - **Verrou optimiste :** la ligne commune et chaque ligne de jeu ont une `version`, et une écriture ne passe que
    si la version n'a pas changé depuis la lecture (`UPDATE … WHERE version = :attendue`). Sinon, rien n'est
    écrasé : `ConcurrentModificationError` (409 en HTTP), puis le cache et le dépôt relisent la base.
  - **Écritures :** une action n'écrit que ce qui a changé, en pratique la ligne commune et la table du jeu en
    cours, dans une seule transaction.
  - **Garde-fou :** un champ ajouté à `GameSession` sans colonne fait échouer `test_game_session_persistence.py`.
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
  `infrastructure/repositories/game_night/game_config_unit_of_work.py`) encadre chaque commande : transaction exclusive,
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
- L'API tourne en un seul processus : l'état des parties, le hub WebSocket, les verrous et les minuteurs sont
  en mémoire. C'est imposé, pas seulement recommandé : au démarrage, l'API prend un verrou consultatif
  PostgreSQL (`SingleInstanceLock`), tenu toute la vie du processus. Une seconde instance sur la même base
  (`--workers 2`, une réplique…) s'arrête avec un message explicite. PostgreSQL libère le verrou si le
  processus meurt.
- Environnements : `development`, `dev`, `local` et `test` sont locaux. Tout autre nom (`staging`, `recette`,
  `production`, ou une faute de frappe) est traité comme un déploiement : secrets, origine de l'app joueur et
  proxy de confiance obligatoires, cookies `Secure`, schéma par migrations seulement.
- Tâches de fond (`infrastructure/runtime/periodic_task.py`) : minuteur des jeux et ménage des comptes. Après
  une erreur, elles réessaient vite (1 s, 2 s, 4 s…, plafonné à leur intervalle), avec le nombre d'échecs
  d'affilée dans le journal. L'arrêt est gracieux : le passage en cours se termine, une transaction n'est
  jamais coupée en deux.

### Comptes joueurs (`/api/accounts`)

- `POST /register`, `POST /login`, `POST /logout`, `GET /me`. Domaine dans `back/domain/accounts/`
  (pseudo, règles du mot de passe, compte, session), cas d'usage dans `back/application/accounts/`.
- Unité de travail `AccountUnitOfWork` : compte, session et compteurs d'essais partagent une transaction.
  Une inscription crée le compte et sa session ensemble ou pas du tout. Une reconnexion révoque l'ancienne
  session dans la même transaction. Le hachage Argon2 a lieu entre deux transactions : aucune connexion à
  la base n'est retenue pendant le calcul.
- Pseudo de 3 à 20 caractères (lettres, accents compris, chiffres, `-`, `_`), unique sans tenir compte de
  la casse. Les noms qui imitent l'équipe (« admin », « modo », « gamebattle »…) sont refusés à l'inscription.
- Mot de passe de 8 à 128 caractères, normalisé en NFKC (un « é » tapé sur n'importe quel clavier reste le
  même), refusé s'il est très répandu ou contient le pseudo.
- Une erreur de règle indique le champ fautif (`{"detail": …, "field": "pseudo" | "password"}`) : l'app
  l'affiche sous ce champ.
- Mots de passe hachés en Argon2id (`argon2-cffi`, paramètres RFC 9106) dans un thread, au plus deux à la
  fois : la boucle d'événements des parties ne bloque jamais. Les anciens hachages sont mis à niveau à la
  connexion suivante.
- La session est un jeton aléatoire de 256 bits, dans un cookie `HttpOnly`, `SameSite=Strict`, valable
  30 jours (`__Host-gb_session` avec `Secure` en production). La base n'en garde que l'empreinte SHA-256.
  Elle glisse : un joueur qui revient après plus de 15 jours repart pour 30 jours. Se reconnecter dans le
  même navigateur révoque la session précédente.
- Le corps des requêtes de connexion est lu par morceaux et borné à 2 Ko, même sans `Content-Length`.
- L'app joueur de production embarque une CSP stricte (tout depuis la même origine, aucun script inline).
- Anti-CSRF en plus de `SameSite=Strict` :
  - toute écriture doit annoncer son origine (`Origin`, sinon `Referer`) ; `Origin: null` est refusé ;
  - l'origine doit figurer dans `GAMEBATTLE_PLAYER_ORIGINS` (obligatoire une fois déployé), ou désigner l'hôte de
    la requête en développement ;
  - `Sec-Fetch-Site: cross-site` est toujours refusé (403) ;
  - l'app joueur a la politique de référent `same-origin` : avec `no-referrer`, ses POST partiraient avec
    `Origin: null`.
- Un mauvais mot de passe et un pseudo inconnu donnent la même réponse, dans le même temps.
- Freins persistés en base (table `auth_attempts`, fenêtres fixes) :
  - limites : 30 essais par adresse IP et 5 connexions par pseudo sur 15 minutes, 10 inscriptions par IP et
    par heure ; une connexion réussie remet le compteur du pseudo à zéro ;
  - chaque essai est réservé dès sa réception, avant toute validation et avant Argon2, par un seul
    `INSERT … ON CONFLICT DO UPDATE … RETURNING` atomique. Il n'y a jamais de lecture séparée : des requêtes
    simultanées ne peuvent pas dépasser la limite, et une requête refusée compte aussi ;
  - les clés sont des HMAC-SHA256 à clé dédiée (`GAMEBATTLE_RATE_LIMIT_SECRET`) : ni IP ni pseudo en clair, et
    rien à retrouver par énumération. Changer la clé remet simplement les compteurs à zéro ;
  - le nettoyeur `AccountJanitor` (`interface/workers/`) déclenche toutes les 10 minutes `AccountMaintenance`,
    qui purge les compteurs périmés et les sessions expirées ;
  - les réponses 429 portent un en-tête `Retry-After`.

#### Déploiement : décisions imposées

- **Même origine.** L'app joueur et l'API sont servies sur le même domaine, derrière Caddy (`/api/*` vers
  uvicorn, le reste vers les fichiers de `app-joueur/dist`). L'app appelle des chemins relatifs, le cookie
  reste `SameSite=Strict`, et CORS n'autorise jamais les cookies. Un déploiement sur deux domaines n'est pas
  prévu : il affaiblirait ces protections.
- **Adresse des joueurs.** uvicorn tourne avec `--no-proxy-headers` : c'est l'application qui détermine
  l'adresse (`interface/client_address.py`). Elle ne lit `X-Forwarded-For` que si la connexion vient d'un
  proxy listé dans `GAMEBATTLE_TRUSTED_PROXIES`, et garde la dernière adresse qui n'est pas un proxy de
  confiance. Caddy a une adresse fixe (`172.30.0.10`) et remplace tout `X-Forwarded-For` envoyé par le client.
- **Schéma.** En production, le schéma n'évolue que par les migrations Alembic (voir plus bas).

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
- `GAMEBATTLE_PLAYER_ORIGINS` (origine exacte de l’app joueur, obligatoire une fois déployé)
- `GAMEBATTLE_TRUSTED_PROXIES` (adresses des reverse proxies de confiance pour `X-Forwarded-For`)
- `GAMEBATTLE_RATE_LIMIT_SECRET` (clé HMAC dédiée des compteurs d'essais, obligatoire une fois déployé ; sans espace,
  générée par `openssl rand -hex 32`)
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

### Production (VPS)

La stack `deploy/` contient trois services : Caddy (HTTPS automatique, app joueur et API sur le même domaine),
le backend et PostgreSQL. Seul Caddy est exposé. La base est sur un réseau interne, sans accès à Internet. Les
conteneurs tournent sans privilèges, et le backend en lecture seule. Au démarrage, le backend applique les
migrations Alembic avant d'ouvrir son port.

```bash
cp deploy/.env.example deploy/.env      # domaine, origine, secrets (openssl rand -hex 32)
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
```

L'adresse de Caddy (`172.30.0.10`) est définie une seule fois dans le compose : elle sert à son réseau et comme
seul proxy de confiance du backend. Le contrôle de santé de Caddy passe par lui-même jusqu'au backend (port
interne 8081, jamais publié). Il n'est sain que si le backend le reconnaît comme proxy : si l'adresse dérive,
`up --wait` échoue et Caddy reste *unhealthy*. Un `X-Forwarded-For` reçu d'un pair inconnu est aussi signalé dans
les journaux (`client_address.untrusted_forwarded_for peer=…`).

Après chaque déploiement, vérifier le contrat avec :

```bash
deploy/verify.sh https://jeu.exemple.fr
```

Le script n'écrit rien : aucun compte créé, aucun essai consommé. Il contrôle les en-têtes de sécurité et la CSP,
l'API sur la même origine, la reconnaissance du proxy, les refus anti-CSRF et l'absence de cookies CORS.

Ce déploiement a été vérifié en local (`GAMEBATTLE_DOMAIN=localhost`, ports 8080/8443) :
- `deploy/verify.sh` passe sans échec ; cookie `__Host-gb_session` `Secure` en HTTPS ;
- un `X-Forwarded-For` forgé n'a aucun effet sur les limites, alors qu'un second client est bien compté à part ;
- cinq connexions simultanées sur le dernier essai donnent un seul 401 et quatre 429 ;
- une seconde instance du backend refuse de démarrer ; une adresse de proxy qui dérive fait échouer `up --wait` ;
- parcours complet dans un navigateur, coupures réseau comprises.

### Salons en ligne (`/api/rooms`, `/ws/rooms/current`)

Un joueur connecté crée une partie **publique** (listée pour tous) ou **privée** (accessible par son lien), en
**1 contre 1** ou **en équipes** (2 à 4 équipes de 4 joueurs). À la création, un lien d'invitation
`/rejoindre/<code>` est remis au joueur ; dans une partie privée en équipes, celui qui ouvre le lien choisit son
équipe (et peut en changer dans la salle d'attente). Ailleurs, les équipes s'équilibrent seules. Lancer les jeux
en ligne viendra ensuite : le bouton « Lancer la partie » est déjà en place, désactivé.

- Domaine `back/domain/rooms/` : l'agrégat `Room` (immuable) porte toutes les règles. Un joueur n'est que dans un
  salon à la fois. Entrer deux fois ne change rien. Un salon complet refuse les nouveaux. Quand l'hôte part, le
  plus ancien membre prend la main, et le dernier départ ferme le salon. Chaque action produit ses événements
  (`room.player_joined`, `room.team_changed`…).
- HTTP : `POST /api/rooms`, `GET /current`, `GET /public`, `GET /invitations/{code}` (aperçu), `POST /invitations/{code}/join`,
  `POST /{id}/join` (parties publiques seulement), `POST /current/team`, `POST /current/leave`. Toutes les routes exigent
  la session et, pour les écritures, la même origine que les comptes. Aucune réponse ne contient d'identifiant de
  compte : les joueurs se reconnaissent à leur pseudo.
- Codes d'invitation :
  - 10 caractères tirés de `secrets`, sans 0/O ni 1/I, soit environ 10^15 possibilités ;
  - 30 consultations par IP par quart d'heure ;
  - un salon privé ne se rejoint pas par son identifiant ;
  - au plus 10 créations de salons par joueur et par heure.
- **Verrou optimiste** : colonne `version`, `UPDATE … WHERE version = :lue`. En cas de conflit (deux joueurs qui
  entrent au même instant), le cas d'usage relit l'état et rejoue, jusqu'à 3 fois. L'unicité de `room_members.account_id`
  garantit « un salon par joueur » même en cas de course.
- **Outbox transactionnelle** (`outbox_events`) : les événements sont écrits dans la même transaction que le salon.
  Le relais `OutboxRelay` les publie dans l'ordre puis les marque publiés. Il est réveillé après chaque écriture
  validée et repasse de toute façon chaque seconde. La livraison est « au moins une fois » : chaque message
  porte l'état complet, donc un message rejoué est sans effet. `RoomJanitor` ferme les salons inactifs depuis
  6 h et purge les événements publiés.
- **WebSocket `/ws/rooms/current`** : flux du salon du joueur connecté.
  - Poignée de main : l'origine est vérifiée avant `accept` (refus 1008), puis la session (cookie HttpOnly, sinon
    4401) et l'appartenance à un salon (sinon 4404).
  - Resynchronisation : `room.snapshot` à chaque connexion et sur demande (`resync`). Ensuite, `room.updated`
    porte la vue complète propre à chaque joueur, avec la présence en ligne et les événements récents.
  - Séparation public / privé : les événements privés (`audience`) ne partent qu'à leur destinataire.
  - Heartbeat : ping toutes les 20 s ; une connexion muette est coupée au bout de 50 s (4408) ; la session est
    revérifiée chaque minute.
  - Débit limité à 2 messages par seconde, en rafale de 10, et 256 caractères au plus par message (4429). La
    file d'envoi est bornée pour chaque connexion : un client lent est coupé, sans ralentir les autres.
  - Au plus 3 onglets par joueur : le plus ancien est fermé (4000).
  - `room.left` ou `room.closed` est envoyé avant la fermeture 4000.
  - L'app joueur se reconnecte avec une attente exponentielle et aléatoire, et tout de suite au retour sur la
    page ou du réseau. Elle ne se reconnecte jamais après 4000, 4401 ou 4404.

### Migrations de la base (Alembic)

En développement et dans les tests, l'API crée elle-même les tables manquantes au démarrage. En
production (`GAMEBATTLE_ENVIRONMENT=production`), elle ne touche jamais au schéma : il faut migrer avant de
démarrer.

```bash
cd back
.venv/bin/alembic upgrade head           # base vide ou déjà suivie par Alembic
.venv/bin/alembic stamp head             # base créée par l'API en développement : la marquer, une seule fois
.venv/bin/alembic revision -m "…"        # nouvelle migration, à écrire dans migrations/versions/
```

La migration `0003` remplace l'ancien document unique (`game_config_state`) par `game_nights` et les tables de
jeu, en recopiant les données ; la descente refait le document. La migration `0004` renomme `game_nights` en
`game_sessions` (et `night_id` en `session_id`), puis ajoute les versions du verrou optimiste, les dates et le
jeu en cours. Une base créée par l'API en développement
(sans Alembic) importe une fois l'ancien document au premier démarrage et le laisse en place ; une fois
vérifié, il peut être supprimé (`DROP TABLE game_config_state`).

La migration `0005` aligne sur PostgreSQL les noms de contraintes que les renommages de `0004` laissaient
derrière eux (`game_nights_pkey`, `<jeu>_games_night_id_fkey`), pour qu'une base migrée et une base créée depuis
les modèles soient identiques.

La migration `0006` crée les salons (`rooms`, `room_members`) et l'outbox (`outbox_events`).

Les migrations sont testées sur un vrai PostgreSQL, jetable, avant toute mise en production :

```bash
bash scripts/test-migrations-postgres.sh   # Docker requis : conteneur postgres:15 créé puis supprimé
```

Le script migre depuis `0002` avec des données réelles, puis compare les contraintes, index et colonnes à une base
construite depuis les modèles. Il vérifie aussi les clés étrangères (`ON DELETE CASCADE` vers `game_sessions`),
le verrou optimiste et la conservation des données, et redescend jusqu'à `0002`. Pour les salons, il vérifie aussi
la contrainte « un salon par joueur », la cascade à la suppression d'un compte et la descente de `0006`. Sans PostgreSQL, ces tests
(`tests/infrastructure/test_migrations_postgres.py`) sont ignorés.

Un test (`test_migrations_build_exactly_the_schema_of_the_models`) vérifie que les migrations produisent
exactement le schéma des modèles SQLAlchemy : une table ajoutée sans migration fait échouer la suite.

### Web écran

```bash
cd /Users/lucasdasilvamarques/GameBattle
bash scripts/dev-web.sh
```

### App joueur

```bash
cd /Users/lucasdasilvamarques/GameBattle
bash scripts/dev-joueur.sh
```

Ouvre <http://127.0.0.1:5174>. Le proxy Vite renvoie `/api` et le WebSocket `/ws` vers le backend sur
`http://127.0.0.1:8000` (ou vers `GAMEBATTLE_API_URL`). Pour essayer à plusieurs, ouvre une fenêtre privée par
joueur et partage le lien d'invitation affiché dans la salle d'attente.

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

Au lancement de la soirée, l’écran public présente les équipes une à une (avec leur touche de buzzer),
puis affiche les **règles de la manche** pendant 10 secondes : trois lignes et un exemple. Chaque
nouvelle manche s’ouvre aussi sur ses règles. L’enchaînement est piloté par le serveur (synchronisé
avec la régie, même après un rechargement) ; la régie peut passer à l’étape suivante, et le premier coup
joué ferme l’écran des règles. Les règles de chaque jeu ont leur propre fichier,
`back/application/<jeu>/<jeu>_rules.py`, branché sur le presenter du jeu.

Pour **Le juste prix**, chaque équipe joue à son tour. Le serveur tire une gamme de prix (par exemple « de
150 à 900 € »), puis attribue à chaque équipe un objet différent de cette gamme, avec un prix différent :
personne ne peut reprendre la réponse de l’équipe précédente. La régie lance le chrono (60 s maximum) :
l’image de l’objet apparaît alors sur l’écran public et sur le mobile, qui affiche aussi le vrai prix. Le
présentateur répond « c’est plus » / « c’est moins » (boutons ou Volume + / Volume −) puis « Trouvé ! ».
L’équipe qui trouve le plus vite remporte la manche ; l’écran public ne reçoit le prix qu’à la fin du tour.
Le catalogue est dans `back/domain/fair_price/services/fair_price_catalog.py` : 31 vrais produits (du sac
FRAKTA d’IKEA à 1 € au Renault Espace à 46 500 €), avec leurs prix publics TTC relevés le 31 octobre 2026 sur
le site de la marque ou d’un grand distributeur français. Les photos, dans `back/media/fair_price/`, viennent
de Wikimedia Commons sous licence libre ; l’auteur et la licence s’affichent sous l’image, et
`back/media/fair_price/CREDITS.md` donne pour chaque objet la page de la photo et la source du prix. Elles sont
servies par le backend sur `/media/fair-price/<fichier>` (liste fermée, cache long). Les prix changent : mettez
à jour `PRICES_CHECKED_ON` et le catalogue quand vous les relevez de nouveau.

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

### Organisation des tests

Les tests suivent les modules métier, pas les couches :

| Dossier | Ce qu'il teste |
| --- | --- |
| `tests/architecture/` | Dépendances entre couches (`test_imports.py`), frontières entre modules (`test_module_boundaries.py`), rangement des fichiers (`test_file_responsibilities.py`) |
| `tests/accounts/` | Règles des comptes, cas d'usage, limites d'essais, dépôts, hachage, ménage, API |
| `tests/rooms/` | Règles des salons, cas d'usage (conflits, limites), dépôt SQL et outbox, API, WebSocket, relais |
| `tests/game_night/` | Soirée : API, persistance des parties, unité de travail, manches, ouverture, événements |
| `tests/games/<jeu>/` | Chaque jeu ; `tests/games/shared/` pour le flux de buzz commun |
| `tests/interface/` | Adresse du client, hub WebSocket, messages et routes temps réel |
| `tests/infrastructure/` | Configuration, tâches de fond, migrations (SQLite et PostgreSQL) |

`tests/support.py` (soirée de test, `BACK_DIR`), `tests/account_support.py`, `tests/room_support.py` (salons en
mémoire, transactionnels), `tests/room_app_support.py` (app réduite avec le vrai relais et le vrai hub) et
`tests/architecture_support.py` regroupent ce que plusieurs fichiers partagent. `tests/conftest.py` fournit une
base SQLite jetable (`sqlite_database`). La configuration de pytest est dans `back/pyproject.toml` (mode
`importlib`, pas de `__init__.py` dans les dossiers de tests).

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

App joueur :

```bash
cd /Users/lucasdasilvamarques/GameBattle/app-joueur
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

