# Stage 1: Build
FROM node:20-alpine AS builder

# Install build dependencies and create non-root user
RUN apk add --no-cache python3 make g++ && \
    addgroup -S nodejs && \
    adduser -S nodeuser -G nodejs

WORKDIR /usr/src/app

# Set ownership and switch to non-root user
RUN chown nodeuser:nodejs /usr/src/app
USER nodeuser

# Copy package files with correct ownership
COPY --chown=nodeuser:nodejs package*.json ./
COPY --chown=nodeuser:nodejs tsconfig.json ./

# Install dependencies
RUN npm ci

# Copy source code with correct ownership
COPY --chown=nodeuser:nodejs . .

# Build TypeScript code
RUN npm run build

# Stage 2: Development
FROM node:20-alpine AS development

# Install development tools and create non-root user
RUN apk add --no-cache python3 make g++ dumb-init && \
    addgroup -S nodejs && \
    adduser -S nodeuser -G nodejs

WORKDIR /usr/src/app

# Set ownership and switch to non-root user
RUN chown nodeuser:nodejs /usr/src/app
USER nodeuser

# Copy package files with correct ownership
COPY --chown=nodeuser:nodejs package*.json ./
COPY --chown=nodeuser:nodejs tsconfig.json ./

# Install dependencies
RUN npm ci

# Copy source code with correct ownership
COPY --chown=nodeuser:nodejs . .

# Expose development port
EXPOSE 3001

# Start development server with hot reload
CMD ["npm", "run", "dev"]

# Stage 3: Production
FROM node:20-alpine AS production

# Install production dependencies and create non-root user
RUN apk add --no-cache dumb-init && \
    addgroup -S nodejs && \
    adduser -S nodeuser -G nodejs

WORKDIR /usr/src/app

# Set ownership and switch to non-root user
RUN chown nodeuser:nodejs /usr/src/app
USER nodeuser

# Copy package files with correct ownership and install production dependencies
COPY --chown=nodeuser:nodejs package*.json ./
RUN npm ci --only=production

# Copy built files from builder with correct ownership
COPY --chown=nodeuser:nodejs --from=builder /usr/src/app/dist ./dist

# Expose production port
EXPOSE 3001

# Use dumb-init as entrypoint
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# Start production server
CMD ["node", "dist/index.js"]


