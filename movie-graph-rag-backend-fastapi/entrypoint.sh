#!/bin/bash
set -e

echo "[$(date)] Starting CineSemantico services..."

# Wait for Fuseki to be healthy
echo "[$(date)] Waiting for Fuseki to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
  if wget --quiet --tries=1 --spider http://fuseki:3030/$/ping 2>/dev/null; then
    echo "[$(date)] ✅ Fuseki is ready!"
    break
  fi
  echo "[$(date)] Fuseki not ready yet... (attempt $((attempt + 1))/$max_attempts)"
  sleep 2
  attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
  echo "[$(date)] ❌ Fuseki failed to start"
  exit 1
fi

# Wait for MongoDB
echo "[$(date)] Waiting for MongoDB to be ready..."
attempt=0
while [ $attempt -lt $max_attempts ]; do
  if nc -z mongodb 27017 2>/dev/null; then
    echo "[$(date)] ✅ MongoDB is ready!"
    break
  fi
  echo "[$(date)] MongoDB not ready yet... (attempt $((attempt + 1))/$max_attempts)"
  sleep 2
  attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
  echo "[$(date)] ❌ MongoDB failed to start"
  exit 1
fi

# Check if Fuseki dataset exists, if not initialize it
echo "[$(date)] Checking if Fuseki dataset '${FUSEKI_DATASET:-movies}' exists..."
DATASET_CHECK=$(wget -q -O - "http://fuseki:3030/" 2>/dev/null || echo "")

if echo "$DATASET_CHECK" | grep -q "${FUSEKI_DATASET:-movies}"; then
  echo "[$(date)] ✅ Dataset already exists"
else
  echo "[$(date)] ⚠️  Dataset not found. Create it in Fuseki UI or run pipeline.py"
fi

# Optional: Load data from pipeline if in the right environment
# ⚠️  DISABLED: Render kills the container after ~30s without response
# if [ "$APP_ENV" = "production" ] && [ -f "/app/data/scripts/pipeline.py" ]; then
#   echo "[$(date)] Production mode detected. Attempting to load initial data..."
#   cd /app && python data/scripts/pipeline.py --max-movies 5000 --skip-enrichment --no-incremental 2>&1 || true
# fi

echo "[$(date)] Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-8000}
