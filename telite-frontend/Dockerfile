FROM node:26-alpine AS build

WORKDIR /app
ARG VITE_API_BASE_URL=
ARG VITE_APP_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_APP_URL=${VITE_APP_URL}

# Update Alpine packages for security
RUN apk update && apk upgrade && apk add --no-cache \
    dumb-init

COPY package*.json ./

# Run npm audit to check for vulnerabilities
RUN npm audit --audit-level=moderate || true

# Install dependencies with security audit enabled
RUN npm install --audit

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

LABEL org.opencontainers.image.title="Telite LMS Frontend" \
      org.opencontainers.image.description="Static React frontend for Telite LMS" \
      org.opencontainers.image.source="https://github.com/telite-systems/telite-lms"

# Update Alpine packages for security patches
RUN apk update && apk upgrade && apk add --no-cache \
    dumb-init \
    gettext

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

ENV BACKEND_SERVICE_HOST=backend \
    BACKEND_INTERNAL_PORT=8001 \
    NGINX_ENVSUBST_TEMPLATE_DIR=/etc/nginx/templates \
    NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx/conf.d

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

RUN mkdir -p /etc/nginx/conf.d && \
    printf '#!/bin/sh\nset -eu\nif [ -f /etc/nginx/templates/default.conf.template ]; then\n  envsubst '\''${BACKEND_SERVICE_HOST} ${BACKEND_INTERNAL_PORT}'\'' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf\nfi\nexec dumb-init -- nginx -g "daemon off;"\n' > /usr/local/bin/start-nginx.sh && \
    chmod +x /usr/local/bin/start-nginx.sh

ENTRYPOINT ["/usr/local/bin/start-nginx.sh"]
