# Frontend image: build the Expo React Native Web bundle, serve as static assets.
# The API URL is baked at build time (the browser runs on the host and hits the
# host-mapped API port). Override with --build-arg EXPO_PUBLIC_API_URL=...

# --- build stage ---
FROM node:22-slim AS build
WORKDIR /app
ARG EXPO_PUBLIC_API_URL=http://localhost:8000
ENV EXPO_PUBLIC_API_URL=$EXPO_PUBLIC_API_URL
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npx expo export --platform web --output-dir dist

# --- serve stage ---
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# SPA fallback so client routes resolve to index.html
RUN printf 'server {\n  listen 80;\n  location / {\n    root /usr/share/nginx/html;\n    try_files $uri $uri/ /index.html;\n  }\n}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
