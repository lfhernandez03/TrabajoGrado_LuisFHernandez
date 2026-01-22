# Script simple para actualizar datos en GraphDB
# Uso: .\scripts\update-data.ps1

$GRAPHDB_URL = "http://localhost:7200"
$REPO_NAME = "Cine"

# Obtener ruta base del workspace
$ScriptDir = Split-Path -Parent $PSCommandPath
$WorkspaceRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$ONTOLOGIES_DIR = Join-Path $WorkspaceRoot "movie-graph-rag-ontologies\data\ontologies"

Write-Host "=== Actualizando datos en GraphDB ===" -ForegroundColor Cyan
Write-Host ""

# Verificar GraphDB
Write-Host "[1/3] Verificando GraphDB..." -ForegroundColor Blue
try {
    $null = Invoke-WebRequest -Uri "$GRAPHDB_URL/rest/repositories" -UseBasicParsing -TimeoutSec 5
    Write-Host "OK - GraphDB respondiendo" -ForegroundColor Green
} catch {
    Write-Host "ERROR - GraphDB no responde en $GRAPHDB_URL" -ForegroundColor Red
    Write-Host "Ejecuta: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

# Limpiar datos existentes
Write-Host ""
Write-Host "[2/3] Limpiando datos anteriores..." -ForegroundColor Blue
try {
    $clearUri = "$GRAPHDB_URL/repositories/$REPO_NAME/statements"
    Invoke-RestMethod -Uri $clearUri -Method Delete -UseBasicParsing | Out-Null
    Write-Host "OK - Datos anteriores eliminados" -ForegroundColor Green
} catch {
    Write-Host "WARNING - No se pudieron limpiar datos (puede que el repo no exista)" -ForegroundColor Yellow
    Write-Host "Crea el repositorio '$REPO_NAME' manualmente en http://localhost:7200" -ForegroundColor Yellow
    exit 1
}

# Cargar datos
Write-Host ""
Write-Host "[3/3] Cargando ontologias y datos..." -ForegroundColor Blue

$files = @(
    "$ONTOLOGIES_DIR\base\movie-ontology.ttl",
    "$ONTOLOGIES_DIR\base\context-ontology.ttl",
    "$ONTOLOGIES_DIR\bridge\bridge-ontology.ttl",
    "$ONTOLOGIES_DIR\instances\movies_data.ttl",
    "$ONTOLOGIES_DIR\instances\contexts_data.ttl",
    "$ONTOLOGIES_DIR\instances\bridge_data.ttl"
)

$loaded = 0
foreach ($file in $files) {
    if (Test-Path $file) {
        $fileName = Split-Path $file -Leaf
        Write-Host "  - Cargando $fileName..." -NoNewline
        
        try {
            $content = Get-Content -Path $file -Raw -Encoding UTF8
            $uploadUri = "$GRAPHDB_URL/repositories/$REPO_NAME/statements"
            Invoke-RestMethod -Uri $uploadUri -Method Post -Body $content -ContentType "application/x-turtle" -UseBasicParsing | Out-Null
            Write-Host " OK" -ForegroundColor Green
            $loaded++
        } catch {
            Write-Host " ERROR" -ForegroundColor Red
            Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "  - FALTA: $file" -ForegroundColor Red
    }
}

# Resumen
Write-Host ""
Write-Host "=== Resumen ===" -ForegroundColor Cyan
Write-Host "Archivos cargados: $loaded de $($files.Count)" -ForegroundColor $(if($loaded -eq $files.Count){"Green"}else{"Yellow"})

# Contar tripletas
try {
    $size = Invoke-RestMethod -Uri "$GRAPHDB_URL/repositories/$REPO_NAME/size" -UseBasicParsing
    Write-Host "Total tripletas: $size" -ForegroundColor Green
} catch {
    Write-Host "No se pudo obtener el total de tripletas" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Listo! Accede a: $GRAPHDB_URL" -ForegroundColor Cyan
Write-Host ""
