# ==============================================================================
# Stage 1: Build Svelte 5 SPA Frontend Assets
# ==============================================================================
FROM --platform=$BUILDPLATFORM node:22-slim AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Build Python dependencies and virtual environment
# ==============================================================================
FROM python:3.12-slim AS python-builder

WORKDIR /build

# Install system build dependencies required for compiling any C-extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment for isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Stage 3: Final minimal runner image
# ==============================================================================
FROM python:3.12-slim AS runner

ARG TARGETPLATFORM
ARG APP_VERSION=0.0.0.dev0
ARG GIT_HASH=unknown

# Install curl for container health check probe and gosu for non-root privilege de-escalation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group (UID/GID 1000) for security and NAS storage alignment
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

WORKDIR /app
RUN chown appuser:appgroup /app

# Copy the pre-compiled virtual environment from the builder stage
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the application source code with correct ownership
COPY --chown=appuser:appgroup backend/ ./backend/.
COPY --from=frontend-builder --chown=appuser:appgroup /build/frontend/dist ./frontend/dist/.

# Create configuration, data, and bin directories, write VERSION metadata, and stage Pro binary
RUN mkdir -p /app/config /app/data /app/bin && \
    echo "${APP_VERSION}" > /app/VERSION && \
    chown -R appuser:appgroup /app/config /app/data /app/bin /app/VERSION
COPY --chown=appuser:appgroup bin/ /app/bin_staging/
RUN if [ -f "/app/bin_staging/${TARGETPLATFORM}/pluvira-pro" ]; then \
        mv "/app/bin_staging/${TARGETPLATFORM}/pluvira-pro" /app/bin/pluvira-pro && \
        chmod 0755 /app/bin/pluvira-pro; \
    elif [ -f "/app/bin_staging/pluvira-pro" ]; then \
        mv "/app/bin_staging/pluvira-pro" /app/bin/pluvira-pro && \
        chmod 0755 /app/bin/pluvira-pro; \
    fi && rm -rf /app/bin_staging

# Copy entrypoint script with execution permissions
COPY scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod 0755 /app/entrypoint.sh

# Healthcheck verification probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8585/health || exit 1

# Expose the default FastAPI port
EXPOSE 8585

# Standardized environment variables for Docker execution
ENV PLUVIRA_VERSION=${APP_VERSION}
ENV PLUVIRA_GIT_HASH=${GIT_HASH}
ENV PLUVIRA_CONFIG_DIR=/app/config
ENV PLUVIRA_DATA_DIR=/app/data
ENV PLUVIRA_TEMP_DIR=/dev/shm/pluvira
ENV PLUVIRA_API_HOST=0.0.0.0
ENV PLUVIRA_API_PORT=8585

# Entrypoint for automatic permission healing and unprivileged gosu execution
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8585"]