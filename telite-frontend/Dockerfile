FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

ENV BACKEND_SERVICE_HOST=backend \
    BACKEND_INTERNAL_PORT=8001

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
