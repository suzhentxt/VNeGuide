# syntax=docker/dockerfile:1.7

FROM node:25-alpine@sha256:bdf2cca6fe3dabd014ea60163eca3f0f7015fbd5c7ee1b0e9ccb4ced6eb02ef4 AS dependencies
WORKDIR /app
COPY demoweb/package.json demoweb/package-lock.json ./
RUN npm ci

FROM node:25-alpine@sha256:bdf2cca6fe3dabd014ea60163eca3f0f7015fbd5c7ee1b0e9ccb4ced6eb02ef4 AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=dependencies /app/node_modules ./node_modules
COPY demoweb ./
COPY data/catalog/field_catalog.json /data/catalog/field_catalog.json
RUN npm run build

FROM node:25-alpine@sha256:bdf2cca6fe3dabd014ea60163eca3f0f7015fbd5c7ee1b0e9ccb4ced6eb02ef4 AS runner
WORKDIR /app
ENV HOSTNAME=0.0.0.0 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    VNEGUIDE_API_BASE_URL=http://api:8000

RUN apk add --no-cache ffmpeg \
    && addgroup --system --gid 10001 vneguide \
    && adduser --system --uid 10001 --ingroup vneguide vneguide

COPY --from=builder --chown=vneguide:vneguide /app/.next/standalone ./
COPY --from=builder --chown=vneguide:vneguide /app/.next/static ./app/.next/static
COPY --from=builder --chown=vneguide:vneguide /app/public ./app/public
COPY --from=builder --chown=vneguide:vneguide /data/catalog/field_catalog.json /data/catalog/field_catalog.json

USER vneguide
EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=3s --start-period=15s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]

CMD ["node", "app/server.js"]
