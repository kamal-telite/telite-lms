FROM node:20-alpine AS build

WORKDIR /app
ARG VITE_API_BASE_URL=
ARG VITE_APP_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_APP_URL=${VITE_APP_URL}
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine

LABEL org.opencontainers.image.title="Telite LMS Frontend" \
      org.opencontainers.image.description="Static React frontend for Telite LMS" \
      org.opencontainers.image.source="https://github.com/telite-systems/telite-lms"

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

ENV BACKEND_SERVICE_HOST=backend \
    BACKEND_INTERNAL_PORT=8001

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
