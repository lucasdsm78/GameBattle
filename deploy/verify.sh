#!/usr/bin/env bash
# Vérifie un déploiement GameBattle sans rien y écrire : aucun compte créé, aucun essai de connexion consommé.
# Usage : deploy/verify.sh https://jeu.exemple.fr [--insecure]   (--insecure : certificat local, ex. https://localhost:8443)
set -uo pipefail

BASE="${1:?Usage : deploy/verify.sh https://jeu.exemple.fr [--insecure]}"
BASE="${BASE%/}"
CURL=(curl --silent --show-error --max-time 10)
[[ "${2:-}" == "--insecure" ]] && CURL+=(--insecure)
failures=0

check() { # check <description> <condition évaluée par bash>
  if eval "$2"; then printf '  \033[32m✓\033[0m %s\n' "$1"; else printf '  \033[31m✗\033[0m %s\n' "$1"; failures=$((failures + 1)); fi
}

status() { "${CURL[@]}" -o /dev/null -w '%{http_code}' "$@"; }

echo "Page de l'app joueur ($BASE/)"
page_headers=$("${CURL[@]}" -D - -o /tmp/gamebattle-verify-page.html "$BASE/")
check "répond 200" '[[ "$page_headers" == *" 200"* ]]'
check "HSTS" 'grep -qi "^strict-transport-security: max-age=" <<<"$page_headers"'
check "interdite dans un cadre (frame-ancestors + X-Frame-Options)" 'grep -qi "frame-ancestors '\''none'\''" <<<"$page_headers" && grep -qi "^x-frame-options: DENY" <<<"$page_headers"'
check "référent same-origin (sinon les POST partent avec Origin: null)" 'grep -qi "^referrer-policy: same-origin" <<<"$page_headers"'
check "CSP stricte dans le HTML" 'grep -q "Content-Security-Policy\" content=\"default-src '\''self'\''" /tmp/gamebattle-verify-page.html'
check "aucun en-tête Server" '! grep -qi "^server:" <<<"$page_headers"'

echo "API sur la même origine"
check "/api/accounts/me joignable (401 sans session)" '[[ $(status "$BASE/api/accounts/me") == 401 ]]'
health=$("${CURL[@]}" "$BASE/health")
check "le backend reconnaît le reverse proxy (via_trusted_proxy)" '[[ "$health" == *"\"via_trusted_proxy\":true"* ]]'
check "documentation de l'API désactivée" '[[ $("${CURL[@]}" "$BASE/openapi.json") != *"openapi"* ]]'

echo "Anti-CSRF (refusé avant tout traitement : rien n'est compté)"
body='{"pseudo":"verification","password":"verification"}'
post() { status -X POST "$BASE/api/accounts/login" -H 'Content-Type: application/json' -d "$body" "$@"; }
check "écriture sans Origin ni Referer → 403" '[[ $(post) == 403 ]]'
check "Origin d'un autre site → 403" '[[ $(post -H "Origin: https://pirate.example") == 403 ]]'
check "Origin: null → 403" '[[ $(post -H "Origin: null") == 403 ]]'
check "Sec-Fetch-Site: cross-site → 403" '[[ $(post -H "Origin: $BASE" -H "Sec-Fetch-Site: cross-site") == 403 ]]'

echo "CORS : jamais de cookies pour un autre site"
preflight=$("${CURL[@]}" -D - -o /dev/null -X OPTIONS "$BASE/api/accounts/login" \
  -H "Origin: https://pirate.example" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type")
check "pas d'Access-Control-Allow-Credentials" '! grep -qi "^access-control-allow-credentials:" <<<"$preflight"'

rm -f /tmp/gamebattle-verify-page.html
if ((failures)); then
  printf '\n\033[31m%d vérification(s) en échec.\033[0m\n' "$failures"
  exit 1
fi
printf '\n\033[32mDéploiement conforme.\033[0m\n'
