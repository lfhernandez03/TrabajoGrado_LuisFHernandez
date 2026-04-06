#!/bin/bash
set -e

echo "[$(date)] Starting CineSemantico services..."

# Wait for Fuseki to be healthy
echo "[$(date)] Waiting for Fuseki to be ready..."
max_attempts=60
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

# Check if dataset exists; if not, create and load from dump
DATASET="${FUSEKI_DATASET:-movies}"
echo "[$(date)] Checking if dataset '$DATASET' exists and has data..."

DATASET_CHECK=$(wget -q -O - "http://fuseki:3030/$/datasets" 2>/dev/null || echo "")

if echo "$DATASET_CHECK" | grep -q "\"$DATASET\""; then
  echo "[$(date)] ℹ️  Dataset exists. Checking if it has data..."
  
  # Try a simple query to see if dataset has data
  TRIPLE_COUNT=$(wget -q -O - "http://fuseki:3030/$DATASET/query?query=SELECT%20COUNT%28%3Fs%29%20WHERE%20%7B%3Fs%20%3Fp%20%3Fo%7D" 2>/dev/null || echo "0")
  
  if echo "$TRIPLE_COUNT" | grep -q '"value" : "0"'; then
    echo "[$(date)] ⚠️  Dataset is empty. Loading from dump..."
    if [ -f "/app/fuseki-init/movies-dump.ttl" ]; then
      echo "[$(date)] Loading TTL dump into Fuseki..."
      curl -X POST "http://fuseki:3030/$DATASET/upload" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@/app/fuseki-init/movies-dump.ttl" 2>/dev/null || echo "Upload attempt completed"
      echo "[$(date)] ✅ Dump loaded (or attempted)"
    else
      echo "[$(date)] [WARN] No dump file found at /app/fuseki-init/movies-dump.ttl"
    fi
  else
    echo "[$(date)] ✅ Dataset has data. Skipping load."
  fi
else
  echo "[$(date)] [WARN] Dataset '$DATASET' not found. Create it manually or run pipeline."
fi

echo "[$(date)] Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-8000}

