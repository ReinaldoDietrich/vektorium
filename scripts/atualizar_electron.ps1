# Script de atualização do app Electron instalado (SE-055/057/058)
# Executar como Administrador: Right-click > "Run with PowerShell" ou PowerShell elevado

$SRC = "B:\Documentos Programas\App Carga Térmica"
$DST = "C:\Program Files\Vektorium\resources"

Write-Host "Atualizando Vektorium em $DST ..." -ForegroundColor Cyan

# Backend
Copy-Item "$SRC\backend\auth_supabase.py" "$DST\backend\auth_supabase.py" -Force
Copy-Item "$SRC\backend\main.py" "$DST\backend\main.py" -Force
Copy-Item "$SRC\backend\workspace.py" "$DST\backend\workspace.py" -Force
Copy-Item "$SRC\backend\composicao_preco.py" "$DST\backend\composicao_preco.py" -Force
Copy-Item "$SRC\backend\routers\admin.py" "$DST\backend\routers\admin.py" -Force
Copy-Item "$SRC\backend\routers\cloud_projetos.py" "$DST\backend\routers\cloud_projetos.py" -Force
Copy-Item "$SRC\backend\routers\projetos.py" "$DST\backend\routers\projetos.py" -Force
Copy-Item "$SRC\backend\routers\composicao_preco.py" "$DST\backend\routers\composicao_preco.py" -Force

# Frontend
Copy-Item "$SRC\frontend\index.html" "$DST\frontend\index.html" -Force
Copy-Item "$SRC\frontend\css\style.css" "$DST\frontend\css\style.css" -Force
Copy-Item "$SRC\frontend\css\sidebar.css" "$DST\frontend\css\sidebar.css" -Force
Copy-Item "$SRC\frontend\js\tela20_admin.js" "$DST\frontend\js\tela20_admin.js" -Force
Copy-Item "$SRC\frontend\js\sidebar.js" "$DST\frontend\js\sidebar.js" -Force
Copy-Item "$SRC\frontend\js\auth.js" "$DST\frontend\js\auth.js" -Force
Copy-Item "$SRC\frontend\js\main.js" "$DST\frontend\js\main.js" -Force
Copy-Item "$SRC\frontend\js\tela1.js" "$DST\frontend\js\tela1.js" -Force
Copy-Item "$SRC\frontend\js\tela5.js" "$DST\frontend\js\tela5.js" -Force
Copy-Item "$SRC\frontend\js\tela7.js" "$DST\frontend\js\tela7.js" -Force
Copy-Item "$SRC\frontend\js\tela9.js" "$DST\frontend\js\tela9.js" -Force
Copy-Item "$SRC\frontend\js\tela10.js" "$DST\frontend\js\tela10.js" -Force
Copy-Item "$SRC\frontend\js\tela12.js" "$DST\frontend\js\tela12.js" -Force
Copy-Item "$SRC\frontend\js\tela16.js" "$DST\frontend\js\tela16.js" -Force
Copy-Item "$SRC\frontend\js\tela17.js" "$DST\frontend\js\tela17.js" -Force
Copy-Item "$SRC\frontend\js\telaLuminotecnico.js" "$DST\frontend\js\telaLuminotecnico.js" -Force

Write-Host ""
Write-Host "Atualização concluída (backend + frontend)!" -ForegroundColor Green
Write-Host "NOTA: main.js/preload.js estão dentro do app.asar — para atualizar esses," -ForegroundColor Yellow
Write-Host "      rode 'npm run build' em electron\ e reinstale o .exe gerado." -ForegroundColor Yellow
Write-Host "Feche e reabra o Vektorium para aplicar." -ForegroundColor Yellow
Write-Host ""
Pause
