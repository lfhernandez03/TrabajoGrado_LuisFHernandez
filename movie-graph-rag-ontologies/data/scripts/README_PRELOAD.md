# 📚 Pre-Load Data to Fuseki - Setup Guide

> **Complete workflow for pre-loading movie graph data into Apache Fuseki before starting the FastAPI application**

## 🎯 Overview

The `movie-graph-rag-backend-fastapi` application requires data to be loaded into Apache Fuseki (RDF triple store) before it can operate. This guide provides step-by-step instructions to:

1. **Pre-load data locally** using the pipeline script
2. **Validate** Fuseki contains the correct data
3. **Start Docker** with confidence that data is ready

---

## 🚀 Quick Start (3 Steps)

### Step 1: Ensure Fuseki is Running

```powershell
# Terminal 1 - Start Fuseki standalone (or use docker-compose)
docker run -d -p 3030:3030 -e ADMIN_PASSWORD=admin \
  -e "JVM_ARGS=-Xmx2g" \
  --name fuseki-dev stain/jena-fuseki:latest
```

### Step 2: Load All Movie Data

```powershell
# Terminal 2 - Navigate to scripts folder
cd movie-graph-rag-ontologies/data/scripts

# Load all movies (full dataset, ~5-10 minutes)
.\pre-load.ps1

# Or load limited dataset for testing
.\pre-load.ps1 -MaxMovies 500
```

### Step 3: Verify Data & Start API

```powershell
# Verify Fuseki has data
.\validate-fuseki.ps1

# Now start FastAPI via Docker
cd movie-graph-rag-backend-fastapi
docker-compose -f docker-compose.local.yml up
```

---

## 📋 Detailed Usage

### Option 1: Full Pre-Load Workflow (Recommended)

**Scenario**: Starting development from scratch

```powershell
# 1. Start Fuseki (if not already running)
docker-compose -f docker-compose.local.yml up fuseki -d

# 2. Load all data into "Cine" dataset
cd movie-graph-rag-ontologies/data/scripts
.\pre-load.ps1

# 3. Verify data loaded successfully
.\validate-fuseki.ps1

# 4. Start full stack (API will connect to pre-loaded Fuseki)
cd ../../backend-fastapi
docker-compose -f docker-compose.local.yml up -d
```

### Option 2: Load Specific Movie Count (Testing)

**Scenario**: Quick test with smaller dataset

```powershell
cd movie-graph-rag-ontologies/data/scripts

# Load only 100 movies (fast: ~30 seconds)
.\pre-load.ps1 -MaxMovies 100

# Load 1000 movies (medium: ~2 minutes)
.\pre-load.ps1 -MaxMovies 1000

# Load all available (~5-10 minutes)
.\pre-load.ps1 -MaxMovies 0  # or just .\pre-load.ps1
```

### Option 3: Validate Without Loading

**Scenario**: Check if data is already loaded

```powershell
cd movie-graph-rag-ontologies/data/scripts

# Quick validation (exists + has data)
.\validate-fuseki.ps1 -Quick

# Full validation (detailed checks)
.\validate-fuseki.ps1

# Validate specific Fuseki instance
.\validate-fuseki.ps1 -FusekiUrl http://your-server:3030
```

---

## 🔍 What These Scripts Do

### `pre-load.ps1` 

**Performs:**
1. ✓ Validates Fuseki is running on `http://localhost:3030`
2. ✓ Executes `pipeline.py` to generate RDF from raw data
3. ✓ Loads 5 TTL files into the "Cine" dataset:
   - `movie-ontology.ttl` - Movie schema
   - `context-ontology.ttl` - Context schema
   - `bridge-ontology.ttl` - Bridge schema
   - `movies_data.ttl` - Movie instances (~160K triples)
   - `bridge_data.ttl` - Bridge instances (~18K triples)
4. ✓ Verifies dataset exists and has data

**Success Indicators:**
- Exit code: `0`
- Console shows: `✓ ALL CHECKS PASSED`
- Fuseki UI shows: Dataset "Cine" with millions of triples

**Failure Modes:**
- Exit code `1`: Fuseki not responding (start it first)
- Exit code `2`: Pipeline execution failed (check Python environment)
- Exit code `3`: Data loaded but verification query failed (rare)

---

### `validate-fuseki.ps1`

**Performs:**
1. ✓ Checks Fuseki is responding
2. ✓ Verifies "Cine" dataset exists
3. ✓ Confirms dataset is not empty
4. ✓ (Optional) Counts triples and shows sample data

**Quick Mode** (`-Quick` flag):
- Only does checks 1-3 (exits as soon as data exists)
- Useful in CI/CD to fast-fail early

**Full Mode** (default):
- Runs all checks + statistics
- Shows sample data from the graph
- Takes ~5-10 seconds

**Exit Codes:**
- `0`: All checks passed
- `1`: Fuseki not responding
- `2`: Dataset not found
- `3`: Dataset exists but is empty
- `4`: Data exists but some detailed checks failed (non-critical)

---

## 🛠️ Configuration

### Environment Variables

The scripts read from `.env` file in `movie-graph-rag-ontologies/`:

```env
# Default values (can override)
FUSEKI_URL=http://localhost:3030
FUSEKI_DATASET=Cine                    # Must match docker-compose!
FUSEKI_USER=admin
FUSEKI_PASSWORD=admin

# For pipeline.py specifically:
MONGO_URI=mongodb://...                # (Optional, used if skipping enrichment)
TMDB_API_KEY=...                       # (Required if --skip-enrichment not used)
OMDB_API_KEY=...                       # (Required if --skip-enrichment not used)
```

**Note**: The scripts use hardcoded Fuseki connection `http://localhost:3030` but respect env vars for credentials.

---

## 📊 Performance Expectations

| Mode | Movies | Time | File Size | Triples |
|------|--------|------|-----------|---------|
| Test | 100 | 30s | ~1 MB | 30K |
| Medium | 500 | 2m | ~5 MB | 150K |
| Full | All (~10K) | 5-10m | ~50 MB | 1.5M+ |

**JVM Memory**: Scripts assume Fuseki has at least **2GB** (`JVM_ARGS: -Xmx2g`)

---

## 🐳 Docker Integration

The scripts are designed to work with Docker Compose:

### Using Docker Data-Loader Service

If using the `data-loader` service in `docker-compose.local.yml`:

```yaml
data-loader:
  image: alpine:3
  depends_on:
    fuseki:
      condition: service_healthy
  volumes:
    - ../../movie-graph-rag-ontologies/data/ontologies:/ontologies:ro
  # ... curl commands to load TTL files
```

**This approach:**
- ✓ Automatic (runs during `docker-compose up`)
- ✓ No manual script needed
- ✓ Data persists in `fuseki_data_local` volume

**But Note:**
- ✗ Harder to debug (errors logged inside container)
- ✗ Data-loader reads PRE-GENERATED TTL files (must run `pipeline.py` first!)
- ✗ No control over movie count

### Recommended Approach

**Pre-load locally first, then use Docker:**

```powershell
# Step 1: Generate and load data locally
.\pre-load.ps1

# Step 2: Docker uses pre-loaded Fuseki volume
docker-compose -f docker-compose.local.yml up

# Step 3: API connects to pre-populated Fuseki
curl http://localhost:8000/health
```

---

## 🐛 Troubleshooting

### Fuseki Not Responding

```powershell
# Check if running
curl http://localhost:3030/$/ping

# If fails, start Fuseki
docker run -d -p 3030:3030 \
  -e ADMIN_PASSWORD=admin \
  -e "JVM_ARGS=-Xmx2g" \
  --name fuseki stain/jena-fuseki:latest
```

### Pipeline Execution Error

```powershell
# Verify Python environment
python --version  # Must be 3.11+

# Check if pipeline.py exists
ls pipeline.py

# Run with verbose logging
$ErrorActionPreference = "Continue"
python pipeline.py --max-movies 100
```

### Dataset Name Mismatch

**Symptom**: Error about dataset "movies" not found

**Fix**: Ensure consistency in `.env` and docker-compose:
```env
FUSEKI_DATASET=Cine  # Must match docker-compose config!
```

### Out of Memory (OOM)

**Symptom**: Fuseki crashes when loading large datasets

**Fix**: Increase JVM memory:
```dockerfile
ENV JVM_ARGS=-Xmx4g  # Increase to 4GB or 8GB
```

### Dataset Verification Fails

```powershell
# Debug by manually querying
$url = "http://localhost:3030/Cine/query"
$query = "SELECT COUNT(?s) WHERE { ?s ?p ?o }"
Invoke-WebRequest -Uri $url -Method POST `
  -Body "query=$([uri]::EscapeDataString($query))" `
  -Headers @{"Authorization"="Basic $(([Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes('admin:admin'))))"} |
  Select-Object -ExpandProperty Content | ConvertFrom-Json
```

---

## 📝 Dataset Details

### What Gets Loaded

The `pre-load.ps1` script executes `pipeline.py` which:

1. **Loads MovieLens data** (~10K movies with ratings, genres, cast)
2. **Enriches from APIs** (TMDb, OMDb - titles, budgets, revenue)
3. **Generates RDF** (owl:Thing, movie:Movie, context:UserContext, etc.)
4. **Creates Bridges** (compatibility scores, mood mappings, energy levels)
5. **Posts to Fuseki** (one dataset "Cine" with all data)

### Dataset Structure

```
Dataset: Cine
  ├── movie:Movie instances (~10K)
  ├── movie:Genre instances
  ├── movie:CrewMember instances
  ├── context:Mood instances
  ├── bridge:MovieContextBridge instances (~150K+)
  ├── Properties: title, genres, cast, ratings, release_date, etc.
  └── Total Triples: ~1.5M+
```

---

## ✅ Verification Checklist

After running `pre-load.ps1`:

- [ ] Exit code is `0`
- [ ] Console shows `✓ ALL CHECKS PASSED`
- [ ] Fuseki UI shows dataset "Cine"
- [ ] `validate-fuseki.ps1` runs without errors
- [ ] FastAPI logs show "Connected to Fuseki"
- [ ] `GET /health` returns 200 OK

---

## 🔗 Related Files

- **Pipeline**: [`movie-graph-rag-ontologies/data/scripts/pipeline.py`](../pipeline.py)
- **Config**: [`movie-graph-rag-ontologies/.env`](../../.env)
- **Docker**: [`movie-graph-rag-backend-fastapi/docker-compose.local.yml`](../../backend-fastapi/docker-compose.local.yml)
- **Docs**: [`movie-graph-rag-backend-fastapi/DOCKER_GUIDE.md`](../../backend-fastapi/DOCKER_GUIDE.md)

---

## 💡 Tips & Best Practices

1. **Always run `pre-load.ps1` before Docker** to catch data issues early
2. **Use `-MaxMovies 100` for quick CI/CD tests** (builds in ~30 sec)
3. **Keep Fuseki volume persistent**: Don't delete `fuseki_data_local` unless you want a fresh start
4. **Monitor Fuseki memory**: If loading >50K movies, increase to `-Xmx4g` or more
5. **Validate often**: Run `validate-fuseki.ps1 -Quick` in scripts/health checks

---

## 📊 Success Story

You'll know it's working when:

```powershell
PS> .\validate-fuseki.ps1
Checking Fuseki health...
✓ Fuseki is responding
Checking if dataset 'Cine' exists...
✓ Dataset 'Cine' exists
Checking if dataset has data...
✓ Dataset is populated
Counting movie:Movie triples...
✓ Found 1,234,567 triples in dataset

✓ ALL VALIDATION CHECKS PASSED
```

Then start the API:

```
FastAPI running on http://localhost:8000
Connected to Fuseki at http://fuseki:3030/Cine
Ready to serve requests!
```
