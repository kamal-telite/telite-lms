FROM node:22-alpine AS build

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
RUN npm ci --audit

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

LABEL org.opencontainers.image.title="Telite LMS Frontend" \
      org.opencontainers.image.description="Static React frontend for Telite LMS" \
      org.opencontainers.image.source="https://github.com/telite-systems/telite-lms"

# Update Alpine packages for security patches
RUN apk update && apk upgrade && apk add --no-cache \
    dumb-init

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

ENV BACKEND_SERVICE_HOST=backend \
    BACKEND_INTERNAL_PORT=8001 \
    NGINX_ENVSUBST_TEMPLATE_DIR=/etc/nginx/templates \
    NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx/conf.d

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

# Use dumb-init as PID 1 for proper signal handling and preserve nginx base entrypoint behavior
ENTRYPOINT ["dumb-init", "--", "/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
