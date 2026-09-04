# -*- coding: utf-8 -*-
"""API da Tela 13 — Proposta Comercial. Reúne o contexto do projeto (leitura), guarda os defaults
do usuário em JSON (nunca no banco), recebe os arquivos base (papel de carta/logomarca/planta) e
gera o .docx da proposta sobre o papel de carta."""
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Body, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models as m
from .. import id_comercial
from ..database import get_db
from ..utils import list_to_dict
from ..proposta import config, gerador

router = APIRouter(prefix="/api/proposta", tags=["proposta-comercial"])


def _disponibilidade_tabelas(db: Session, projeto_id: int) -> dict:
    n_completo = (db.query(m.CamaraCompleto)
                    .join(m.SistemaRefrigeracao)
                    .filter(m.SistemaRefrigeracao.projeto_id == projeto_id).count())
    n_simples = (db.query(m.CamaraSimples)
                   .join(m.SistemaRefrigeracao)
                   .filter(m.SistemaRefrigeracao.projeto_id == projeto_id).count())
    tem_camaras = (n_completo + n_simples) > 0
    tem_sistemas = db.query(m.SistemaRefrigeracao).filter_by(projeto_id=projeto_id).count() > 0
    tem_racks = (db.query(m.RackParalelo)
                   .join(m.SistemaRefrigeracao)
                   .filter(m.SistemaRefrigeracao.projeto_id == projeto_id).count()) > 0
    tem_forcadores = (db.query(m.ForcadorSelecaoCompleto)
                        .join(m.CamaraCompleto)
                        .join(m.SistemaRefrigeracao)
                        .filter(m.SistemaRefrigeracao.projeto_id == projeto_id).count()
                      + db.query(m.ForcadorSelecaoSimples)
                          .join(m.CamaraSimples)
                          .join(m.SistemaRefrigeracao)
                          .filter(m.SistemaRefrigeracao.projeto_id == projeto_id).count()) > 0
    tem_paineis = db.query(m.PainelTermico).filter_by(projeto_id=projeto_id).count() > 0
    tem_portas = db.query(m.PortaFrigorifica).filter_by(projeto_id=projeto_id).count() > 0
    tem_orcamento = db.query(m.ComposicaoPrecoItem).filter_by(projeto_id=projeto_id).count() > 0
    tem_pagamento = db.query(m.CondicaoPagamentoProjeto).filter_by(projeto_id=projeto_id).first() is not None
    return {
        "comp_linhas": tem_camaras and tem_forcadores,
        "comp_geral": tem_camaras or tem_racks,
        "consumo": tem_sistemas and tem_forcadores,
        "lumino": tem_camaras and n_completo > 0,
        "resumo_paineis": tem_paineis or tem_portas,
        "orcamento": tem_orcamento,
        "pagamento": tem_pagamento,
    }


@router.get("/contexto")
def contexto(projeto_id: int, db: Session = Depends(get_db)):
    """Tudo que a tela precisa: dados do projeto, defaults do usuário, árvore de Ids (com os que o
    projeto usa já pré-marcados) e a lista padrão de exceções."""
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")

    rev = getattr(projeto, "revisao", 0) or 0
    codigo = getattr(projeto, "codigo_base", None) or projeto.codigo_projeto or ""

    arvore = id_comercial.listar_arvore(db)
    memorial = id_comercial.montar_memorial_projeto(db, projeto_id)
    ids_projeto = set(str(x) for x in (memorial.get("ids_resolvidos") or []))
    itens_com_texto = {str(i.get("id_comercial")) for i in (memorial.get("itens") or [])}

    excecoes = gerador._excecoes_linhas(None)

    disp = _disponibilidade_tabelas(db, projeto_id)

    return {
        "projeto": {
            "id": projeto.id,
            "codigo_revisao": f"{codigo} - R{int(rev):02d}",
            "cliente": projeto.cliente,
            "contato": projeto.contato,
            "razao_social": getattr(projeto, "razao_social_faturamento", None) or projeto.cliente,
            "cnpj": getattr(projeto, "cnpj_faturamento", None),
            "cidade_estado": f"{projeto.cidade_instalacao or ''}/{projeto.estado_uf or ''}",
            "tipo_painel": gerador._tipos_painel(db, projeto_id),  # da Tela 7 (só leitura)
        },
        "defaults": config.carregar_defaults(),
        "arvore_ids": list_to_dict(arvore),
        "ids_projeto": sorted(ids_projeto),
        "ids_com_texto": sorted(itens_com_texto),
        "excecoes_padrao": excecoes,
        "tabelas": [
            {"chave": "comp_linhas",    "rotulo": "Compilação de Linhas",       "disponivel": disp["comp_linhas"]},
            {"chave": "comp_geral",     "rotulo": "Compilação Geral",           "disponivel": disp["comp_geral"]},
            {"chave": "consumo",        "rotulo": "Consumo Elétrico",           "disponivel": disp["consumo"]},
            {"chave": "lumino",         "rotulo": "Estudo Luminotécnico",       "disponivel": disp["lumino"]},
            {"chave": "resumo_paineis", "rotulo": "Resumo de Painéis (Total)",  "disponivel": disp["resumo_paineis"]},
            {"chave": "orcamento",      "rotulo": "Tabela de Orçamento",        "disponivel": disp["orcamento"]},
            {"chave": "pagamento",      "rotulo": "Formas de Pagamento",        "disponivel": disp["pagamento"]},
        ],
    }


@router.get("/defaults")
def obter_defaults():
    return config.carregar_defaults()


@router.put("/defaults")
def salvar_defaults(payload: dict = Body(...)):
    return config.salvar_defaults(payload or {})


@router.post("/upload")
async def upload_arquivo(tipo: str, arquivo: UploadFile = File(...)):
    """Recebe papel de carta / logomarca / planta. Salva em uploads/proposta e devolve o caminho
    relativo. papel_carta e logo viram default do usuário; a planta é usada por proposta."""
    if tipo not in ("papel_carta", "logo", "planta"):
        raise HTTPException(400, "tipo inválido")
    config._garantir_dirs()
    ext = Path(arquivo.filename or "").suffix or ""
    nome = f"{tipo}_{uuid.uuid4().hex}{ext}"
    destino = config.UPLOADS_PROPOSTA / nome
    destino.write_bytes(await arquivo.read())
    if tipo in ("papel_carta", "logo"):
        config.salvar_defaults({f"{tipo}_path": nome})
    return {"path": nome}


_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post("/gerar")
def gerar(projeto_id: int, opcoes: dict = Body(default=None), db: Session = Depends(get_db)):
    """Gera o .docx num arquivo temporário, pós-processa com LibreOffice (se disponível) e ABRE no
    aplicativo padrão do Windows para o usuário visualizar/editar/salvar. Devolve {aberto, caminho}."""
    import os, subprocess, tempfile
    from ..models import Projeto
    opcoes = opcoes or {}
    if opcoes.get("campos"):
        config.salvar_defaults(opcoes["campos"])
    try:
        conteudo, nome = gerador.gerar(db, projeto_id, opcoes)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback, logging
        logging.getLogger("proposta").error("Erro ao gerar proposta: %s\n%s", e, traceback.format_exc())
        raise HTTPException(500, f"Erro interno ao gerar proposta: {type(e).__name__}: {e}")

    nome = nome.replace("/", "-").replace("\\", "-")
    tmp_dir = Path(tempfile.gettempdir()) / "vektorium_proposta"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    caminho = tmp_dir / nome
    caminho.write_bytes(conteudo)

    try:
        subprocess.Popen(
            ['cmd', '/c', 'start', '', str(caminho)],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    except Exception as e:
        raise HTTPException(500, f"Não foi possível abrir o documento: {e}")

    return {"aberto": True, "caminho": str(caminho)}
