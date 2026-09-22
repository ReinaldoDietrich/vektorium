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
    Write-Host "[1/4] Instalando dependencias npm..." -ForegroundColor Cyan
    Push-Location electron
    npm install
    Pop-Location
} else {
    Write-Host "[1/4] Dependencias npm OK" -ForegroundColor Green
}

# ---- 3. Compilar arquivos de calculo para .pyc (protecao do codigo-fonte) ----
Write-Host ""
Write-Host "[2/4] Compilando calculos para .pyc..." -ForegroundColor Cyan
$pyEmbed = "python-embed\python.exe"
if (Test-Path $pyEmbed) {
    $calcArqs = @(
        "backend\calc_service.py",
        "backend\calc_puro_uc_rack.py",
        "backend\calc_paineis_portas.py",
        "backend\calc_polinomio_compressor.py",
        "backend\calculos\camara_completo.py",
        "backend\calculos\camara_simples.py",
        "backend\calculos\condensador.py",
        "backend\calculos\forcador.py",
        "backend\calculos\infiltracao.py",
        "backend\calculos\luminotecnico.py",
        "backend\calculos\valvula.py",
        "backend\calculos\comum.py"
    )
    $compiled = 0
    foreach ($f in $calcArqs) {
        if (Test-Path $f) {
            & $pyEmbed -m py_compile $f 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) { $compiled++ }
            else { Write-Host "  AVISO: falha ao compilar $f" -ForegroundColor Yellow }
        }
    }
    Write-Host "  $compiled arquivo(s) compilado(s) para .pyc." -ForegroundColor Green
} else {
    Write-Host "  AVISO: python-embed nao encontrado — .pyc nao gerados." -ForegroundColor Yellow
}

# ---- 4. Build Electron ----
Write-Host ""
Write-Host "[3/4] Buildando Electron (npm run build)..." -ForegroundColor Cyan
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

# ---- 5. Resultado ----
Write-Host ""
Write-Host "[4/4] Build concluido!" -ForegroundColor Green
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
