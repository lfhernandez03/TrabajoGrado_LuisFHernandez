#!/bin/bash
set -e

echo "[$(date)] Starting Fuseki with pre-loaded TDB2 data..."

cd /opt/fuseki
FUSEKI_BASE=/fuseki \
java -Xmx180m -Xms64m \
    -jar fuseki-server.jar \
    --port 3030 \
    >/tmp/fuseki-runtime.log 2>&1 \
    &
FUSEKI_PID=$!
cd /app

echo "[$(date)] Waiting for Fuseki..."
max=60
i=0
while [ $i -lt $max ]; do
    wget -q --spider http://localhost:3030/$/ping 2>/dev/null && echo "[$(date)] Fuseki ready!" && break
    i=$((i + 1))
    echo "[$(date)] Not ready yet ($i/$max)..."
    sleep 2
done

if [ $i -eq $max ]; then
    echo "[$(date)] ERROR: Fuseki failed to start. Log:"
    cat /tmp/fuseki-runtime.log
    exit 1
fi

echo "[$(date)] FUSEKI_URL=${FUSEKI_URL}"
echo "[$(date)] Starting FastAPI on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
