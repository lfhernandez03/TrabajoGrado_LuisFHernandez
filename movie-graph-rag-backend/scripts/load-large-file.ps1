# Script para cargar archivos TTL grandes dividiendolos en chunks
# Uso: .\scripts\load-large-file.ps1

param(
    [string]$FilePath = "C:\Users\luish\Documents\GitHub\TrabajoGrado_LuisFHernandez\movie-graph-rag-ontologies\data\ontologies\instances\movies_data.ttl",
    [int]$LinesPerChunk = 1000
)

$GRAPHDB_URL = "http://localhost:7200"
$REPO_NAME = "Cine"

Write-Host "=== Cargando archivo grande en chunks ===" -ForegroundColor Cyan
Write-Host "Archivo: $FilePath" -ForegroundColor White
Write-Host "Lineas por chunk: $LinesPerChunk" -ForegroundColor White
Write-Host ""

if (-not (Test-Path $FilePath)) {
    Write-Host "ERROR: Archivo no encontrado: $FilePath" -ForegroundColor Red
    exit 1
}

# Leer el archivo
Write-Host "[1/3] Leyendo archivo..." -ForegroundColor Blue
$lines = Get-Content -Path $FilePath -Encoding UTF8
$totalLines = $lines.Count
Write-Host "Total de lineas: $totalLines" -ForegroundColor Green

# Extraer prefijos (lineas que empiezan con @prefix)
$prefixes = $lines | Where-Object { $_ -match '^@prefix' }
$dataLines = $lines | Where-Object { $_ -notmatch '^@prefix' -and $_ -notmatch '^@base' -and $_.Trim() -ne '' }

Write-Host "Prefijos encontrados: $($prefixes.Count)" -ForegroundColor Green
Write-Host "Lineas de datos: $($dataLines.Count)" -ForegroundColor Green

# Calcular chunks
$totalChunks = [Math]::Ceiling($dataLines.Count / $LinesPerChunk)
Write-Host ""
Write-Host "[2/3] Dividiendo en $totalChunks chunks..." -ForegroundColor Blue

# Cargar chunks
Write-Host ""
Write-Host "[3/3] Cargando chunks..." -ForegroundColor Blue

$uploadUri = "$GRAPHDB_URL/repositories/$REPO_NAME/statements"
$successCount = 0

for ($i = 0; $i -lt $totalChunks; $i++) {
    $start = $i * $LinesPerChunk
    $end = [Math]::Min($start + $LinesPerChunk - 1, $dataLines.Count - 1)
    $chunkLines = $dataLines[$start..$end]
    
    # Construir chunk con prefijos
    $chunk = @()
    $chunk += $prefixes
    $chunk += ""
    $chunk += $chunkLines
    
    $content = $chunk -join "`n"
    
    Write-Host "  Chunk $($i+1)/$totalChunks (lineas $start-$end)..." -NoNewline
    
    try {
        Invoke-RestMethod -Uri $uploadUri -Method Post -Body $content -ContentType "application/x-turtle" -UseBasicParsing | Out-Null
        Write-Host " OK" -ForegroundColor Green
        $successCount++
    } catch {
        Write-Host " ERROR" -ForegroundColor Red
        Write-Host "    $($_.Exception.Message)" -ForegroundColor Red
    }
    
    # Pequeña pausa para no saturar GraphDB
    Start-Sleep -Milliseconds 100
}

# Resumen
Write-Host ""
Write-Host "=== Resumen ===" -ForegroundColor Cyan
Write-Host "Chunks cargados: $successCount de $totalChunks" -ForegroundColor $(if($successCount -eq $totalChunks){"Green"}else{"Yellow"})

# Contar tripletas
try {
    $size = Invoke-RestMethod -Uri "$GRAPHDB_URL/repositories/$REPO_NAME/size" -UseBasicParsing
    Write-Host "Total tripletas: $size" -ForegroundColor Green
} catch {
    Write-Host "No se pudo obtener el total de tripletas" -ForegroundColor Yellow
}

Write-Host ""
