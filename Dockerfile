# --- build the Vue dashboard ---
FROM node:20-alpine AS web
WORKDIR /web
COPY dashboard/package*.json ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

# --- python runtime that serves API + built dashboard ---
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=web /web/dist ./dashboard/dist
# Hugging Face Spaces route to port 7860 by default
ENV PORT=7860
EXPOSE 7860
CMD ["python", "src/dashboard_api.py"]
