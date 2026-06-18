# === Build Stage ===
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
ENV PATH="./node_modules/.bin:$PATH"
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/src/ ./src/
COPY frontend/*.json ./
COPY frontend/*.js ./
COPY frontend/*.html ./
RUN npm run build

# === Production Stage ===