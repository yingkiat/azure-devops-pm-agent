# Dockerfile for EA Portal - Static HTML serving only
FROM python:3.11-slim AS builder

WORKDIR /app

# Copy source files needed for build
COPY portal/ portal/
COPY ea_diagrams/ ea_diagrams/
COPY archi_inputs/ archi_inputs/
COPY ea_inputs/views/ ea_inputs/views/
COPY ea_inputs/02_IT_systems/ ea_inputs/02_IT_systems/

# Build the portal (generates static HTML)
RUN python portal/build.py

# Production stage - lightweight nginx server
FROM nginx:alpine

# Copy built static files from builder
COPY --from=builder /app/portal/dist /usr/share/nginx/html

# Nginx runs on port 80 by default
EXPOSE 80

# No environment variables needed - it's just static HTML!
