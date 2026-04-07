# ═══════════════════════════════════════════════════════════════════════════════
# Pre-Load Script for Fuseki Data
# ═══════════════════════════════════════════════════════════════════════════════
#
# PURPOSE:
#   1. Validates Fuseki is running on http://localhost:3030
#   2. Executes pipeline.py to generate and load ALL movie data
#   3. Verifies the "Cine" dataset was created and populated
#   4. Reports success/failure for use in docker-compose orchestration
#
# USAGE:
#   # Load all movies (full dataset)
#   .\pre-load.ps1
#
#   # Load limited movies for testing
#   .\pre-load.ps1 -MaxMovies 500
#
# REQUIREMENTS:
#   - Python 3.11+ installed and in PATH
#   - Fuseki running on http://localhost:3030
#   - .env file with FUSEKI_USER and FUSEKI_PASSWORD (if required)
#
# EXIT CODES:
#   0 = Success (data loaded)
#   1 = Fuseki not responding
#   2 = Pipeline execution failed
#   3 = Dataset verification failed

param(
    [int]$MaxMovies = 0  # 0 = load all movies
)

$ErrorActionPreference = "Stop"

# Colors for output
$Green = "`e[32m"
$Red = "`e[31m"
$Yellow = "`e[33m"
$Reset = "`e[0m"
$Bold = "`e[1m"

Write-Host "`n$Bold━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$Reset" -ForegroundColor Cyan
Write-Host "$Bold╔═ PRE-LOAD FUSEKI DATA SCRIPT ═╗$Reset" -ForegroundColor Cyan
Write-Host "$Bold━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$Reset" -ForegroundColor Cyan

# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Check Fuseki availability
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n$Yellow[STEP 1]$Reset Checking Fuseki connectivity..." -ForegroundColor White

$FusekiUrl = "http://localhost:3030"
$HealthCheckUrl = "$FusekiUrl/$/ping"

try {
    $response = Invoke-WebRequest -Uri $HealthCheckUrl -TimeoutSec 5 -ErrorAction Stop
    Write-Host "$Green✓ Fuseki is running$Reset" -ForegroundColor Green
} catch {
    Write-Host "$Red✗ Fuseki not responding at $FusekiUrl$Reset" -ForegroundColor Red
    Write-Host "  Start Fuseki first:" -ForegroundColor Yellow
    Write-Host "    docker-compose -f docker-compose.local.yml up fuseki" -ForegroundColor Cyan
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Execute Pipeline
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n$Yellow[STEP 2]$Reset Running pipeline.py..." -ForegroundColor White

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PipelineScript = Join-Path $ScriptDir "pipeline.py"

if (-not (Test-Path $PipelineScript)) {
    Write-Host "$Red✗ Pipeline script not found: $PipelineScript$Reset" -ForegroundColor Red
    exit 2
}

$PipelineArgs = @("$PipelineScript")
if ($MaxMovies -gt 0) {
    $PipelineArgs += "--max-movies"
    $PipelineArgs += $MaxMovies
    Write-Host "  Loading $MaxMovies movies..." -ForegroundColor Gray
} else {
    Write-Host "  Loading ALL movies..." -ForegroundColor Gray
}

try {
    & python @PipelineArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "$Red✗ Pipeline failed with exit code $LASTEXITCODE$Reset" -ForegroundColor Red
        exit 2
    }
    Write-Host "$Green✓ Pipeline completed successfully$Reset" -ForegroundColor Green
} catch {
    Write-Host "$Red✗ Error running pipeline: $_$Reset" -ForegroundColor Red
    exit 2
}

# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Verify Dataset
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n$Yellow[STEP 3]$Reset Verifying dataset 'Cine'..." -ForegroundColor White

$FusekiUser = $env:FUSEKI_USER ? $env:FUSEKI_USER : "admin"
$FusekiPassword = $env:FUSEKI_PASSWORD ? $env:FUSEKI_PASSWORD : "admin"
$Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${FusekiUser}:${FusekiPassword}"))

$QueryUrl = "$FusekiUrl/Cine/query"
$Query = "ASK { ?s ?p ?o }"

try {
    $response = Invoke-WebRequest `
        -Uri $QueryUrl `
        -Method POST `
        -Headers @{
            "Authorization" = "Basic $Auth"
            "Accept" = "application/json"
        } `
        -Body "query=$([uri]::EscapeDataString($Query))" `
        -TimeoutSec 10 `
        -ErrorAction Stop
    
    $Content = $response.Content | ConvertFrom-Json
    if ($Content.boolean -eq $true) {
        Write-Host "$Green✓ Dataset 'Cine' is populated with data$Reset" -ForegroundColor Green
    } else {
        Write-Host "$Red✗ Dataset 'Cine' exists but is empty$Reset" -ForegroundColor Red
        exit 3
    }
} catch {
    Write-Host "$Red✗ Failed to verify dataset: $_$Reset" -ForegroundColor Red
    exit 3
}

# ═══════════════════════════════════════════════════════════════════════════════
# Final Status
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n$Bold━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$Reset" -ForegroundColor Green
Write-Host "$Green$Bold✓ ALL CHECKS PASSED - Ready for docker-compose up$Reset" -ForegroundColor Green
Write-Host "$Bold━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$Reset`n" -ForegroundColor Green

exit 0
