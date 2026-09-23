# -*- coding: utf-8 -*-
"""Geração da lista de Equipamentos (auto, a partir da compilação) e CRUD de Centro de Custo por
projeto — infraestrutura compartilhada, usada pela Composição de Preço (Tela 10, ver
backend/composicao_preco.py) e pela Tela 7 (cadastro de Centro de Custo).

Histórico: esse router hospedava a antiga "Tela 10 — Resumo de Equipamentos e Materiais"
(resumo/materiais/equipamento-valor/exportar), fundida com a Composição de Preço em
scripts/migrar_fusao_tela10.py — os dados de preço agora vivem em ComposicaoPrecoItem
(backend/composicao_preco.py), não mais em equipamento_valor_tela10/material_tela10."""
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from .. import id_comercial as idc

router = APIRouter(prefix="/api/tela10", tags=["tela10"])


def _t(v):
    return v if (v is not None and v != "") else "—"


def _gerar_equipamentos(db: Session, projeto_id: int):
    from .compilacao_geral import _montar_compilacao_geral
    projeto, dados = _montar_compilacao_geral(db, projeto_id)
    tensao_eq = projeto.tensao_equipamentos
    tensao_comando = projeto.tensao_comando

    raw = []

    def add(tipo, descricao, fabricante, qtd, chave=None, id_comercial=None):
        # `chave` (aprovado 2026-08-08): identidade estável do item pra sincronizar_equipamentos
        # não duplicar quando a descrição muda com o recálculo (ex.: Rack Paralelo, cuja descrição
        # embute capacidade/modelo calculados, que mudam a cada ajuste de Folga Técnica/Motor).
        # Itens sem chave própria (Forçador/UC/Válvula) continuam usando a descrição como sempre.
        raw.append({"tipo": tipo, "descricao": descricao,
                     "fabricante": fabricante, "quantidade": qtd or 1,
                     "chave": chave or descricao, "id_comercial": id_comercial})

    for s in dados["sistemas"]:
        sistema = db.get(m.SistemaRefrigeracao, s["sistema_id"])

        for cam in s["camaras"]:
            f = cam["forcador"]
            if f.get("modelo_evp"):
                add("Forçador de Ar",
                    f'Forçador de Ar - {_t(f.get("fornecedor"))} - {_t(f.get("modelo_evp"))} - {_t(tensao_comando)}',
                    f.get("fornecedor"), f.get("quantidade"), id_comercial=f.get("id_comercial"))
                if f.get("modelo_valvula_base"):
                    # Agrupa pelo modelo PURO da válvula (sem o "Nx" por forçador embutido, ver
                    # compilacao.py:_rotulo_valvula_base) e multiplica a quantidade real de
                    # válvulas = nº de forçadores x nº de válvulas por forçador — antes somava só
                    # nº de forçadores, subestimando a quantidade real pela metade quando havia
                    # mais de 1 válvula por forçador (bug real).
                    qtd_forcadores = f.get("quantidade") or 1
                    qtd_valv_unit = f.get("valvula_qtd_unit") or 1
                    # tipo_expansao do Sistema é o CÓDIGO da árvore (aprovado 2026-08-08) — nome
                    # resolvido fresco aqui, o texto do memorial resumido continua idêntico.
                    tipo_expansao_nome = idc.nome_por_codigo(db, sistema.tipo_expansao) if sistema else None
                    add("Válvula de Expansão",
                        f'Válvula de Expansão {_t(tipo_expansao_nome)} - {_t(f.get("fabricante_valvula"))} - {_t(f.get("modelo_valvula_base"))}',
                        f.get("fabricante_valvula"), qtd_forcadores * qtd_valv_unit,
                        id_comercial=sistema.tipo_expansao if sistema else None)

        ru = s["rack_uc"]
        if ru.get("fonte") == "uc":
            uc_sel = (db.query(m.UnidadeSelecaoSistema)
                      .filter_by(sistema_id=sistema.id, considerado=True).first())
            fab_uc = uc_sel.fabricante_uc if uc_sel else None
            uc_id_com = None
            if uc_sel and uc_sel.catalogo_id:
                cat = db.get(m.CatalogoUC, uc_sel.catalogo_id)
                uc_id_com = cat.id_comercial if cat else None
            # N unidades idênticas em paralelo (aprovado 2026-08-13) — a quantidade do BOM = N.
            add("Unidade Condensadora",
                f'Unidade Condensadora - {_t(fab_uc)} - {_t(ru.get("modelo_tecnico"))} - {_t(tensao_eq)}',
                fab_uc, ru.get("quantidade_paralelo") or 1, id_comercial=uc_id_com)
        elif ru.get("fonte") == "rack":
            cap = ru.get("carga_total_fornecida_kcal_h")
            # N racks idênticos em paralelo — quantidade do BOM = N.
            add("Rack Paralelo",
                f'Rack Paralelo {_t(ru.get("estrutura_equipamento"))} - {_t(ru.get("modelo_compressor"))} - '
                f'Temp. Evap. {_t(sistema.temp_evaporacao)} - Capacidade {_t(cap)} - {_t(tensao_eq)}',
                ru.get("fabricante_compressor"), ru.get("quantidade_paralelo") or 1,
                chave=f"Rack Paralelo — Sistema {sistema.nome}")

        cd = s["condensador"]
        if cd.get("fonte") == "rack" and cd.get("modelo_condensador"):
            rack = sistema.rack_paralelo
            cond_id_com = None
            if rack and rack.linha_condensador:
                lc = db.query(m.LinhaCondensadorRemoto).filter_by(nome=rack.linha_condensador).first()
                cond_id_com = lc.id_comercial if lc else None
            # A descrição carrega a qtd de condensadores POR RACK ("Nx modelo", escolha do usuário);
            # a quantidade do BOM = nº de racks em paralelo, então o total = qtd_por_rack × N racks.
            add("Condensador Remoto a Ar",
                f'Condensador Remoto a Ar - {_t(rack.tipo_condensador if rack else None)} - '
                f'{_t(rack.fabricante_condensador if rack else None)} - {_t(cd.get("modelo_condensador"))} - {_t(tensao_eq)}',
                (rack.fabricante_condensador if rack else None), cd.get("quantidade_paralelo") or 1,
                id_comercial=cond_id_com)

    # Agrupa por `chave` (identidade estável), não por `descricao` (que pro Rack Paralelo muda a
    # cada recálculo) — mantém a última descrição vista pra exibição/sincronização.
    agrupado = defaultdict(lambda: {"quantidade": 0, "fabricante": None, "tipo": None, "descricao": None, "id_comercial": None})
    for item in raw:
        k = item["chave"]
        agrupado[k]["quantidade"] += item["quantidade"]
        agrupado[k]["fabricante"] = item["fabricante"]
        agrupado[k]["tipo"] = item["tipo"]
        agrupado[k]["descricao"] = item["descricao"]
        agrupado[k]["id_comercial"] = item.get("id_comercial")

    resultado = []
    for chave in sorted(agrupado.keys()):
        g = agrupado[chave]
        resultado.append({
            "descricao": g["descricao"],
            "chave": chave,
            "fabricante": g["fabricante"],
            "tipo": g["tipo"],
            "unidade": "un",
            "quantidade": g["quantidade"],
            "id_comercial": g.get("id_comercial"),
        })
    return projeto, resultado


# ---- Centro de Custos (mestre global, ver models.CentroCusto) ----

@router.get("/centro-custo")
def listar_centros(db: Session = Depends(get_db)):
    return [{"id": c.id, "codigo": c.codigo, "referencia_id": c.referencia_id,
             "etapa": c.etapa, "descricao": c.descricao, "bloco_composicao": c.bloco_composicao}
            for c in db.query(m.CentroCusto)
            .order_by(m.CentroCusto.ordem, m.CentroCusto.id).all()]


@router.post("/centro-custo")
def criar_centro(body: dict, db: Session = Depends(get_db)):
    cc = m.CentroCusto(
        codigo=body.get("codigo", "").strip(),
        referencia_id=body.get("referencia_id"),
        etapa=body.get("etapa"),
        descricao=body.get("descricao"),
        bloco_composicao=body.get("bloco_composicao"),
    )
    db.add(cc)
    db.commit()
    db.refresh(cc)
    return {"id": cc.id, "codigo": cc.codigo, "referencia_id": cc.referencia_id,
            "etapa": cc.etapa, "descricao": cc.descricao, "bloco_composicao": cc.bloco_composicao}


@router.put("/centro-custo/{cc_id}")
def atualizar_centro(cc_id: int, body: dict, db: Session = Depends(get_db)):
    cc = db.get(m.CentroCusto, cc_id)
    if not cc:
        raise HTTPException(404)
    for campo in ("codigo", "referencia_id", "etapa", "descricao", "bloco_composicao"):
        if campo in body:
            setattr(cc, campo, body[campo])
    db.commit()
    return {"id": cc.id, "codigo": cc.codigo, "referencia_id": cc.referencia_id,
            "etapa": cc.etapa, "descricao": cc.descricao, "bloco_composicao": cc.bloco_composicao}


@router.delete("/centro-custo/{cc_id}")
def excluir_centro(cc_id: int, db: Session = Depends(get_db)):
    cc = db.get(m.CentroCusto, cc_id)
    if not cc:
        raise HTTPException(404)
    db.query(m.ComposicaoPrecoItem).filter_by(centro_custo_id=cc_id).update({"centro_custo_id": None})
    db.delete(cc)
    db.commit()
    return {"ok": True}
