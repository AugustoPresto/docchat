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

# At runtime, replace placeholders with real upstream URLs from env vars.
# BACKEND_URL  → internal Fly.io URL for API calls (e.g. http://docchat-backend.internal:8000/api/)
# PUBLIC_BACKEND_URL → public HTTPS URL for health check (e.g. https://docchat-backend.fly.dev)
CMD ["sh", "-c", \
  "BACKEND=${BACKEND_URL:-http://backend:8000/api/} && \
   HEALTH=${PUBLIC_BACKEND_URL:-http://backend:8000}/health && \
   sed -i \"s|BACKEND_UPSTREAM_PLACEHOLDER|${BACKEND}|g\" /etc/nginx/conf.d/default.conf && \
   sed -i \"s|HEALTH_UPSTREAM_PLACEHOLDER|${HEALTH}|g\" /etc/nginx/conf.d/default.conf && \
   nginx -g 'daemon off;'"]
