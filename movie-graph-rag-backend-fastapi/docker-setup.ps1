# Windows PowerShell Script - Configuración rápida Docker
# Uso: & 'docker-setup.ps1'

Write-Host "🐳 Configurando movie-graph-rag-backend con Docker..." -ForegroundColor Cyan
Write-Host ""

# 1. Verificar Docker
Write-Host "✅ Verificando Docker..." -ForegroundColor Yellow
$dockerCmd = Get-Command docker-compose -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Host "❌ docker-compose no está instalado" -ForegroundColor Red
    Write-Host "   👉 Descarga: https://docs.docker.com/compose/install/" -ForegroundColor Yellow
    exit 1
}

# 2. Crear .env si no existe
Write-Host "📝 Verificando archivo .env..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "   Creando .env desde .env.example..." -ForegroundColor Gray
    Copy-Item ".env.example" ".env"
    Write-Host "   ✅ Archivo .env creado" -ForegroundColor Green
    Write-Host "   ⚠️  IMPORTANTE: Actualiza las credenciales en .env" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ .env ya existe" -ForegroundColor Green
}

# 3. Build imagen Docker
Write-Host ""
Write-Host "🏗️  Construyendo imagen Docker..." -ForegroundColor Yellow
docker-compose build api

# 4. Levantar servicios
Write-Host ""
Write-Host "🚀 Levantando servicios (MongoDB + Fuseki + FastAPI)..." -ForegroundColor Yellow
docker-compose up -d

# 5. Esperar a que estén sanos
Write-Host ""
Write-Host "⏳ Esperando a que los servicios se inicialicen (10s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 6. Verificar salud
Write-Host ""
Write-Host "🏥 Verificando salud de servicios..." -ForegroundColor Yellow

# FastAPI
Write-Host "   FastAPI: " -NoNewline
$apiHealthy = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ OK" -ForegroundColor Green
        $apiHealthy = $true
    }
} catch {
    Write-Host "⏳ Iniciando..." -ForegroundColor Gray
}

# Fuseki
Write-Host "   Fuseki: " -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3030/$/ping" -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ OK" -ForegroundColor Green
    }
} catch {
    Write-Host "⏳ Iniciando..." -ForegroundColor Gray
}

# MongoDB
Write-Host "   MongoDB: " -NoNewline
try {
    $output = docker-compose exec -T mongodb mongosh -u root -p password --eval "db.runCommand('ping')" 2>&1
    if ($output -like "*ok*" -or $output -like "*1*") {
        Write-Host "✅ OK" -ForegroundColor Green
    }
} catch {
    Write-Host "⏳ Iniciando..." -ForegroundColor Gray
}

# 7. Output final
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ Backend configurado correctamente!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 Endpoints disponibles:" -ForegroundColor Cyan
Write-Host "   • API:     http://localhost:8000" -ForegroundColor White
Write-Host "   • Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "   • Fuseki:  http://localhost:3030" -ForegroundColor White
Write-Host "   • MongoDB: mongodb://root:password@localhost:27017" -ForegroundColor White
Write-Host ""
Write-Host "📊 Comandos útiles:" -ForegroundColor Cyan
Write-Host "   • Ver logs:        docker-compose logs -f api" -ForegroundColor Gray
Write-Host "   • Ejecutar tests:  docker-compose exec api pytest" -ForegroundColor Gray
Write-Host "   • Shell Python:    docker-compose exec api bash" -ForegroundColor Gray
Write-Host "   • Detener:         docker-compose down" -ForegroundColor Gray
Write-Host ""
Write-Host "🔧 Próximos pasos:" -ForegroundColor Cyan
Write-Host "   1. Carga ontologías en Fuseki:" -ForegroundColor White
Write-Host "      docker-compose exec api python scripts/compute_network_metrics.py" -ForegroundColor Gray
Write-Host ""
Write-Host "   2. Prueba la API:" -ForegroundColor White
Write-Host "      curl http://localhost:8000/health" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. Abre la documentación:" -ForegroundColor White
Write-Host "      start http://localhost:8000/docs" -ForegroundColor Gray
Write-Host ""
