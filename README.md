# GameBattle

Monorepo pour une plateforme multi-jeux orientée plateau / animation live, avec :

- un **backend FastAPI**
- une **app mobile React Native** pour le présentateur
- une **app React web** affichée sur l'écran principal

Le backend suit une architecture DDD inspirée de `BetLeague`.

---

## État actuel du projet

Cette version fournit un moteur multi-jeux synchronisé : **Blindtest**, **Stop Chrono**,
**Culture générale**, **La Bombe**, **Mémoire en chaîne** et **Les 7 différences**.

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

Le backend reprend le découpage DDD suivant :

- `domain/` : règles métier, agrégats, exceptions, repository abstrait
- `application/` : modèles d'entrée / sortie et use cases
- `infrastructure/` : config, PostgreSQL, temps réel
- `presentation/` : routeurs HTTP / WebSocket
- `dependency_injections.py` : composition racine
- `main.py` : bootstrap FastAPI, middleware sécurité, CORS

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
- `GAMEBATTLE_SPOTIFY_CLIENT_ID`
- `GAMEBATTLE_SPOTIFY_CLIENT_SECRET`

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

Pour un buzzer USB plus avancé qui n'émule pas un clavier, utilise le bridge local :

- fichier d'exemple : `scripts/hardware-buzzers.example.json`
- runner : `scripts/dev-buzzers.sh`
- module Python : `back/infrastructure/hardware/usb_buzzer_bridge.py`

---

## Validations exécutées

Backend :

```bash
cd /Users/lucasdasilvamarques/GameBattle/back
./.venv/bin/python -m pytest tests/test_game_config_api.py -q
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
./.venv/bin/python -m infrastructure.hardware.usb_buzzer_bridge --help
```

---

## Suite recommandée

Ensuite, je recommande cet ordre :

1. **Lecture blindtest native complète** : remplacer le provider Spotify Web API par un provider SDK natif dans la même abstraction
2. **Buzzers USB avancés** : auto-détection + UI de calibration des périphériques HID
3. **Catalogue de contenus** : ajouter de nouveaux puzzles et banques de questions

