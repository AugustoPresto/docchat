# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV VITE_API_URL=/api/v1
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

# At runtime, replace placeholders with the backend URLs (defaults fit docker-compose).
# BACKEND_URL        → API upstream, e.g. http://backend:8000/api/
# PUBLIC_BACKEND_URL → base URL for /health, e.g. http://backend:8000
CMD ["sh", "-c", \
  "BACKEND=${BACKEND_URL:-http://backend:8000/api/} && \
   HEALTH=${PUBLIC_BACKEND_URL:-http://backend:8000}/health && \
   sed -i \"s|BACKEND_UPSTREAM_PLACEHOLDER|${BACKEND}|g\" /etc/nginx/conf.d/default.conf && \
   sed -i \"s|HEALTH_UPSTREAM_PLACEHOLDER|${HEALTH}|g\" /etc/nginx/conf.d/default.conf && \
   nginx -g 'daemon off;'"]
