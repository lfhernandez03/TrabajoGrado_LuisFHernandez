# Windows PowerShell - Deploy a Vercel
# Uso: & '.\vercel-deploy.ps1'

Write-Host "🚀 Desplegando Next.js a Vercel..." -ForegroundColor Cyan
Write-Host ""

# 1. Verificar Vercel CLI
Write-Host "✅ Verificando Vercel CLI..." -ForegroundColor Yellow
$vercelCmd = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercelCmd) {
    Write-Host "❌ vercel no está instalado" -ForegroundColor Red
    Write-Host "   Instalando: npm install -g vercel" -ForegroundColor Yellow
    npm install -g vercel
}

# 2. Verificar autenticación
Write-Host "🔐 Verificando autenticación..." -ForegroundColor Yellow
$vercelConfig = Join-Path $env:APPDATA ".vercel"
if (-not (Test-Path $vercelConfig)) {
    Write-Host "   Requiere login:" -ForegroundColor Yellow
    vercel login
}

# 3. Crear .env.local
Write-Host "📝 Verificando .env.local..." -ForegroundColor Yellow
if (-not (Test-Path ".env.local")) {
    Write-Host "   Creando .env.local desde .env.example..." -ForegroundColor Gray
    Copy-Item ".env.example" ".env.local"
    Write-Host "   ⚠️  IMPORTANTE: Edita .env.local con tu URL de backend" -ForegroundColor Yellow
    Write-Host "   Abre .env.local y actualiza NEXT_PUBLIC_API_URL" -ForegroundColor Yellow
    exit 1
}

# 4. Build local
Write-Host ""
Write-Host "🏗️  Compilando Next.js localmente..." -ForegroundColor Yellow
npm run build

# 5. Seleccionar environment
Write-Host ""
Write-Host "📌 Selecciona el ambiente de deployment:" -ForegroundColor Cyan
Write-Host "   1) Preview (staging)" -ForegroundColor White
Write-Host "   2) Production" -ForegroundColor White

$envChoice = Read-Host "Selecciona (1 o 2)"

if ($envChoice -eq "2") {
    Write-Host ""
    Write-Host "🚨 CONFIRMACIÓN: Desplegando a PRODUCCIÓN" -ForegroundColor Red
    $confirm = Read-Host "¿Estás seguro? (yes/no)"
    
    if ($confirm -ne "yes") {
        Write-Host "Cancelado." -ForegroundColor Yellow
        exit 0
    }
    
    Write-Host "🚀 Desplegando a producción..." -ForegroundColor Yellow
    vercel deploy --prod
} else {
    Write-Host "🚀 Desplegando a preview..." -ForegroundColor Yellow
    vercel deploy
}

Write-Host ""
Write-Host "✅ Deployment completado!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Próximos pasos:" -ForegroundColor Cyan
Write-Host "   1. Verifica los logs: vercel logs" -ForegroundColor Gray
Write-Host "   2. Abre: vercel inspect [URL]" -ForegroundColor Gray
Write-Host "   3. En Vercel dashboard, configura variables si es necesario" -ForegroundColor Gray
Write-Host ""
