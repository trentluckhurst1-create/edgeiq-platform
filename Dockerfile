FROM python:3.14.3-slim

ARG NODE_VERSION=24.14.0

ENV NODE_ENV=production
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
    | tar -xJ -C /usr/local --strip-components=1 \
    && node --version \
    && npm --version

COPY package.json package-lock.json ./
RUN npm ci

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY . .

RUN unzip -oq deployment/edgeiq_free_beta_runtime_v1.zip -d /app \
    && test -d /app/public/data \
    && test -d /app/public/performance-intelligence \
    && rm deployment/edgeiq_free_beta_runtime_v1.zip

RUN npm_config_ignore_scripts=true npm run build

CMD ["npm", "run", "start"]