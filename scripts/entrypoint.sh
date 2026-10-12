#!/usr/bin/env bash
set -e

# ==============================================================================
# Pluvira Container Initialization & Dynamic Permission Auto-Healing Entrypoint
# ==============================================================================

# If running as root, perform dynamic PUID/PGID user mapping and permission auto-healing
if [ "$(id -u)" = "0" ]; then
    PUID="${PUID:-1000}"
    PGID="${PGID:-1000}"

    # Adjust group ID if different
    if [ "$(id -g appuser 2>/dev/null || echo '')" != "$PGID" ]; then
        groupmod -o -g "$PGID" appgroup 2>/dev/null || groupadd -o -g "$PGID" appgroup 2>/dev/null || true
    fi

    # Adjust user ID if different
    if [ "$(id -u appuser 2>/dev/null || echo '')" != "$PUID" ]; then
        usermod -o -u "$PUID" -g "$PGID" appuser 2>/dev/null || useradd -o -u "$PUID" -g "$PGID" -m -s /bin/bash appuser 2>/dev/null || true
    fi

    # Ensure runtime persistence and RAM disk directories exist
    mkdir -p /app/config /app/data /dev/shm/pluvira

    # Fix ownership on mounted volumes and runtime paths to prevent [Errno 13] Permission denied
    chown -R "$PUID:$PGID" /app/config /app/data /dev/shm/pluvira /app/bin 2>/dev/null || true
    chmod 775 /app/config /app/data /dev/shm/pluvira 2>/dev/null || true

    # Drop root privileges and execute application command as non-root appuser
    exec gosu "$PUID:$PGID" "$@"
fi

# If already running as unprivileged user, execute command directly
exec "$@"
