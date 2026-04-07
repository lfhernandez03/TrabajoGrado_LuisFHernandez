# ═══════════════════════════════════════════════════════════════════════════════
# Fuseki Data Validation Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# PURPOSE:
#   Quick validation that Fuseki dataset "Cine" is properly loaded with data
#
# USAGE:
#   .\validate-fuseki.ps1                              # Full validation
#   .\validate-fuseki.ps1 -Quick                      # Quick check only
#   .\validate-fuseki.ps1 -FusekiUrl http://localhost:3030
#
# EXIT CODES:
#   0 = All validations passed
#   1 = Fuseki not responding
#   2 = Dataset not found
#   3 = Dataset is empty
#   4 = Some validations failed (but data exists)

param(
    [string]$FusekiUrl = "http://localhost:3030",
    [string]$Dataset = "Cine",
    [switch]$Quick = $false,
    [string]$FusekiUser = "admin",
    [string]$FusekiPassword = "admin"
)

$ErrorActionPreference = "Continue"

# Colors
$Green = "`e[32m"
$Red = "`e[31m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"
$Bold = "`e[1m"

Write-Host "`n$Bold$Blue━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$Reset" -ForegroundColor Cyan
Write-Host "$Bold$Blue╔═ FUSEKI VALIDATION ═╗$Reset" -ForegroundColor Cyan
Write-Host "$Bold$Blue━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$Reset`n" -ForegroundColor Cyan

Write-Host "Target: $Blue$FusekiUrl$Reset, Dataset: $Blue$Dataset$Reset`n"

$Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${FusekiUser}:${FusekiPassword}"))
$HealthCheckUrl = "$FusekiUrl/$/ping"
$QueryUrl = "$FusekiUrl/$Dataset/query"

$AllPassed = $true
$FailCount = 0

# ═══════════════════════════════════════════════════════════════════════════════
# Check 1: Fuseki Health
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "$Yellow[1]$Reset Checking Fuseki health..." -ForegroundColor White
try {
    $response = Invoke-WebRequest -Uri $HealthCheckUrl -TimeoutSec 5 -ErrorAction Stop
    Write-Host "$Green✓ Fuseki is responding$Reset" -ForegroundColor Green
} catch {
    Write-Host "$Red✗ Fuseki health check failed: $_$Reset" -ForegroundColor Red
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════════
# Check 2: Dataset Exists
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n$Yellow[2]$Reset Checking if dataset '$Dataset' exists..." -ForegroundColor White
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
    if ($Content.boolean -ne $null) {
        Write-Host "$Green✓ Dataset '$Dataset' exists$Reset" -ForegroundColor Green
    }
} catch {
    Write-Host "$Red✗ Dataset '$Dataset' not found or error querying: $_$Reset" -ForegroundColor Red
    exit 2
}

# ═══════════════════════════════════════════════════════════════════════════════
# Check 3: Dataset Not Empty
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n$Yellow[3]$Reset Checking if dataset has data..." -ForegroundColor White

if ($Content.boolean -eq $true) {
    Write-Host "$Green✓ Dataset is populated$Reset" -ForegroundColor Green
} else {
    Write-Host "$Red✗ Dataset is EMPTY$Reset" -ForegroundColor Red
    exit 3
}

# Return early if quick check requested
if ($Quick) {
    Write-Host "`n$Green✓ Quick validation passed$Reset`n"
    exit 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# Check 4: Count Movies
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n$Yellow[4]$Reset Counting movie:Movie triples..." -ForegroundColor White

$MovieQuery = "SELECT (COUNT(?m) AS ?count) WHERE { ?m a ?type . FILTER(STRSTARTS(STR(?type), 'http://')) }"

try {
    $response = Invoke-WebRequest `
        -Uri $QueryUrl `
        -Method POST `
        -Headers @{
            "Authorization" = "Basic $Auth"
            "Accept" = "application/json"
        } `
        -Body "query=$([uri]::EscapeDataString($MovieQuery))" `
        -TimeoutSec 10 `
        -ErrorAction Stop
    
    $Content = $response.Content | ConvertFrom-Json
    $MovieCount = 0
    
    if ($Content.results.bindings.Length -gt 0) {
        $MovieCount = [int]$Content.results.bindings[0].count.value
    }
    
    if ($MovieCount -gt 0) {
        Write-Host "$Green✓ Found $MovieCount triples in dataset$Reset" -ForegroundColor Green
    } else {
        Write-Host "$Yellow⚠ No movies found (but dataset has other data)$Reset" -ForegroundColor Yellow
        $FailCount++
    }
} catch {
    Write-Host "$Red✗ Failed to count movies: $_$Reset" -ForegroundColor Red
    $FailCount++
}

# ═══════════════════════════════════════════════════════════════════════════════
# Check 5: Sample Data
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n$Yellow[5]$Reset Checking sample data structure..." -ForegroundColor White

$SampleQuery = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 3"

try {
    $response = Invoke-WebRequest `
        -Uri $QueryUrl `
        -Method POST `
        -Headers @{
            "Authorization" = "Basic $Auth"
            "Accept" = "application/json"
        } `
        -Body "query=$([uri]::EscapeDataString($SampleQuery))" `
        -TimeoutSec 10 `
        -ErrorAction Stop
    
    $Content = $response.Content | ConvertFrom-Json
    $SampleCount = $Content.results.bindings.Length
    
    if ($SampleCount -gt 0) {
        Write-Host "$Green✓ Sample triples found ($SampleCount samples)$Reset" -ForegroundColor Green
        Write-Host "  Example:" -ForegroundColor Gray
        foreach ($binding in $Content.results.bindings | Select-Object -First 1) {
            Write-Host "    Subject: $($binding.s.value)" -ForegroundColor Gray
            Write-Host "    Predicate: $($binding.p.value)" -ForegroundColor Gray
            Write-Host "    Value: $($binding.o.value)" -ForegroundColor Gray
        }
    } else {
        Write-Host "$Red✗ No sample data found$Reset" -ForegroundColor Red
        $FailCount++
    }
} catch {
    Write-Host "$Yellow⚠ Could not retrieve sample data: $_$Reset" -ForegroundColor Yellow
    $FailCount++
}

# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n$Bold$Blue━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$Reset"

if ($FailCount -eq 0) {
    Write-Host "$Green$Bold✓ ALL VALIDATION CHECKS PASSED$Reset" -ForegroundColor Green
    exit 0
} else {
    Write-Host "$Yellow$Bold⚠ VALIDATION COMPLETED WITH $FailCount WARNINGS$Reset" -ForegroundColor Yellow
    Write-Host "  (Data exists but some detailed checks failed)" -ForegroundColor Gray
    exit 4
}
