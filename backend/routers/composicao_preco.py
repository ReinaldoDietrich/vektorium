# -*- coding: utf-8 -*-
"""Composição de Preço — API. Itens/comissionamento/margem de negociação são por PROJETO;
Fatores/Itens-Default/Vendedores são MESTRE (globais, editados na Tela D — ver
backend/composicao_preco.py pra regras de cálculo)."""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict, list_to_dict
from .. import composicao_preco as cp
from . import _bloqueio_projeto as bp
from . import _bloqueio_fechada as bf

router = APIRouter(prefix="/api/composicao-preco", tags=["composicao-preco"])


# ---------------- Item (por projeto) ----------------

CAMPOS_ITEM = {"bloco", "descricao", "fabricante", "observacao", "quantidade", "custo_unitario",
                "fator_id", "centro_custo_id", "ordem", "incluir_orcamento"}


@router.get("")
def obter_composicao(projeto_id: int, db: Session = Depends(get_db)):
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    return cp.montar_composicao(db, projeto_id)


@router.get("/tudo")
def obter_tudo(projeto_id: int, sincronizar: bool = True, db: Session = Depends(get_db)):
    """Composição + Resumo + Comissionamento + DRE numa passada só (ver composicao_preco.obter_tudo)
    — usado pela Tela 10 pra não bater 4 endpoints separados a cada campo editado.
    sincronizar=false pula as 4 sincronizações pesadas ao editar campos simples."""
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    return cp.obter_tudo(db, projeto_id, sincronizar=sincronizar)


@router.post("/item")
def criar_item(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    dados = {k: v for k, v in payload.items() if k in CAMPOS_ITEM}
    if not dados.get("bloco") or dados["bloco"] not in cp.BLOCOS_COMPOSICAO:
        raise HTTPException(400, "bloco inválido")
    if not dados.get("descricao"):
        raise HTTPException(400, "descricao obrigatória")
    ordem_max = db.query(m.ComposicaoPrecoItem).filter_by(projeto_id=projeto_id, bloco=dados["bloco"]).count()
    item = m.ComposicaoPrecoItem(projeto_id=projeto_id, origem="manual",
                                  ordem=dados.pop("ordem", ordem_max), **dados)
    db.add(item)
    db.commit()
    return model_to_dict(item)


@router.put("/item/{item_id}")
def atualizar_item(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    item = db.get(m.ComposicaoPrecoItem, item_id)
    if not item:
        raise HTTPException(404)
    bp.verificar_projeto_da(item)
    bf.verificar_entidade_aberta(item)
    dados = {k: v for k, v in payload.items() if k in CAMPOS_ITEM}
    # item "sistema" (auto-sincronizado da Tela 10) não pode ter descrição/quantidade editadas à
    # mão — só custo_unitario/fator/centro_custo, senão a próxima sincronização re-cria a linha.
    if item.origem == "sistema":
        dados.pop("descricao", None)
        dados.pop("quantidade", None)
        dados.pop("bloco", None)
    for k, v in dados.items():
        setattr(item, k, v)
    db.commit()
    return model_to_dict(item)


@router.delete("/item/{item_id}")
def excluir_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(m.ComposicaoPrecoItem, item_id)
    if item:
        bp.verificar_projeto_da(item)
        bf.verificar_entidade_aberta(item)
        db.delete(item)
        db.commit()
    return {"ok": True}


@router.post("/item/{item_id}/editar")
def editar_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(m.ComposicaoPrecoItem, item_id)
    if not item:
        raise HTTPException(404)
    bp.verificar_projeto_da(item)
    bf.editar_entidade(db, item)
    return model_to_dict(item)


@router.post("/item/{item_id}/salvar")
def salvar_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(m.ComposicaoPrecoItem, item_id)
    if not item:
        raise HTTPException(404)
    bp.verificar_projeto_da(item)
    snapshot = {k: v for k, v in model_to_dict(item).items() if k not in ("id", "fechada", "calculo_snapshot_json")}
    bf.salvar_entidade(db, item, snapshot=snapshot, nome_model="ComposicaoPrecoItem")
    return model_to_dict(item)


@router.post("/restaurar-padroes")
def restaurar_padroes(projeto_id: int, bloco: str | None = None, db: Session = Depends(get_db)):
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_aberto(db, projeto_id)
    criados = cp.restaurar_padroes(db, projeto_id, bloco)
    return {"itens_criados": criados}


@router.post("/atualizar-cc-fv-arvore")
def atualizar_cc_fv_arvore(projeto_id: int, db: Session = Depends(get_db)):
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_aberto(db, projeto_id)
    return cp.atualizar_cc_fv_arvore(db, projeto_id)


# ---------------- Resumo / Comissionamento / DRE ----------------

@router.get("/resumo")
def resumo(projeto_id: int, db: Session = Depends(get_db)):
    return cp.resumo_por_bloco(db, projeto_id)


@router.get("/exportar/excel")
def exportar_excel(projeto_id: int, db: Session = Depends(get_db)):
    from ..exportacao.composicao_preco_export import gerar_excel_composicao_preco
    from ..utils import resposta_excel_projeto
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    composicao = cp.montar_composicao(db, projeto_id)
    conteudo = gerar_excel_composicao_preco(projeto, composicao)
    from ..utils import nome_arquivo_projeto
    return resposta_excel_projeto(conteudo, nome_arquivo_projeto(projeto, "Composição de Preço", "xlsx"), projeto)


@router.get("/lista-materiais")
def lista_materiais(projeto_id: int, bloco: str | None = None, centro_custo_id: int | None = None,
                     fabricante: str | None = None, db: Session = Depends(get_db)):
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    return cp.lista_materiais(db, projeto_id, bloco, centro_custo_id, fabricante)


@router.get("/lista-materiais/exportar/excel")
def exportar_lista_materiais_excel(projeto_id: int, bloco: str | None = None,
                                    centro_custo_id: int | None = None, fabricante: str | None = None,
                                    db: Session = Depends(get_db)):
    from ..exportacao.composicao_preco_export import gerar_excel_lista_materiais
    from ..utils import resposta_excel_projeto
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    linhas = cp.lista_materiais(db, projeto_id, bloco, centro_custo_id, fabricante)
    conteudo = gerar_excel_lista_materiais(projeto, linhas)
    from ..utils import nome_arquivo_projeto
    return resposta_excel_projeto(conteudo, nome_arquivo_projeto(projeto, "Lista de Materiais", "xlsx"), projeto)


@router.get("/comissionamento")
def obter_comissionamento(projeto_id: int, db: Session = Depends(get_db)):
    return cp.comissionamento(db, projeto_id)


@router.post("/comissionamento")
def add_vendedor_projeto(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    vendedor_id = payload.get("vendedor_id")
    if not vendedor_id:
        raise HTTPException(400, "vendedor_id obrigatório")
    vendedor = db.get(m.Vendedor, vendedor_id)
    if not vendedor:
        raise HTTPException(404, "Vendedor não encontrado")
    existe = (db.query(m.ComissaoVendedorProjeto)
              .filter_by(projeto_id=projeto_id, vendedor_id=vendedor_id).first())
    if existe:
        raise HTTPException(400, "Vendedor já vinculado a este projeto")
    vinc = m.ComissaoVendedorProjeto(projeto_id=projeto_id, vendedor_id=vendedor_id,
                                      percentual=payload.get("percentual", vendedor.pct_comissao_padrao or 0))
    db.add(vinc)
    db.commit()
    return model_to_dict(vinc)


@router.put("/comissionamento/{vinc_id}")
def atualizar_vendedor_projeto(vinc_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    vinc = db.get(m.ComissaoVendedorProjeto, vinc_id)
    if not vinc:
        raise HTTPException(404)
    bp.verificar_projeto_aberto(db, vinc.projeto_id)
    bf.verificar_entidade_aberta(vinc)
    if "percentual" in payload:
        vinc.percentual = payload["percentual"]
    db.commit()
    return model_to_dict(vinc)


@router.delete("/comissionamento/{vinc_id}")
def excluir_vendedor_projeto(vinc_id: int, db: Session = Depends(get_db)):
    vinc = db.get(m.ComissaoVendedorProjeto, vinc_id)
    if vinc:
        bp.verificar_projeto_aberto(db, vinc.projeto_id)
        bf.verificar_entidade_aberta(vinc)
        db.delete(vinc)
        db.commit()
    return {"ok": True}


@router.post("/comissionamento/{vinc_id}/editar")
def editar_comissao(vinc_id: int, db: Session = Depends(get_db)):
    vinc = db.get(m.ComissaoVendedorProjeto, vinc_id)
    if not vinc:
        raise HTTPException(404)
    bp.verificar_projeto_aberto(db, vinc.projeto_id)
    bf.editar_entidade(db, vinc)
    return model_to_dict(vinc)


@router.post("/comissionamento/{vinc_id}/salvar")
def salvar_comissao(vinc_id: int, db: Session = Depends(get_db)):
    vinc = db.get(m.ComissaoVendedorProjeto, vinc_id)
    if not vinc:
        raise HTTPException(404)
    bp.verificar_projeto_aberto(db, vinc.projeto_id)
    snapshot = {k: v for k, v in model_to_dict(vinc).items() if k not in ("id", "fechada", "calculo_snapshot_json")}
    bf.salvar_entidade(db, vinc, snapshot=snapshot, nome_model="ComissaoVendedorProjeto")
    return model_to_dict(vinc)


@router.get("/dre")
def dre(projeto_id: int, db: Session = Depends(get_db)):
    return cp.dre_projeto(db, projeto_id)


@router.get("/margem-negociacao")
def obter_margem_negociacao(projeto_id: int, db: Session = Depends(get_db)):
    reg = db.get(m.MargemNegociacaoProjeto, projeto_id)
    return {"projeto_id": projeto_id, "percentual": reg.percentual if reg else 0.05,
            "fechada": reg.fechada if reg else False}


@router.put("/margem-negociacao")
def salvar_margem_negociacao(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    pct = payload.get("percentual")
    if pct is None:
        raise HTTPException(400, "percentual obrigatório")
    reg = db.get(m.MargemNegociacaoProjeto, projeto_id)
    if reg:
        bf.verificar_entidade_aberta(reg)
        reg.percentual = pct
    else:
        db.add(m.MargemNegociacaoProjeto(projeto_id=projeto_id, percentual=pct))
    db.commit()
    return {"projeto_id": projeto_id, "percentual": pct}


@router.post("/margem-negociacao/editar")
def editar_margem(projeto_id: int, db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    reg = db.get(m.MargemNegociacaoProjeto, projeto_id)
    if not reg:
        reg = m.MargemNegociacaoProjeto(projeto_id=projeto_id, percentual=0.05)
        db.add(reg)
        db.commit()
    bf.editar_entidade(db, reg)
    return {"projeto_id": projeto_id, "percentual": reg.percentual, "fechada": reg.fechada}


@router.post("/margem-negociacao/salvar")
def salvar_margem_entidade(projeto_id: int, db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    reg = db.get(m.MargemNegociacaoProjeto, projeto_id)
    if not reg:
        raise HTTPException(404)
    snapshot = {"projeto_id": reg.projeto_id, "percentual": reg.percentual}
    bf.salvar_entidade(db, reg, snapshot=snapshot, nome_model="MargemNegociacaoProjeto")
    return {"projeto_id": projeto_id, "percentual": reg.percentual, "fechada": reg.fechada}


# ---------------- Fatores de Venda por Projeto (SE-202) ----------------

CAMPOS_FATOR_PROJETO = {"codigo", "tipo", "descricao", "pct_margem", "tipo_faturamento", "ordem"}


@router.get("/fatores-projeto")
def listar_fatores_projeto(projeto_id: int, db: Session = Depends(get_db)):
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    return list_to_dict(db.query(m.FatorVendaProjeto)
                         .filter_by(projeto_id=projeto_id)
                         .order_by(m.FatorVendaProjeto.ordem, m.FatorVendaProjeto.id).all())


@router.post("/fatores-projeto")
def criar_fator_projeto(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    if not payload.get("codigo") or not payload.get("descricao"):
        raise HTTPException(400, "codigo e descricao obrigatórios")
    dados = {k: v for k, v in payload.items() if k in CAMPOS_FATOR_PROJETO}
    obj = m.FatorVendaProjeto(projeto_id=projeto_id, **dados)
    db.add(obj)
    db.commit()
    return model_to_dict(obj)


@router.put("/fatores-projeto/{fator_id}")
def atualizar_fator_projeto(fator_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.FatorVendaProjeto, fator_id)
    if not obj:
        raise HTTPException(404)
    bp.verificar_projeto_aberto(db, obj.projeto_id)
    for k, v in payload.items():
        if k in CAMPOS_FATOR_PROJETO:
            setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.delete("/fatores-projeto/{fator_id}")
def excluir_fator_projeto(fator_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.FatorVendaProjeto, fator_id)
    if not obj:
        return {"ok": True}
    bp.verificar_projeto_aberto(db, obj.projeto_id)
    em_uso = db.query(m.ComposicaoPrecoItem).filter_by(fator_id=fator_id).count()
    if em_uso:
        raise HTTPException(400, f"Fator em uso em {em_uso} item(ns) — não pode ser excluído.")
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.post("/copiar-fatores-globais")
def copiar_fatores_globais(projeto_id: int, db: Session = Depends(get_db)):
    """Copia todos os FatorVenda globais como FatorVendaProjeto (se o projeto ainda não tem)."""
    bp.verificar_projeto_aberto(db, projeto_id)
    existentes = db.query(m.FatorVendaProjeto).filter_by(projeto_id=projeto_id).count()
    if existentes:
        raise HTTPException(400, "Projeto já possui fatores — use os endpoints individuais.")
    globais = db.query(m.FatorVenda).order_by(m.FatorVenda.ordem, m.FatorVenda.id).all()
    criados = 0
    for fg in globais:
        db.add(m.FatorVendaProjeto(
            projeto_id=projeto_id, codigo=fg.codigo, tipo=fg.tipo,
            descricao=fg.descricao, pct_margem=fg.pct_margem,
            tipo_faturamento=fg.tipo_faturamento, ordem=fg.ordem))
        criados += 1
    db.commit()
    return {"criados": criados}


# ---------------- Empresa do Projeto (SE-202) ----------------

@router.get("/empresa-projeto")
def obter_empresa_projeto(projeto_id: int, db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    if projeto.empresa_id and projeto.empresa:
        return model_to_dict(projeto.empresa)
    return None


@router.put("/empresa-projeto")
def vincular_empresa_projeto(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_aberto(db, projeto_id)
    empresa_id = payload.get("empresa_id")
    if empresa_id is not None:
        empresa = db.get(m.EmpresaFaturamento, empresa_id)
        if not empresa:
            raise HTTPException(404, "Empresa não encontrada")
    projeto.empresa_id = empresa_id
    db.commit()
    return {"ok": True, "empresa_id": empresa_id}


# ---------------- Condição de Pagamento — Editar / Salvar (fechada) ----------------

@router.post("/condicao-pagamento/editar")
def editar_condicao_pagamento(projeto_id: int, db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    cond = db.query(m.CondicaoPagamentoProjeto).filter_by(projeto_id=projeto_id).first()
    if not cond:
        raise HTTPException(404, "Nenhuma condição de pagamento para este projeto")
    bf.editar_entidade(db, cond)
    return model_to_dict(cond)


@router.post("/condicao-pagamento/salvar")
def salvar_condicao_pagamento_entidade(projeto_id: int, db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    cond = db.query(m.CondicaoPagamentoProjeto).filter_by(projeto_id=projeto_id).first()
    if not cond:
        raise HTTPException(404, "Nenhuma condição de pagamento para este projeto")
    snapshot = {k: v for k, v in model_to_dict(cond).items() if k not in ("id", "fechada", "calculo_snapshot_json")}
    bf.salvar_entidade(db, cond, snapshot=snapshot, nome_model="CondicaoPagamentoProjeto")
    return model_to_dict(cond)


# ---------------- Mestre: Fatores de Venda (Tela D) ----------------

@router.get("/fatores")
def listar_fatores(db: Session = Depends(get_db)):
    return list_to_dict(db.query(m.FatorVenda).order_by(m.FatorVenda.ordem, m.FatorVenda.id).all())


@router.post("/fatores")
def criar_fator(payload: dict = Body(...), db: Session = Depends(get_db)):
    if not payload.get("codigo") or not payload.get("descricao"):
        raise HTTPException(400, "codigo e descricao obrigatórios")
    obj = m.FatorVenda(**{k: v for k, v in payload.items() if hasattr(m.FatorVenda, k) and k != "id"})
    db.add(obj)
    db.commit()
    return model_to_dict(obj)


@router.put("/fatores/{fator_id}")
def atualizar_fator(fator_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.FatorVenda, fator_id)
    if not obj:
        raise HTTPException(404)
    for k, v in payload.items():
        if hasattr(obj, k) and k != "id":
            setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.delete("/fatores/{fator_id}")
def excluir_fator(fator_id: int, db: Session = Depends(get_db)):
    em_uso = db.query(m.ComposicaoPrecoItem).filter_by(fator_id=fator_id).count()
    if em_uso:
        raise HTTPException(400, f"Fator em uso em {em_uso} item(ns) de composição — não pode ser excluído.")
    obj = db.get(m.FatorVenda, fator_id)
    if obj:
        db.delete(obj)
        db.commit()
    return {"ok": True}


# ---------------- Mestre: Itens Default (Tela D) ----------------

@router.get("/itens-mestre")
def listar_itens_mestre(db: Session = Depends(get_db)):
    return list_to_dict(db.query(m.ItemComposicaoMestre)
                         .order_by(m.ItemComposicaoMestre.bloco, m.ItemComposicaoMestre.ordem).all())


@router.post("/itens-mestre")
def criar_item_mestre(payload: dict = Body(...), db: Session = Depends(get_db)):
    if payload.get("bloco") not in cp.BLOCOS_COMPOSICAO or not payload.get("descricao"):
        raise HTTPException(400, "bloco (válido) e descricao obrigatórios")
    obj = m.ItemComposicaoMestre(**{k: v for k, v in payload.items()
                                     if hasattr(m.ItemComposicaoMestre, k) and k != "id"})
    db.add(obj)
    db.commit()
    return model_to_dict(obj)


@router.put("/itens-mestre/{item_id}")
def atualizar_item_mestre(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.ItemComposicaoMestre, item_id)
    if not obj:
        raise HTTPException(404)
    for k, v in payload.items():
        if hasattr(obj, k) and k != "id":
            setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.delete("/itens-mestre/{item_id}")
def excluir_item_mestre(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.ItemComposicaoMestre, item_id)
    if obj:
        db.delete(obj)
        db.commit()
    return {"ok": True}


# ---------------- Mestre: Vendedores (Tela D) ----------------

@router.get("/vendedores")
def listar_vendedores(db: Session = Depends(get_db)):
    return list_to_dict(db.query(m.Vendedor).order_by(m.Vendedor.ordem, m.Vendedor.id).all())


@router.post("/vendedores")
def criar_vendedor(payload: dict = Body(...), db: Session = Depends(get_db)):
    if not payload.get("nome"):
        raise HTTPException(400, "nome obrigatório")
    obj = m.Vendedor(**{k: v for k, v in payload.items() if hasattr(m.Vendedor, k) and k != "id"})
    db.add(obj)
    db.commit()
    return model_to_dict(obj)


@router.put("/vendedores/{vendedor_id}")
def atualizar_vendedor(vendedor_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.Vendedor, vendedor_id)
    if not obj:
        raise HTTPException(404)
    for k, v in payload.items():
        if hasattr(obj, k) and k != "id":
            setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.delete("/vendedores/{vendedor_id}")
def excluir_vendedor(vendedor_id: int, db: Session = Depends(get_db)):
    em_uso = db.query(m.ComissaoVendedorProjeto).filter_by(vendedor_id=vendedor_id).count()
    if em_uso:
        raise HTTPException(400, f"Vendedor vinculado a {em_uso} projeto(s) — não pode ser excluído.")
    obj = db.get(m.Vendedor, vendedor_id)
    if obj:
        db.delete(obj)
        db.commit()
    return {"ok": True}


# ---------------- Mestre: Empresas de Faturamento (Tela D) ----------------

@router.get("/empresas")
def listar_empresas(db: Session = Depends(get_db)):
    return list_to_dict(db.query(m.EmpresaFaturamento).order_by(m.EmpresaFaturamento.ordem, m.EmpresaFaturamento.id).all())


@router.post("/empresas")
def criar_empresa(payload: dict = Body(...), db: Session = Depends(get_db)):
    if not payload.get("razao_social"):
        raise HTTPException(400, "razao_social obrigatória")
    obj = m.EmpresaFaturamento(**{k: v for k, v in payload.items() if hasattr(m.EmpresaFaturamento, k) and k != "id"})
    db.add(obj)
    db.commit()
    return model_to_dict(obj)


@router.put("/empresas/{empresa_id}")
def atualizar_empresa(empresa_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.EmpresaFaturamento, empresa_id)
    if not obj:
        raise HTTPException(404)
    for k, v in payload.items():
        if hasattr(obj, k) and k != "id":
            setattr(obj, k, v)
    db.commit()
    return model_to_dict(obj)


@router.delete("/empresas/{empresa_id}")
def excluir_empresa(empresa_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.EmpresaFaturamento, empresa_id)
    if obj:
        db.delete(obj)
        db.commit()
    return {"ok": True}


# ---------------- Condições de Pagamento (por projeto) ----------------

@router.get("/condicao-pagamento")
def obter_condicao_pagamento(projeto_id: int, db: Session = Depends(get_db)):
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    return cp.listar_agenda_pagamento(db, projeto_id)


@router.post("/condicao-pagamento/gerar-agenda")
def gerar_agenda_pagamento(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    if not db.get(m.Projeto, projeto_id):
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_aberto(db, projeto_id)
    cond_existente = db.query(m.CondicaoPagamentoProjeto).filter_by(projeto_id=projeto_id).first()
    if cond_existente:
        bf.verificar_entidade_aberta(cond_existente)
    percentual_sinal = payload.get("percentual_sinal")
    data_sinal = payload.get("data_sinal")
    quantidade_parcelas = payload.get("quantidade_parcelas")
    periodicidade_dias = payload.get("periodicidade_dias")
    if percentual_sinal is None or not data_sinal or not quantidade_parcelas or not periodicidade_dias:
        raise HTTPException(400, "percentual_sinal, data_sinal, quantidade_parcelas e periodicidade_dias são obrigatórios")
    return cp.gerar_agenda_pagamento(db, projeto_id, percentual_sinal, data_sinal,
                                      int(quantidade_parcelas), int(periodicidade_dias))


@router.delete("/condicao-pagamento")
def excluir_condicao_pagamento(projeto_id: int, db: Session = Depends(get_db)):
    bp.verificar_projeto_aberto(db, projeto_id)
    cond = db.query(m.CondicaoPagamentoProjeto).filter_by(projeto_id=projeto_id).first()
    if cond:
        bf.verificar_entidade_aberta(cond)
    db.query(m.CondicaoPagamentoParcela).filter_by(projeto_id=projeto_id).delete()
    db.query(m.CondicaoPagamentoProjeto).filter_by(projeto_id=projeto_id).delete()
    db.commit()
    return {"ok": True}


@router.put("/condicao-pagamento/parcela/{parcela_id}")
def atualizar_parcela_pagamento(parcela_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    parcela = db.get(m.CondicaoPagamentoParcela, parcela_id)
    if not parcela:
        raise HTTPException(404)
    bp.verificar_projeto_aberto(db, parcela.projeto_id)
    cond = db.query(m.CondicaoPagamentoProjeto).filter_by(projeto_id=parcela.projeto_id).first()
    if cond:
        bf.verificar_entidade_aberta(cond)
    if "data" in payload:
        parcela.data = payload["data"]
    if "valor" in payload:
        parcela.valor = payload["valor"]
    db.commit()
    return model_to_dict(parcela)
