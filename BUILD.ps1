# BUILD.ps1 — Vektorium
# Executa na raiz do projeto: B:\Documentos Programas\App Carga Térmica\
# Uso: clique direito → "Executar com PowerShell"  OU  .\BUILD.ps1

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "=== VEKTORIUM BUILD ===" -ForegroundColor Cyan
Write-Host ""

# ---- 1. Versao atual ----
$pkg = Get-Content "electron\package.json" | ConvertFrom-Json
Write-Host "Versao: $($pkg.version)" -ForegroundColor Yellow

# ---- 2. Instalar dependencias Electron (se node_modules ausente) ----
if (-not (Test-Path "electron\node_modules")) {
    Write-Host ""
    Write-Host "[1/3] Instalando dependencias npm..." -ForegroundColor Cyan
    Push-Location electron
    npm install
    Pop-Location
} else {
    Write-Host "[1/3] Dependencias npm OK" -ForegroundColor Green
}

# ---- 3. Build Electron ----
Write-Host ""
Write-Host "[2/3] Buildando Electron (npm run build)..." -ForegroundColor Cyan
Push-Location electron
npm run build
$exitCode = $LASTEXITCODE
Pop-Location

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "ERRO: Build falhou (exit $exitCode)" -ForegroundColor Red
    Read-Host "Pressione Enter para sair"
    exit $exitCode
}

# ---- 4. Resultado ----
Write-Host ""
Write-Host "[3/3] Build concluido!" -ForegroundColor Green
$instalador = Get-ChildItem "Instalacao EXE\Vektorium-Setup-*.exe" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($instalador) {
    Write-Host "Instalador: $($instalador.FullName)" -ForegroundColor Yellow
    Write-Host "Tamanho:    $([math]::Round($instalador.Length / 1MB, 1)) MB"
} else {
    # Tenta o caminho com acento (depende do terminal)
    $instalador2 = Get-ChildItem "Instalação EXE\Vektorium-Setup-*.exe" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($instalador2) {
        Write-Host "Instalador: $($instalador2.FullName)" -ForegroundColor Yellow
        Write-Host "Tamanho:    $([math]::Round($instalador2.Length / 1MB, 1)) MB"
    }
}

Write-Host ""
Read-Host "Pressione Enter para sair"
