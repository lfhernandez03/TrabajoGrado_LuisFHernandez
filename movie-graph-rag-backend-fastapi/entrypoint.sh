#!/bin/bash
set -e

echo "[$(date)] Starting CineSemantico services..."

# ─── Start Fuseki in background ────────────────────────────────────────────────
# Fuseki is embedded in this container and connects to the pre-loaded TDB2
# database baked into the image at /fuseki/databases/movies.
echo "[$(date)] Starting Fuseki server with pre-loaded TDB2 data..."

FUSEKI_BASE=/fuseki \
java -Xmx180m -Xms64m \
    -jar /jena-fuseki/fuseki-server.jar \
    --port 3030 \
    --configFile /fuseki/configuration/movies.ttl \
    &

# ─── Wait for Fuseki to be ready ───────────────────────────────────────────────
echo "[$(date)] Waiting for Fuseki to be ready..."
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
  if wget --quiet --tries=1 --spider http://localhost:3030/$/ping 2>/dev/null; then
    echo "[$(date)] Fuseki is ready!"
    break
  fi
  echo "[$(date)] Fuseki not ready yet... (attempt $((attempt + 1))/$max_attempts)"
  sleep 2
  attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
  echo "[$(date)] Fuseki failed to start after $((max_attempts * 2))s"
  exit 1
fi

# ─── Start FastAPI ─────────────────────────────────────────────────────────────
# MongoDB is external (Atlas), so no local wait needed.
# Render sets $PORT; fall back to 8000 for local runs.
echo "[$(date)] Starting FastAPI application on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
