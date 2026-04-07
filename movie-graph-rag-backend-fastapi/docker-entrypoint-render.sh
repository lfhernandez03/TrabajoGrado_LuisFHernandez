#!/bin/bash
set -e

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# =============================================================================
# Start Fuseki Server
# =============================================================================
log_info "Starting Apache Fuseki server..."

# Crear directorio TDB2 antes de arrancar Fuseki
mkdir -p /fuseki/databases

export FUSEKI_BASE=/fuseki
cd /opt/fuseki

# Heap reducido para caber dentro del límite de 512MB de Render free tier:
# JVM ~180m heap + ~100m overhead + Python/uvicorn ~150m ≈ 430MB total
java -Xmx180m -Xms64m \
    -jar fuseki-server.jar \
    --port 3030 \
    --tdb2 \
    --update \
    --loc=/fuseki/databases \
    /${FUSEKI_DATASET} \
    >/tmp/fuseki.log 2>&1 &

FUSEKI_PID=$!
log_info "Fuseki started with PID=$FUSEKI_PID"

# =============================================================================
# Wait for Fuseki to be Ready
# =============================================================================
log_info "Waiting for Fuseki to respond on http://localhost:3030..."

READY=0
MAX_ATTEMPTS=75
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    # Detectar crash inmediato: si el proceso ya no existe, no seguir esperando
    if ! kill -0 $FUSEKI_PID 2>/dev/null; then
        log_error "❌ Fuseki process (PID=$FUSEKI_PID) died. Logs:"
        cat /tmp/fuseki.log
        exit 1
    fi

    if wget -q --spider "http://localhost:3030/\$/ping" 2>/dev/null; then
        READY=1
        log_info "✅ Fuseki is ready!"
        break
    fi

    ATTEMPT=$((ATTEMPT + 1))
    if [ $((ATTEMPT % 5)) -eq 0 ]; then
        log_warn "Waiting for Fuseki... ($ATTEMPT/$MAX_ATTEMPTS)"
    fi
    sleep 2
done

if [ $READY -eq 0 ]; then
    log_error "❌ Fuseki failed to start after ${MAX_ATTEMPTS} attempts ($((MAX_ATTEMPTS * 2)) sec)"
    log_error "Fuseki logs:"
    cat /tmp/fuseki.log
    kill $FUSEKI_PID 2>/dev/null || true
    exit 1
fi

# =============================================================================
# Load Base Ontologies
# =============================================================================
log_info "Loading base ontology schemas..."

ONTOLOGY_FILES=(
    "/ontologies/base/movie-ontology.ttl"
    "/ontologies/base/context-ontology.ttl"
    "/ontologies/bridge/bridge-ontology.ttl"
)

for f in "${ONTOLOGY_FILES[@]}"; do
    if [ -f "$f" ]; then
        log_info "  Loading $(basename $f)..."
        if ! curl -sf -X POST "http://localhost:3030/${FUSEKI_DATASET}/data" \
             -H "Content-Type: text/turtle" \
             --data-binary "@$f" >/dev/null 2>&1; then
            log_error "Failed to load $f"
            kill $FUSEKI_PID 2>/dev/null || true
            exit 1
        fi
        log_info "  ✅ $(basename $f) loaded"
    fi
done

# =============================================================================
# Execute Pipeline (generates instance data)
# =============================================================================
log_info "Starting data pipeline to generate instance data..."

cd /app/scripts

# Check if pipeline.py exists
if [ ! -f "pipeline.py" ]; then
    log_warn "⚠️  pipeline.py not found at /app/scripts/pipeline.py, skipping data generation"
    log_warn "   Only base ontologies will be available"
else
    # Set environment for pipeline
    export FUSEKI_URL=http://localhost:3030
    export FUSEKI_DATASET=${FUSEKI_DATASET}
    export FUSEKI_USER=
    export FUSEKI_PASSWORD=""
    export PYTHONUNBUFFERED=1
    
    # Run pipeline with max 5000 movies on Render (balance between data & startup time)
    # Set via MAX_MOVIES env var, default to 5000
    MAX_MOVIES=${MAX_MOVIES:-5000}
    
    log_info "Running pipeline.py with --max-movies $MAX_MOVIES --skip-enrichment --no-incremental..."
    
    if python pipeline.py --max-movies $MAX_MOVIES --skip-enrichment --no-incremental 2>&1 | tee /tmp/pipeline.log; then
        log_info "✅ Pipeline completed successfully!"
    else
        log_error "⚠️  Pipeline failed (non-critical - base ontologies available)"
        log_error "Pipeline logs (last 30 lines):"
        tail -30 /tmp/pipeline.log
        # Don't exit - let FastAPI start anyway with just base ontologies
    fi
fi

# =============================================================================
# Start FastAPI Application
# =============================================================================
cd /app

log_info "Starting FastAPI on port ${PORT:-8000}..."
log_info "Fuseki available at: ${FUSEKI_URL}/${FUSEKI_DATASET}"

# Wait a moment for any Fuseki indexing
sleep 3

# Start FastAPI (runs in foreground)
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --access-log \
    --log-level info
