FROM node:22.22.0-bookworm-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends unzip \
    && rm -rf /var/lib/apt/lists/*

COPY deployment/edgeiq_free_beta_runtime_v1.zip /app/deployment/edgeiq_free_beta_runtime_v1.zip
COPY deployment/edgeiq_render_server.mjs /app/deployment/edgeiq_render_server.mjs

RUN unzip -oq /app/deployment/edgeiq_free_beta_runtime_v1.zip -d /app \
    && test -f /app/dist/index.html \
    && test -d /app/public/data \
    && test -d /app/public/performance-intelligence \
    && rm /app/deployment/edgeiq_free_beta_runtime_v1.zip

CMD ["node", "deployment/edgeiq_render_server.mjs"]