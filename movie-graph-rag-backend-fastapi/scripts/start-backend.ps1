param(
    [int]$Port = 8000,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "No se encontró el entorno virtual del backend en: $PythonExe"
}

Push-Location $ProjectRoot
try {
    if (-not $NoReload) {
        Write-Host "Iniciando backend con reload en puerto $Port" -ForegroundColor Cyan
        & $PythonExe -m uvicorn app.main:app --reload --port $Port
    }
    else {
        Write-Host "Iniciando backend sin reload en puerto $Port" -ForegroundColor Cyan
        & $PythonExe -m uvicorn app.main:app --port $Port
    }
}
finally {
    Pop-Location
}
