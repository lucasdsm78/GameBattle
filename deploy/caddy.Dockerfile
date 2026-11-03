# Image Caddy avec l'app joueur compilée : construite depuis la racine du dépôt (voir docker-compose.prod.yml).
FROM node:22-alpine AS joueur
WORKDIR /app
COPY app-joueur/package.json app-joueur/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app-joueur/ ./
RUN npm run build

FROM caddy:2.10-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=joueur /app/dist /srv/joueur
