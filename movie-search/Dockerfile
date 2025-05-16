# Base image using Debian-based Node 18
FROM node:18 AS base

# 1. Install dependencies only when needed
FROM base AS deps

WORKDIR /app

# Install dependencies based on the preferred package manager
COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./

# Use npm ci if lockfile exists
RUN \
  if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
  elif [ -f package-lock.json ]; then npm ci; \
  elif [ -f pnpm-lock.yaml ]; then npm install -g pnpm && pnpm install; \
  else echo "Lockfile not found." && exit 1; \
  fi

# 2. Rebuild the source code only when needed
FROM base AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

COPY .env.development .env.development
COPY .env.production .env.production

# Build the Next.js app
RUN npm run build

# 3. Production image
FROM base AS runner

WORKDIR /app

ENV NODE_ENV=production

# Create app user
RUN addgroup --system nodejs && adduser --system --ingroup nodejs nextjs

# Optional: install debugging tools
RUN apt-get update && apt-get install -y curl && apt-get clean

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Optional: for tracing
# COPY --from=builder --chown=nextjs:nodejs /app/instrumentation.js ./
# COPY --from=builder --chown=nextjs:nodejs /app/tracing.js ./

# Run as non-root user
USER nextjs

EXPOSE 3000
ENV PORT 3000

# CMD node --require ./tracing.js server.js
# CMD node --require ./instrumentation.js server.js
CMD node server.js
