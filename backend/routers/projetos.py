import shutil
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db, DB_PATH, BASE_DIR
from ..utils import model_to_dict, list_to_dict, chave_ordem_camara
from . import _bloqueio_projeto as bp
from . import _bloqueio_fechada as bf
from ..workspace import workspace

router = APIRouter(prefix="/api", tags=["projetos"])

_CAMPOS_DADOS_GERAIS = {
    "codigo_projeto", "data", "cliente", "contato", "telefone",
    "razao_social_faturamento", "cnpj_faturamento", "cep_faturamento",
    "endereco_faturamento", "endereco_obra", "cep_obra",
}
_CAMPOS_CLIMA = {
    "cidade_instalacao", "estado_uf", "altitude_m",
    "estacao_inmet_id", "estacao_climatologica_id", "criterio_climatico",
    "temp_ambiente", "ur_externa",
}
_CAMPOS_ESTRUTURAL = {
    "tipo_comando", "tensao_equipamentos", "tensao_comando",
    "custo_energia", "pasta_salvamento", "condicao_salao",
    "considerar_iluminacao_ambiente",
}


def _verificar_secoes_projeto(obj, payload: dict):
    """Bloqueia se o payload tentar alterar campos de uma seção fechada."""
    campos = set(payload.keys())
    if campos & _CAMPOS_DADOS_GERAIS and obj.fechada_dados_gerais:
        raise HTTPException(423, "Seção 'Dados Gerais' está fechada — clique em Editar antes de alterar.")
    if campos & _CAMPOS_CLIMA and obj.fechada_clima:
        raise HTTPException(423, "Seção 'Clima' está fechada — clique em Editar antes de alterar.")
    if campos & _CAMPOS_ESTRUTURAL and obj.fechada_estrutural:
        raise HTTPException(423, "Seção 'Estrutural' está fechada — clique em Editar antes de alterar.")


def _contar_vinculos(db: Session, sistema_id: int) -> int:
    return (db.query(m.CamaraCompleto).filter_by(sistema_id=sistema_id).count()
            + db.query(m.CamaraSimples).filter_by(sistema_id=sistema_id).count()
            + db.query(m.Expositor).filter_by(sistema_id=sistema_id).count())


@router.get("/projetos")
def listar_projetos(db: Session = Depends(get_db)):
    return list_to_dict(db.query(m.Projeto).order_by(m.Projeto.id.desc()).all())


@router.post("/projetos/escolher-pasta")
def escolher_pasta(payload: dict = Body(default={})):
    """Abre a janela nativa do Windows pra escolher pasta via PowerShell FolderBrowserDialog —
    substitui tkinter que falhava silenciosamente dentro do processo Electron (sem display X11 /
    COM STA não inicializado). Síncrono e bloqueante de propósito: FastAPI roda endpoints `def`
    (não `async def`) numa threadpool, então isso não trava o resto do app."""
    import subprocess, re
    inicial = str(payload.get("inicial") or "")
    # Sanitiza o path: só aceita caminhos válidos Windows (evita injeção no script PS)
    if not re.match(r'^[A-Za-z]:\\[\w\s\\().,-]*$', inicial):
        from pathlib import Path
        inicial = str(Path.home())
    inicial_ps = inicial.replace("'", "")   # remove aspas simples residuais
    script = (
        "[System.Windows.Forms.Application]::EnableVisualStyles(); "
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
        f"$d.SelectedPath = '{inicial_ps}'; "
        "$d.Description = 'Escolher pasta de salvamento do projeto'; "
        "$d.ShowNewFolderButton = $true; "
        "[void]$d.ShowDialog(); "
        "Write-Output $d.SelectedPath"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-STA", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
        )
        pasta = result.stdout.strip() or None
    except Exception:
        pasta = None
    return {"pasta": pasta or None}


@router.post("/sistema/backup-banco")
def backup_banco():
    """Cópia do arquivo do banco de dados inteiro (todos os projetos) — devolve o arquivo
    como download para o navegador/Electron salvar via dialog nativo."""
    from fastapi.responses import FileResponse
    _wal_checkpoint()
    nome = f"carga_termica_BACKUP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    return FileResponse(DB_PATH, filename=nome, media_type="application/octet-stream")


# ──────────────────────────────────────────────────────────────────────────────
# SE-107: Endpoints master-only — backup pré-logout, importar banco, deploy,
#         build EXE
# ──────────────────────────────────────────────────────────────────────────────
import subprocess as _subprocess
import os as _os
import json as _json_builtin
import sqlite3 as _sqlite3

_BASE = str(BASE_DIR)
_INSTALL_DIR = r"C:\Program Files\Vektorium\resources"
_ELECTRON_DIR = _os.path.join(_BASE, "electron")

_project_base_file = _os.path.join(_BASE, ".project_base")
if _os.path.isfile(_project_base_file):
    with open(_project_base_file, "r", encoding="utf-8-sig") as _f:
        _PROJECT_BASE = _f.read().strip()
else:
    _PROJECT_BASE = _BASE

_BACKUP_BASE = _os.path.join(_INSTALL_DIR, "A - Backup Banco de Dados")
_BACKUP_BANCO = _os.path.join(_BACKUP_BASE, "Banco de dados")
_BACKUP_SISTEMA = _os.path.join(_BACKUP_BASE, "Sistema")


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H-%M-%S")


def _wal_checkpoint():
    conn = _sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def _backup_banco_para_pasta():
    _os.makedirs(_BACKUP_BANCO, exist_ok=True)
    ts = _timestamp()
    nome = f"carga_termica_BACKUP_{ts}.db"
    destino = _os.path.join(_BACKUP_BANCO, nome)
    _wal_checkpoint()
    shutil.copy2(str(DB_PATH), destino)
    return destino


def _backup_sistema_para_pasta():
    if not _os.path.isdir(_INSTALL_DIR):
        raise HTTPException(500, f"Pasta de instalação não encontrada: {_INSTALL_DIR}")
    _os.makedirs(_BACKUP_SISTEMA, exist_ok=True)
    ts = _timestamp()
    pasta_destino = _os.path.join(_BACKUP_SISTEMA, f"Sistema_BACKUP_{ts}")
    _os.makedirs(pasta_destino, exist_ok=True)
    for item in ["backend", "frontend", "database", "dados", "python-embed"]:
        src = _os.path.join(_INSTALL_DIR, item)
        dst = _os.path.join(pasta_destino, item)
        if _os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.pyo", "*.db-wal", "*.db-shm"
            ))
    ini = _os.path.join(_INSTALL_DIR, "iniciar_app.py")
    if _os.path.isfile(ini):
        shutil.copy2(ini, _os.path.join(pasta_destino, "iniciar_app.py"))
    return pasta_destino


@router.post("/sistema/backup-pre-logout")
def backup_pre_logout():
    resultados = {"banco": None, "sistema": None, "erros": []}
    try:
        resultados["banco"] = _backup_banco_para_pasta()
    except Exception as e:
        resultados["erros"].append(f"Backup banco: {e}")
    try:
        resultados["sistema"] = _backup_sistema_para_pasta()
    except Exception as e:
        resultados["erros"].append(f"Backup sistema: {e}")
    if resultados["erros"] and not resultados["banco"] and not resultados["sistema"]:
        raise HTTPException(500, "; ".join(resultados["erros"]))
    return resultados


@router.post("/sistema/importar-banco")
def importar_banco(payload: dict = Body(...)):
    from ..database import engine as _engine

    caminho = payload.get("caminho")
    if not caminho or not _os.path.isfile(caminho):
        raise HTTPException(400, "Arquivo de banco não encontrado.")

    try:
        conn_test = _sqlite3.connect(caminho)
        conn_test.execute("SELECT count(*) FROM sqlite_master")
        conn_test.close()
    except Exception as e:
        raise HTTPException(400, f"Arquivo não é um banco SQLite válido: {e}")

    try:
        backup_seguranca = _backup_banco_para_pasta()
    except Exception as e:
        raise HTTPException(500, f"Falha no backup de segurança: {e}")

    db_path_str = str(DB_PATH)
    wal_path = db_path_str + "-wal"
    shm_path = db_path_str + "-shm"

    _engine.dispose()

    try:
        for f in [wal_path, shm_path]:
            if _os.path.isfile(f):
                _os.remove(f)
        shutil.copy2(caminho, db_path_str)
        for f in [wal_path, shm_path]:
            if _os.path.isfile(f):
                _os.remove(f)
    except Exception as e:
        try:
            shutil.copy2(backup_seguranca, db_path_str)
        except Exception:
            pass
        raise HTTPException(500, f"Erro ao importar banco: {e}. Backup de segurança em: {backup_seguranca}")

    return {
        "ok": True,
        "backup_seguranca": backup_seguranca,
        "msg": "Banco importado com sucesso. Reinicie o aplicativo para garantir integridade."
    }


@router.post("/sistema/deploy")
def deploy_para_program_files():
    resultados = {"backup_banco": None, "backup_sistema": None, "etapas": [], "erros": []}

    _origem = _BASE
    if _os.path.normcase(_BASE) == _os.path.normcase(_INSTALL_DIR):
        _origem = _PROJECT_BASE
    if _os.path.normcase(_origem) == _os.path.normcase(_INSTALL_DIR):
        raise HTTPException(400,
            "Deploy impossível: o backend está rodando de Program Files e "
            "não há .project_base configurado apontando para o diretório de desenvolvimento.")
    if not _os.path.isdir(_origem):
        raise HTTPException(400, f"Diretório de origem não encontrado: {_origem}")

    temp_dir = r"C:\Temp\vk_deploy"
    try:
        if _os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        _os.makedirs(temp_dir, exist_ok=True)

        ignore_fn = shutil.ignore_patterns(
            "__pycache__", "*.pyc", "*.pyo", "*.db-wal", "*.db-shm",
            "node_modules", "venv", ".venv", ".git", ".claude",
            "Documentos*", "Instalação*", "Instalacao*", "A - Backup*",
            "mockups", "_tmp_proposta", "_reversao_*", "*.log",
            "scripts", "calc_remoto_client.py", "calc_remoto.py"
        )

        for pasta in ["backend", "frontend", "dados"]:
            src = _os.path.join(_origem, pasta)
            dst = _os.path.join(temp_dir, pasta)
            if _os.path.isdir(src):
                shutil.copytree(src, dst, ignore=ignore_fn)

        ini = _os.path.join(_origem, "iniciar_app.py")
        if _os.path.isfile(ini):
            shutil.copy2(ini, _os.path.join(temp_dir, "iniciar_app.py"))

        resultados["etapas"].append("Cópia dev → temp OK")
    except Exception as e:
        raise HTTPException(500, f"Falha ao copiar para diretório temporário: {e}")

    _wal_checkpoint()
    script_path = r"C:\Temp\vk_deploy_script.ps1"
    try:
        script_content = (
            "$ErrorActionPreference = 'Stop'\n"
            f"$src = '{temp_dir}'\n"
            f"$dst = '{_INSTALL_DIR}'\n"
            "\n"
            "# Criar pastas de backup\n"
            "$backupBase = Join-Path $dst 'A - Backup Banco de Dados'\n"
            "$backupBanco = Join-Path $backupBase 'Banco de dados'\n"
            "$backupSistema = Join-Path $backupBase 'Sistema'\n"
            "New-Item -ItemType Directory -Force $backupBanco | Out-Null\n"
            "New-Item -ItemType Directory -Force $backupSistema | Out-Null\n"
            "\n"
            "# Permissao de escrita para o usuario (backup_pre_logout sem elevacao)\n"
            "$usr = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name\n"
            "$g = '\"' + $usr + ':(OI)(CI)M\"'\n"
            "icacls $backupBanco /grant $g /Q\n"
            "icacls $backupSistema /grant $g /Q\n"
            "\n"
            "$ts = Get-Date -Format 'yyyy-MM-dd HH-mm-ss'\n"
            "\n"
            "# Backup do banco AppData (banco real, checkpoint ja feito pelo Python)\n"
            "$dbAppData = Join-Path $env:APPDATA 'Vektorium\\database\\carga_termica.db'\n"
            "if (Test-Path $dbAppData) {\n"
            "    Copy-Item $dbAppData (Join-Path $backupBanco \"carga_termica_BACKUP_$ts.db\") -Force\n"
            "}\n"
            "\n"
            "# Backup do sistema PF (inclui database do EXE)\n"
            "$bkpSys = Join-Path $backupSistema \"Sistema_BACKUP_$ts\"\n"
            "New-Item -ItemType Directory -Force $bkpSys | Out-Null\n"
            "foreach ($pasta in @('backend','frontend','database','dados','python-embed')) {\n"
            "    $s = Join-Path $dst $pasta\n"
            "    if (Test-Path $s) { Copy-Item $s (Join-Path $bkpSys $pasta) -Recurse -Force }\n"
            "}\n"
            "$iniDst = Join-Path $dst 'iniciar_app.py'\n"
            "if (Test-Path $iniDst) { Copy-Item $iniDst (Join-Path $bkpSys 'iniciar_app.py') -Force }\n"
            "\n"
            "# Deploy: copiar codigo de temp para PF (sem database)\n"
            "foreach ($pasta in @('backend', 'frontend', 'dados')) {\n"
            "    $s = Join-Path $src $pasta\n"
            "    $d = Join-Path $dst $pasta\n"
            "    if (Test-Path $s) {\n"
            "        if (Test-Path $d) { Remove-Item $d -Recurse -Force }\n"
            "        Copy-Item $s $d -Recurse -Force\n"
            "    }\n"
            "}\n"
            "$ini = Join-Path $src 'iniciar_app.py'\n"
            "if (Test-Path $ini) { Copy-Item $ini (Join-Path $dst 'iniciar_app.py') -Force }\n"
            "Remove-Item $src -Recurse -Force\n"
            "\n"
            "# Gravar caminho do projeto de origem para deploy futuro\n"
            f"[IO.File]::WriteAllText((Join-Path $dst '.project_base'), '{_origem}', (New-Object System.Text.UTF8Encoding $true))\n"
        )
        with open(script_path, "w", encoding="utf-8-sig") as f:
            f.write(script_content)

        result = _subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                f"Start-Process powershell -Verb RunAs -Wait "
                f"-ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','{script_path}'"
            ],
            capture_output=True, text=True, timeout=180
        )

        check_file = _os.path.join(_INSTALL_DIR, "frontend", "index.html")
        if not _os.path.isfile(check_file):
            raise Exception("Verificação falhou — frontend/index.html não encontrado em Program Files.")

        resultados["etapas"].append("Backup do destino OK")
        resultados["etapas"].append("Deploy para Program Files OK")
    except _subprocess.TimeoutExpired:
        raise HTTPException(500, "Deploy expirou (timeout 180s). O UAC pode ter sido cancelado.")
    except Exception as e:
        raise HTTPException(500, f"Deploy para Program Files falhou: {e}")
    finally:
        if _os.path.isfile(script_path):
            try:
                _os.remove(script_path)
            except Exception:
                pass

    return resultados


@router.post("/sistema/build-exe")
def build_exe():
    resultados = {"etapas": [], "erros": []}

    try:
        deploy_result = deploy_para_program_files()
        resultados["etapas"].extend(deploy_result.get("etapas", []))
        resultados["backup_banco"] = deploy_result.get("backup_banco")
        resultados["backup_sistema"] = deploy_result.get("backup_sistema")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Deploy falhou: {e}")

    npm_path = shutil.which("npm")
    if not npm_path:
        for tentativa in [
            r"C:\Program Files\nodejs\npm.cmd",
            r"C:\Program Files (x86)\nodejs\npm.cmd",
            _os.path.expandvars(r"%APPDATA%\npm\npm.cmd"),
        ]:
            if _os.path.isfile(tentativa):
                npm_path = tentativa
                break
    if not npm_path:
        raise HTTPException(500, "npm não encontrado no PATH do sistema.")

    try:
        result = _subprocess.run(
            [npm_path, "run", "build"],
            cwd=_ELECTRON_DIR,
            capture_output=True, text=True, timeout=600,
            env={**_os.environ, "ELECTRON_BUILDER_ALLOW_UNRESOLVED_DEPENDENCIES": "true"}
        )
        if result.returncode != 0:
            stderr_resumo = (result.stderr or "")[-500:]
            raise Exception(f"electron-builder código {result.returncode}.\n{stderr_resumo}")
        resultados["etapas"].append("Build EXE OK")
        resultados["stdout_resumo"] = (result.stdout or "")[-300:]
    except _subprocess.TimeoutExpired:
        raise HTTPException(500, "Build EXE expirou (timeout 10min).")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Build EXE falhou: {e}")

    return resultados


@router.post("/projetos")
def criar_projeto(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = m.Projeto(**payload)
    if not obj.codigo_base:
        obj.codigo_base = obj.codigo_projeto
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.get("/projetos/{projeto_id}")
def obter_projeto(projeto_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404, "Projeto não encontrado")
    return model_to_dict(obj)


@router.put("/projetos/{projeto_id}/pasta-salvamento")
def atualizar_pasta_salvamento(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_da(obj)
    obj.pasta_salvamento = payload.get("pasta_salvamento") or None
    db.commit()
    db.refresh(obj)
    path_vek = workspace.projeto_pertence_a(obj.id)
    if path_vek:
        workspace.marcar_modificado(obj.id)
        workspace.salvar_arquivo(path_vek)
    return {"pasta_salvamento": obj.pasta_salvamento}


@router.put("/projetos/{projeto_id}")
def atualizar_projeto(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_da(obj)
    _verificar_secoes_projeto(obj, payload)
    for k, v in payload.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    path_vek = workspace.projeto_pertence_a(obj.id)
    if path_vek:
        workspace.marcar_modificado(obj.id)
        workspace.salvar_arquivo(path_vek)
    return model_to_dict(obj)


@router.delete("/projetos/{projeto_id}")
def excluir_projeto(projeto_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_da(obj)
    path_vek = workspace.projeto_pertence_a(projeto_id)
    db.delete(obj)
    db.commit()
    workspace.desregistrar_projeto(projeto_id)
    if path_vek:
        workspace.salvar_arquivo(path_vek)
    return {"ok": True}


@router.post("/projetos/{projeto_id}/fechar")
def fechar_projeto(projeto_id: int, db: Session = Depends(get_db)):
    """"Fechar Projeto" (Tela 1, aprovado 2026-08-12) — trava reversível: bloqueia qualquer
    escrita nos dados desse projeto (ver backend/routers/_bloqueio_projeto.py) até "Reabrir
    Projeto" ser clicado."""
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404, "Projeto não encontrado")
    obj.fechado = True
    db.commit()
    return {"fechado": True}


@router.post("/projetos/{projeto_id}/reabrir")
def reabrir_projeto(projeto_id: int, db: Session = Depends(get_db)):
    """Reverte "Fechar Projeto" — nunca passa pela checagem de bloqueio (senão um projeto fechado
    nunca poderia ser reaberto)."""
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404, "Projeto não encontrado")
    obj.fechado = False
    db.commit()
    return {"fechado": False}


@router.post("/projetos/{projeto_id}/editar-dados-gerais")
def editar_dados_gerais(projeto_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404)
    obj.fechada_dados_gerais = False
    db.commit()
    return {"fechada_dados_gerais": False}


@router.post("/projetos/{projeto_id}/salvar-dados-gerais")
def salvar_dados_gerais(projeto_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404)
    obj.fechada_dados_gerais = True
    db.commit()
    return {"fechada_dados_gerais": True}


@router.post("/projetos/{projeto_id}/editar-clima")
def editar_clima(projeto_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404)
    obj.fechada_clima = False
    db.commit()
    return {"fechada_clima": False}


@router.post("/projetos/{projeto_id}/salvar-clima")
def salvar_clima(projeto_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404)
    obj.fechada_clima = True
    db.commit()
    return {"fechada_clima": True}


@router.post("/projetos/{projeto_id}/editar-estrutural")
def editar_estrutural(projeto_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404)
    obj.fechada_estrutural = False
    db.commit()
    return {"fechada_estrutural": False}


@router.post("/projetos/{projeto_id}/salvar-estrutural")
def salvar_estrutural(projeto_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.Projeto, projeto_id)
    if not obj:
        raise HTTPException(404)
    obj.fechada_estrutural = True
    db.commit()
    return {"fechada_estrutural": True}


@router.post("/projetos/{projeto_id}/exportar-tudo")
def exportar_tudo(projeto_id: int, db: Session = Depends(get_db)):
    """"Exportar Tudo" (Tela 1, botão ao lado de "+ Revisão", aprovado 2026-08-12) — reúne todas
    as planilhas já calculadas do projeto (Compilação de Linhas, Resumo Painéis/Portas por ID e
    porta por câmara, Compilação Geral, Consumo Elétrico, Estudo Luminotécnico, Resumo por
    Bloco/Tabela de Orçamento/DRE) numa única pasta de trabalho, uma aba por origem, salva direto
    na Pasta de Salvamento do projeto. Reaproveita as mesmas funções de montagem/exportação já
    usadas pelos downloads individuais de cada tela — nenhuma delas é alterada aqui; só reabre
    cada .xlsx já gerado e copia as abas pra dentro do combinado (ver combinar_excel.py)."""
    import re
    from pathlib import Path
    import openpyxl
    from ..exportacao.combinar_excel import adicionar_workbook

    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    if not projeto.pasta_salvamento:
        raise HTTPException(400, "Defina a \"Pasta de Salvamento do Projeto\" antes de exportar tudo.")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # a aba padrão vazia — cada fonte abaixo cria a(s) sua(s) própria(s)

    # Tela 5 — Compilação de Linhas
    from .compilacao import (_montar_itens_compilacao, _totais_gerais, _disjuntores_gerais,
                              _colunas_resumo_selecionadas, _colunas_resumo_compressao_selecionadas,
                              gerar_excel_compilacao)
    _, sistemas, itens, resumo_sistemas, resumo_compressao, observacao, eh_qd = _montar_itens_compilacao(db, projeto_id, 0.92)
    totais_gerais = _totais_gerais(resumo_sistemas, resumo_compressao, 0.92)
    potencia_maxima_compressao_w = sum((r.get("potencia_maxima_w") or 0) for r in resumo_compressao)
    disjuntor_geral_quadro_linhas, disjuntor_geral_compressao = _disjuntores_gerais(
        db, projeto, resumo_sistemas, resumo_compressao, potencia_maxima_compressao_w, 0.92)
    conteudo = gerar_excel_compilacao(projeto, sistemas, itens, resumo_sistemas, observacao,
                                       _colunas_resumo_selecionadas(None), resumo_compressao,
                                       _colunas_resumo_compressao_selecionadas(None), totais_gerais,
                                       eh_qd, disjuntor_geral_quadro_linhas, disjuntor_geral_compressao)
    adicionar_workbook(wb, conteudo, "Compilação de Linhas")

    # Tela 7 — Resumo de Painéis por ID e Porta por Câmara (modo="camara")
    from .paineis_portas import montar_resumo, gerar_excel_paineis_portas
    resumo_pp = montar_resumo(db, projeto, "camara")
    conteudo = gerar_excel_paineis_portas(projeto, resumo_pp)
    adicionar_workbook(wb, conteudo, "Painéis e Portas por Câmara")

    # Tela 8 — Compilação Geral
    from .compilacao_geral import _montar_compilacao_geral, gerar_excel_compilacao_geral
    _, dados_cg = _montar_compilacao_geral(db, projeto_id)
    conteudo = gerar_excel_compilacao_geral(projeto, dados_cg)
    adicionar_workbook(wb, conteudo, "Compilação Geral")

    # Tela 9 — Consumo Elétrico
    from .consumo import _montar_consumo, gerar_excel_consumo
    _, dados_consumo = _montar_consumo(db, projeto_id)
    conteudo = gerar_excel_consumo(projeto, dados_consumo)
    adicionar_workbook(wb, conteudo, "Consumo Elétrico")

    # Tela 11 — Estudo Luminotécnico
    from .luminotecnico import montar_estudo, gerar_excel_luminotecnico
    dados_lumino = montar_estudo(db, projeto_id)
    conteudo = gerar_excel_luminotecnico(projeto, dados_lumino)
    adicionar_workbook(wb, conteudo, "Estudo Luminotécnico")

    # Tela 10 — Resumo por Bloco + Tabela de Orçamento + DRE
    from .. import composicao_preco as cp
    from ..exportacao.composicao_preco_export import gerar_excel_resumo_orcamento
    dados_cp = cp.montar_composicao(db, projeto_id)
    resumo_cp = cp.resumo_por_bloco(db, projeto_id, dados=dados_cp)
    orcamento_cp = cp.tabela_orcamento(dados_cp)
    com_cp = cp.comissionamento(db, projeto_id, dados=dados_cp, resumo=resumo_cp)
    dre_cp = cp.dre_projeto(db, projeto_id, dados=dados_cp, resumo=resumo_cp, com=com_cp)
    conteudo = gerar_excel_resumo_orcamento(projeto, resumo_cp, orcamento_cp, dre_cp)
    adicionar_workbook(wb, conteudo, "Resumo de Equipamentos")

    titulo = f"{projeto.codigo_projeto or projeto_id} — {projeto.cliente}" if projeto.cliente else f"{projeto.codigo_projeto or projeto_id}"
    nome_arquivo = re.sub(r'[\\/:*?"<>|]', "-", f"{titulo}_R{(projeto.revisao or 0):02d}.xlsx")
    destino = Path(projeto.pasta_salvamento)
    try:
        destino.mkdir(parents=True, exist_ok=True)
        caminho = destino / nome_arquivo
        wb.save(caminho)
    except OSError as e:
        raise HTTPException(400, f"Não foi possível salvar em \"{projeto.pasta_salvamento}\": {e}")
    return {"salvo_em": str(caminho)}


# ===================== CONTROLE DE REVISÃO =====================
# "Gerar Revisão" = deep-copy editável do projeto inteiro (não congela o original). Uma revisão é só
# outro Projeto — cálculo/exportações não mudam. Copia toda a árvore de posse remapeando os ids.

def _cols(obj, exclude):
    """Valores de coluna do objeto, exceto as chaves em `exclude` (id + FKs que serão remapeadas)."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in exclude}


@router.post("/projetos/{projeto_id}/revisao")
def gerar_revisao(projeto_id: int, db: Session = Depends(get_db)):
    orig = db.get(m.Projeto, projeto_id)
    if not orig:
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_da(orig)
    base = orig.codigo_base or orig.codigo_projeto or str(orig.id)
    if not orig.codigo_base:
        # 1ª revisão deste projeto: o original também precisa do mesmo codigo_base, senão ele fica
        # de fora do agrupamento (cada um vira uma "pasta" separada na lista da Tela 1 em vez de
        # R00 pai + R01 filha) — bug real encontrado em produção (projeto 2026.027).
        orig.codigo_base = base
    prox = (db.query(func.max(m.Projeto.revisao)).filter(m.Projeto.codigo_base == base).scalar() or 0) + 1

    novo = m.Projeto(**_cols(orig, {"id"}))
    novo.codigo_base = base
    novo.revisao = prox
    novo.revisao_de = orig.id
    novo.fechado = False  # revisão nova sempre nasce editável (aprovado 2026-08-12)
    db.add(novo)
    db.flush()

    map_cc, map_cs = {}, {}   # câmara antiga -> nova (pra remapear Painéis/Portas da Tela E)
    for s in orig.sistemas:
        ns = m.SistemaRefrigeracao(**_cols(s, {"id", "projeto_id"}), projeto_id=novo.id)
        db.add(ns)
        db.flush()
        for c in s.camaras_completo:
            nc = m.CamaraCompleto(**_cols(c, {"id", "sistema_id"}), sistema_id=ns.id)
            db.add(nc)
            db.flush()
            map_cc[c.id] = nc.id
            for e in c.equipamentos:
                db.add(m.EquipamentoCamaraCompleto(**_cols(e, {"id", "camara_id"}), camara_id=nc.id))
            for f in c.forcadores:
                nf = m.ForcadorSelecaoCompleto(**_cols(f, {"id", "camara_id"}), camara_id=nc.id)
                db.add(nf)
                db.flush()
                for v in f.valvulas:
                    db.add(m.ValvulaSelecaoCompleto(**_cols(v, {"id", "forcador_selecao_id"}), forcador_selecao_id=nf.id))
            for p in c.portas:
                db.add(m.PortaCamara(**_cols(p, {"id", "camara_id"}), camara_id=nc.id))
        for c in s.camaras_simples:
            nc = m.CamaraSimples(**_cols(c, {"id", "sistema_id"}), sistema_id=ns.id)
            db.add(nc)
            db.flush()
            map_cs[c.id] = nc.id
            for f in c.forcadores:
                nf = m.ForcadorSelecaoSimples(**_cols(f, {"id", "camara_id"}), camara_id=nc.id)
                db.add(nf)
                db.flush()
                for v in f.valvulas:
                    db.add(m.ValvulaSelecaoSimples(**_cols(v, {"id", "forcador_selecao_id"}), forcador_selecao_id=nf.id))
        for ex in s.expositores:
            nex = m.Expositor(**_cols(ex, {"id", "sistema_id"}), sistema_id=ns.id)
            db.add(nex)
            db.flush()
            for mo in ex.modulos:
                db.add(m.ModuloExpositor(**_cols(mo, {"id", "expositor_id"}), expositor_id=nex.id))
        for rk in s.racks:
            nrk = m.RackParalelo(**_cols(rk, {"id", "sistema_id"}), sistema_id=ns.id)
            db.add(nrk)
            db.flush()
            for mt in rk.materiais:
                db.add(m.MaterialRack(**_cols(mt, {"id", "rack_id"}), rack_id=nrk.id))
            for cp in rk.compressores:
                db.add(m.CompressorRack(**_cols(cp, {"id", "rack_id"}), rack_id=nrk.id))
            for cd in rk.condensadores:
                db.add(m.RackCondensadorSelecao(**_cols(cd, {"id", "rack_id"}), rack_id=nrk.id))
        for uc in db.query(m.UnidadeSelecaoSistema).filter_by(sistema_id=s.id).all():
            db.add(m.UnidadeSelecaoSistema(**_cols(uc, {"id", "sistema_id"}), sistema_id=ns.id))
    db.flush()

    # Tela E — Painéis/Portas (projeto_id + câmaras remapeadas; ambiente não climatizado fica sem câmara)
    for pt in db.query(m.PainelTermico).filter_by(projeto_id=orig.id).all():
        db.add(m.PainelTermico(**_cols(pt, {"id", "projeto_id", "camara_completo_id", "camara_simples_id"}),
            projeto_id=novo.id, camara_completo_id=map_cc.get(pt.camara_completo_id),
            camara_simples_id=map_cs.get(pt.camara_simples_id)))
    for pf in db.query(m.PortaFrigorifica).filter_by(projeto_id=orig.id).all():
        db.add(m.PortaFrigorifica(**_cols(pf, {"id", "projeto_id", "camara_completo_id", "camara_simples_id"}),
            projeto_id=novo.id, camara_completo_id=map_cc.get(pf.camara_completo_id),
            camara_simples_id=map_cs.get(pf.camara_simples_id)))
    db.commit()
    db.refresh(novo)
    workspace.registrar_revisao(novo.id, orig.id)
    path_vek = workspace.projeto_pertence_a(novo.id)
    if path_vek:
        workspace.salvar_arquivo(path_vek)
    return model_to_dict(novo)


# ===================== FILTRO GLOBAL DE FABRICANTE (POR TIPO) =====================
# UM filtro independente por TIPO de equipamento (forçador, UC, condensador) — fabricante raramente
# faz a linha completa, então não faz sentido exigir que cubra tudo de uma vez. Move só o "Considerar"
# (não altera dados). Por tipo, um fabricante só é elegível se tiver EXATAMENTE UMA opção em TODA
# unidade daquele tipo: forçador = cada câmara; UC = cada sistema; condensador = cada rack.

def _unidades_por_tipo(db: Session, projeto_id: int):
    """Unidades com seleção, separadas por tipo. Cada unidade = {opcoes:[(fab_nome, obj)], rack}."""
    sistemas = db.query(m.SistemaRefrigeracao).filter_by(projeto_id=projeto_id).all()
    forcador, uc, condensador = [], [], []
    for s in sistemas:
        for cam in list(s.camaras_completo) + list(s.camaras_simples):
            ops = [(f.fabricante.nome, f) for f in cam.forcadores if f.fabricante]
            if ops:
                forcador.append({"opcoes": ops, "rack": None})
        ucs = db.query(m.UnidadeSelecaoSistema).filter_by(sistema_id=s.id).all()
        ops = [(u.fabricante_uc, u) for u in ucs if u.fabricante_uc]
        if ops:
            uc.append({"opcoes": ops, "rack": None})
        for rack in s.racks:   # condensador por rack (todos os racks, não só o considerado)
            ops = [((c.fabricante_condensador or (c.fabricante_rel.nome if c.fabricante_rel else None)), c)
                   for c in rack.condensadores
                   if c.fabricante_condensador or c.fabricante_id_condensador]
            if ops:
                condensador.append({"opcoes": ops, "rack": rack})
    return {"forcador": forcador, "uc": uc, "condensador": condensador}


def _elegiveis(unidades):
    if not unidades:
        return []
    candidatos = {nome for u in unidades for nome, _ in u["opcoes"]}
    # precisa estar em TODA unidade do tipo, exatamente 1 vez (uma linha por fabricante por unidade)
    return [f for f in sorted(candidatos)
            if all(sum(1 for nome, _ in u["opcoes"] if nome == f) == 1 for u in unidades)]


@router.get("/projetos/{projeto_id}/fabricante-global")
def listar_fabricante_global(projeto_id: int, db: Session = Depends(get_db)):
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    un = _unidades_por_tipo(db, projeto_id)
    return {tipo: _elegiveis(unidades) for tipo, unidades in un.items()}


@router.post("/projetos/{projeto_id}/fabricante-global/aplicar")
def aplicar_fabricante_global(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_aberto(db, projeto_id)
    tipo = (payload.get("tipo") or "").strip()
    fabricante = (payload.get("fabricante") or "").strip()
    un = _unidades_por_tipo(db, projeto_id)
    if tipo not in un:
        raise HTTPException(400, "Tipo inválido (use forcador, uc ou condensador).")
    unidades = un[tipo]
    if fabricante not in _elegiveis(unidades):
        raise HTTPException(400, "Fabricante não elegível para esse tipo (não cobre todo o escopo).")
    for u in unidades:
        for nome, obj in u["opcoes"]:
            obj.considerado = (nome == fabricante)
        if u["rack"]:  # espelha a opção considerada nas colunas do rack (compilação lê de lá)
            cons = next((o for _, o in u["opcoes"] if o.considerado), None)
            if cons:
                for campo in m.CAMPOS_CONDENSADOR:
                    setattr(u["rack"], campo, getattr(cons, campo))
    db.commit()
    return {"ok": True, "tipo": tipo, "fabricante": fabricante}


@router.get("/projetos/{projeto_id}/sistemas")
def listar_sistemas(projeto_id: int, db: Session = Depends(get_db)):
    sistemas = sorted(db.query(m.SistemaRefrigeracao).filter_by(projeto_id=projeto_id).all(),
                      key=lambda s: chave_ordem_camara(s.nome, "", ""))
    return [{**model_to_dict(s), "vinculos": _contar_vinculos(db, s.id)} for s in sistemas]


@router.post("/projetos/{projeto_id}/sistemas")
def criar_sistema(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    obj = m.SistemaRefrigeracao(projeto_id=projeto_id, **payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/sistemas/{sistema_id}")
def atualizar_sistema(sistema_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.SistemaRefrigeracao, sistema_id)
    if not obj:
        raise HTTPException(404, "Sistema não encontrado")
    bp.verificar_projeto_da(obj)
    bf.verificar_entidade_aberta(obj)
    campos_criticos = {"gas_refrigerante", "tipo_expansao", "temp_evaporacao", "classificacao"}
    mudou_critico = any(k in campos_criticos and getattr(obj, k) != v for k, v in payload.items())
    vinc = _contar_vinculos(db, sistema_id)
    for k, v in payload.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    if mudou_critico and vinc > 0:
        obj.precisa_revisar = True
    db.commit()
    db.refresh(obj)
    return {**model_to_dict(obj), "vinculos": vinc}


@router.get("/sistemas/{sistema_id}/vinculos")
def vinculos_sistema(sistema_id: int, db: Session = Depends(get_db)):
    return {"vinculos": _contar_vinculos(db, sistema_id)}


@router.delete("/sistemas/{sistema_id}")
def excluir_sistema(sistema_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.SistemaRefrigeracao, sistema_id)
    if not obj:
        raise HTTPException(404, "Sistema não encontrado")
    bp.verificar_projeto_da(obj)
    bf.verificar_entidade_aberta(obj)
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.post("/sistemas/{sistema_id}/editar")
def editar_sistema(sistema_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.SistemaRefrigeracao, sistema_id)
    if not obj:
        raise HTTPException(404)
    bp.verificar_projeto_da(obj)
    return model_to_dict(bf.editar_entidade(db, obj))


@router.post("/sistemas/{sistema_id}/salvar")
def salvar_sistema(sistema_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.SistemaRefrigeracao, sistema_id)
    if not obj:
        raise HTTPException(404)
    bp.verificar_projeto_da(obj)
    return model_to_dict(bf.salvar_entidade(db, obj, nome_model="SistemaRefrigeracao"))
