# Dockerfile for EA Portal - Static HTML serving only
FROM python:3.11-slim AS builder

WORKDIR /app
ENV PYTHONPATH=/app/src:/app

# Copy source files needed for build
COPY src/ src/
COPY portal/ portal/
COPY ea_diagrams/ ea_diagrams/
COPY archi_inputs/ archi_inputs/
COPY ea_inputs/views/ ea_inputs/views/
COPY ea_inputs/02_IT_systems/ ea_inputs/02_IT_systems/
COPY ea_inputs/04_projects/ ea_inputs/04_projects/

# Install dependencies for portal build
COPY pyproject.toml ./
RUN python -c "import re, subprocess, sys, tomllib; \
    dependencies = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; \
    required = {'pandas', 'openpyxl', 'pyyaml', 'jsonschema', 'lxml'}; \
    declared = {re.match(r'[\w.-]+', dependency).group().lower(): dependency for dependency in dependencies}; \
    missing = required - declared.keys(); \
    missing and sys.exit('Missing portal dependencies in pyproject.toml: ' + ', '.join(sorted(missing))); \
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', *[declared[name] for name in sorted(required)]])"

# Build the portal (generates static HTML)
RUN python portal/build.py

# Production stage - lightweight nginx server
FROM nginx:1.27-alpine

# Copy hardened nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static files from builder
COPY --from=builder /app/portal/dist /usr/share/nginx/html

# Nginx runs on port 80 by default
EXPOSE 80

# No environment variables needed - it's just static HTML!
