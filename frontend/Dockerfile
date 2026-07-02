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
CMD ["sh", "-c", "if [ -n \"$BACKEND_URL\" ]; then sed -i \"s|http://backend:8000/api/|$BACKEND_URL|g\" /etc/nginx/conf.d/default.conf; fi && if [ -n \"$PUBLIC_BACKEND_URL\" ]; then sed -i \"s|http://backend:8000/health|$PUBLIC_BACKEND_URL/health|g\" /etc/nginx/conf.d/default.conf; fi && nginx -g 'daemon off;'"]
