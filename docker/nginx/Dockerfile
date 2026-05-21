# ─────────────────────────────────────────────────────────────────────────────
# Multi-stage build: Node.js (React build) → Nginx (serve + reverse proxy)
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Build the React frontend
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies first (layer caching)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --legacy-peer-deps 2>/dev/null || npm install --legacy-peer-deps --include=dev

# Copy source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:1.31.0-alpine

# Required by entrypoint.sh for self-signed cert (prod) + htpasswd generation
RUN apk add --no-cache openssl apache2-utils

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy both dev and prod nginx configs — entrypoint selects the right one
COPY docker/nginx/nginx-dev.conf /etc/nginx/conf.d/nginx-dev.conf
COPY docker/nginx/nginx-prod.conf /etc/nginx/conf.d/nginx-prod.conf

# Copy built React app from Stage 1
COPY --from=build /app/dist /usr/share/nginx/html

# Create ACME challenge directory (used in prod mode)
RUN mkdir -p /var/www/certbot

# Copy entrypoint that selects config and templates domain
COPY docker/nginx/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# Copy periodic nginx reload helper so renewed certs are picked up automatically
COPY scripts/nginx_auto_reload.sh /usr/local/bin/nginx_auto_reload.sh
RUN sed -i 's/\r$//' /usr/local/bin/nginx_auto_reload.sh && chmod +x /usr/local/bin/nginx_auto_reload.sh

EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
