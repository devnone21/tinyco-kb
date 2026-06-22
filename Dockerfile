# syntax=docker/dockerfile:1.7
# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app

# Install deps.
# - If package-lock.json exists (committed for reproducible CI):
#     use `npm ci` for deterministic installs.
# - Otherwise (first build / no lockfile):
#     fall back to `npm install` so the build doesn't break.
# To switch to strict mode: run `npm install` locally and commit the
# generated package-lock.json, then change `npm install` → `npm ci`.
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then \
      echo ">>> using npm ci (lockfile present)"; \
      npm ci --no-audit --no-fund; \
    else \
      echo ">>> using npm install (no lockfile found)"; \
      npm install --no-audit --no-fund; \
    fi

# Build
COPY . .
RUN npm run build

# ---- runtime stage ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
