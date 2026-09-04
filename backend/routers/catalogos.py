"""CRUD genérico para os catálogos simples (tabelas de apoio). Catálogos com estrutura mais
rica (forçadores, expositores aninhados) têm router próprio."""
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from ..database import get_db
from ..utils import model_to_dict, list_to_dict
from ..calculos.clima import resolver_clima_estacao

router = APIRouter(prefix="/api/catalogos", tags=["catalogos"])


def _crud(path: str, model, permitir_exclusao: bool = True):
    sub = APIRouter()

    @sub.get(f"/{path}")
    def listar(db: Session = Depends(get_db)):
        return list_to_dict(db.query(model).order_by(model.id).all())

    @sub.post(f"/{path}")
    def criar(payload: dict = Body(...), db: Session = Depends(get_db)):
        obj = model(**payload)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return model_to_dict(obj)

    @sub.put(f"/{path}/{{item_id}}")
    def atualizar(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(404, "Não encontrado")
        for k, v in payload.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return model_to_dict(obj)

    if permitir_exclusao:
        @sub.delete(f"/{path}/{{item_id}}")
        def excluir(item_id: int, db: Session = Depends(get_db)):
            obj = db.get(model, item_id)
            if not obj:
                raise HTTPException(404, "Não encontrado")
            db.delete(obj)
            db.commit()
            return {"ok": True}

    router.include_router(sub)


_crud("produtos", m.Produto)
_crud("tipos-embalagem", m.TipoEmbalagem)
_crud("isolamento-parede-teto", m.IsolamentoParedeTeto)
_crud("isolamento-piso", m.IsolamentoPiso)
_crud("tipos-equipamento", m.TipoEquipamento)
_crud("condicoes-climaticas", m.CondicaoClimatica)
_crud("estados-brasileiros", m.EstadoBrasileiro)
_crud("dados-climatologicos-inmet", m.DadosClimatologicosInmet)
_crud("tabela-tipo02", m.TabelaTipo02)
_crud("fator-altura", m.FatorAltura)
_crud("fator-insolacao", m.FatorInsolacao)
_crud("faixas-trocas-ar", m.FaixaTrocasAr)
_crud("classes-produto", m.ClasseProduto)
_crud("setores-expositor", m.SetorExpositor)
_crud("fabricantes", m.Fabricante, permitir_exclusao=False)  # compartilhado entre Forçador/Válvula/
# Condensador — excluir um Fabricante cascateia (models.py) e apaga linhas dos OUTROS módulos junto;
# sem tela pra excluir fabricante de propósito (2026-07-20)
_crud("modelos-valvula", m.ModeloValvula)
_crud("configuracao-global", m.ConfiguracaoGlobal)
_crud("ids-comerciais", m.IdComercial)
_crud("classificacao-sistema-compressor", m.ClassificacaoSistemaCompressor)
_crud("lubrificante-compressor", m.LubrificanteCompressor)
_crud("dados-fisicos-compressor-bitzer", m.DadosFisicosCompressorBitzer)
_crud("tabela-disjuntor-termomagnetico", m.TabelaDisjuntorTermomagnetico)
_crud("tabela-disjuntor-ddr", m.TabelaDisjuntorDDR)
_crud("tabela-valvula-expansao", m.TabelaValvulaExpansao)
_crud("tabela-controlador-valvula", m.TabelaControladorValvula)
_crud("tabela-compatibilidade-valvula", m.TabelaCompatibilidadeValvula)
_crud("ambientes-luminotecnico", m.LookupAmbienteLuminotecnico)  # "Tela 11 - Ambientes para Estudo Luminotécnico"


@router.get("/ids-comerciais/subtree")
def subtree_ids(raiz: str, db: Session = Depends(get_db)):
    """Retorna todos os nós descendentes de `raiz` na árvore de Ids Comerciais — usado pelo
    seletor de id_pai nas telas de importação de catálogo."""
    nos = (db.query(m.IdComercial)
           .filter(m.IdComercial.codigo.like(f"{raiz}.%"))
           .order_by(m.IdComercial.codigo).all())
    raiz_no = db.query(m.IdComercial).filter_by(codigo=raiz).first()
    resultado = []
    if raiz_no:
        resultado.append({"codigo": raiz_no.codigo, "nome": raiz_no.nome})
    for n in nos:
        resultado.append({"codigo": n.codigo, "nome": n.nome})
    return resultado


# ---- Mover nó da árvore de Ids Comerciais (drag-and-drop, Configurações) — aprovado 2026-08-09 ----
# A árvore não tem FK de pai (hierarquia lida do próprio código, ver models.py:IdComercial) — mover
# um nó troca o código dele E de todo descendente, em cascata, e precisa atualizar toda referência
# solta (texto copiado) espalhada pelo banco. Por isso SEMPRE em 2 passos: preview (só lê, mostra o
# que vai mudar) e confirmar (só grava depois que o usuário já viu a lista completa).

_REFERENCIAS_CODIGO_SISTEMA = [
    "tipo_expansao", "tipo_compressao", "estrutura_compressao", "partida", "modo_operacao",
    "selecao_condensador_ar", "tipo_automacao_linhas", "automacao_linhas_fabricante",
    "modelo_controlador_linhas", "automacao", "automacao_fabricante", "modelo_controlador_equipamentos",
]

# Toda tabela com coluna id_comercial (String, cópia solta do código) — levantado via grep em
# models.py, não suposição.
_TABELAS_ID_COMERCIAL = [
    (m.LinhaForcador, "id_comercial"),
    (m.LinhaCondensadorRemoto, "id_comercial"),
    (m.CatalogoUC, "id_comercial"),
    (m.LookupPainelPorta, "id_comercial"),
    (m.CatalogoComercial, "id_comercial"),
    (m.LookupLampada, "id_comercial"),
]


def _mapa_movimentacao(db: Session, item_id: int, novo_pai_codigo: str):
    no = db.get(m.IdComercial, item_id)
    if not no:
        raise HTTPException(404, "Nó a mover não encontrado")
    if novo_pai_codigo == no.codigo or novo_pai_codigo.startswith(no.codigo + "."):
        raise HTTPException(400, "Não é possível mover um nó para dentro dele mesmo (ciclo)")
    pai = db.query(m.IdComercial).filter_by(codigo=novo_pai_codigo).first()
    if not pai:
        raise HTTPException(404, "Nó de destino não encontrado")

    prefixo = novo_pai_codigo + "."
    filhos_diretos = [f for f in db.query(m.IdComercial).filter(m.IdComercial.codigo.like(f"{prefixo}%")).all()
                       if f.codigo[len(prefixo):].isdigit()]
    nums = [int(f.codigo[len(prefixo):]) for f in filhos_diretos]
    novo_codigo_base = f"{prefixo}{(max(nums) if nums else 0) + 1}"

    descendentes = db.query(m.IdComercial).filter(m.IdComercial.codigo.like(f"{no.codigo}.%")).all()
    mapa = {no.codigo: novo_codigo_base}
    for d in descendentes:
        mapa[d.codigo] = novo_codigo_base + d.codigo[len(no.codigo):]
    return no, mapa


def _levantar_afetados(db: Session, mapa: dict) -> list:
    afetados = []
    for codigo_antigo, codigo_novo in mapa.items():
        for campo in _REFERENCIAS_CODIGO_SISTEMA:
            for s in db.query(m.SistemaRefrigeracao).filter(getattr(m.SistemaRefrigeracao, campo) == codigo_antigo).all():
                afetados.append({"tabela": "SistemaRefrigeracao", "id": s.id, "identificacao": s.nome,
                                  "campo": campo, "de": codigo_antigo, "para": codigo_novo})
        for p in db.query(m.Projeto).filter(m.Projeto.tipo_comando == codigo_antigo).all():
            afetados.append({"tabela": "Projeto", "id": p.id, "identificacao": p.codigo_projeto,
                              "campo": "tipo_comando", "de": codigo_antigo, "para": codigo_novo})
        for modelo, campo in _TABELAS_ID_COMERCIAL:
            for obj in db.query(modelo).filter(getattr(modelo, campo) == codigo_antigo).all():
                nome_obj = getattr(obj, "nome", None) or getattr(obj, "modelo", None) or obj.id
                afetados.append({"tabela": modelo.__name__, "id": obj.id, "identificacao": nome_obj,
                                  "campo": campo, "de": codigo_antigo, "para": codigo_novo})
    return afetados


@router.post("/ids-comerciais/{item_id}/mover-preview")
def mover_id_comercial_preview(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    novo_pai_codigo = (payload.get("novo_pai_codigo") or "").strip()
    no, mapa = _mapa_movimentacao(db, item_id, novo_pai_codigo)
    return {"nó_movido": no.codigo, "mapa": mapa, "afetados": _levantar_afetados(db, mapa)}


@router.post("/ids-comerciais/{item_id}/mover-confirmar")
def mover_id_comercial_confirmar(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    novo_pai_codigo = (payload.get("novo_pai_codigo") or "").strip()
    no, mapa = _mapa_movimentacao(db, item_id, novo_pai_codigo)

    for codigo_antigo, codigo_novo in mapa.items():
        alvo = db.query(m.IdComercial).filter_by(codigo=codigo_antigo).first()
        if alvo:
            alvo.codigo = codigo_novo

    for codigo_antigo, codigo_novo in mapa.items():
        for campo in _REFERENCIAS_CODIGO_SISTEMA:
            db.query(m.SistemaRefrigeracao).filter(getattr(m.SistemaRefrigeracao, campo) == codigo_antigo) \
                .update({campo: codigo_novo})
        db.query(m.Projeto).filter(m.Projeto.tipo_comando == codigo_antigo).update({"tipo_comando": codigo_novo})
        for modelo, campo in _TABELAS_ID_COMERCIAL:
            db.query(modelo).filter(getattr(modelo, campo) == codigo_antigo).update({campo: codigo_novo})

    db.commit()
    return {"ok": True, "mapa": mapa}


@router.get("/tabela02-faixas")
def obter_tabela02_faixas(db: Session = Depends(get_db)):
    """Matriz completa (150 faixas de área x 7 tipos) da Tabela 02 real, para exibir/editar de
    uma vez em Configurações — igual à planilha de origem do usuário."""
    tipos = db.query(m.TabelaTipo02).order_by(m.TabelaTipo02.id).all()
    faixas_db = db.query(m.FaixaAreaTabela02).order_by(m.FaixaAreaTabela02.area_de).all()
    brackets = {}
    for f in faixas_db:
        key = (f.area_de, f.area_ate)
        brackets.setdefault(key, {})[f.tabela02_id] = f.carga_kcal_h
    faixas = [{"area_de": k[0], "area_ate": k[1], "valores": v} for k, v in sorted(brackets.items())]
    return {"tipos": [{"id": t.id, "tipo": t.tipo} for t in tipos], "faixas": faixas}


@router.put("/tabela02-faixas")
def salvar_tabela02_faixas(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Substitui a matriz inteira pela versão editada (mesma lógica da matriz de forçadores)."""
    db.query(m.FaixaAreaTabela02).delete()
    for faixa in payload.get("faixas", []):
        for tabela02_id, valor in (faixa.get("valores") or {}).items():
            if valor is None or valor == "":
                continue
            db.add(m.FaixaAreaTabela02(tabela02_id=int(tabela02_id), area_de=faixa["area_de"],
                                        area_ate=faixa["area_ate"], carga_kcal_h=float(valor)))
    db.commit()
    return {"ok": True}


@router.get("/clima/estacoes")
def listar_estacoes(busca: str = None, uf: str = None, db: Session = Depends(get_db)):
    """Lista de estações INMET para a Tela 1 escolher manualmente (não precisa bater com o nome
    exato da cidade do projeto — o usuário pode escolher a estação mais próxima)."""
    q = db.query(m.CondicaoClimatica)
    if uf:
        q = q.filter(m.CondicaoClimatica.uf == uf.upper())
    if busca:
        q = q.filter(m.CondicaoClimatica.cidade.ilike(f"%{busca}%"))
    return list_to_dict(q.order_by(m.CondicaoClimatica.cidade).limit(500).all())


@router.get("/clima/resolver")
def resolver_clima(estacao_id: int, criterio: str = "pico_sazonal", db: Session = Depends(get_db)):
    """Devolve TBS/TBU/UR da estação conforme o critério de projeto escolhido (Tela 1)."""
    est = db.get(m.CondicaoClimatica, estacao_id)
    if not est:
        return {"encontrado": False}
    tbs, tbu, ur = resolver_clima_estacao(est, criterio)
    return {"encontrado": True, "cidade": est.cidade, "uf": est.uf,
            "temp_bulbo_seco": tbs, "temp_bulbo_umido": tbu, "umidade_relativa": ur}


@router.get("/clima-inmet/estacoes")
def listar_estacoes_inmet(uf: str = None, busca: str = None, db: Session = Depends(get_db)):
    """Tela 1 - Dados Climatológicos INMET 1990-2020 (Configurações) — lista de estações pro campo
    Estação Climatológica, filtrada por Estado (UF) selecionado."""
    q = db.query(m.DadosClimatologicosInmet)
    if uf:
        q = q.filter(m.DadosClimatologicosInmet.uf == uf.upper())
    if busca:
        q = q.filter(m.DadosClimatologicosInmet.nome_estacao.ilike(f"%{busca}%"))
    return list_to_dict(q.order_by(m.DadosClimatologicosInmet.nome_estacao).limit(500).all())


@router.get("/clima-inmet/resolver")
def resolver_clima_inmet(estacao_id: int, db: Session = Depends(get_db)):
    """Fonte única de Temperatura/UR do projeto (Tela 1): Temp. Máxima Histórica + UR Média
    Histórica da estação selecionada — substitui o antigo seletor de Critério de Projeto."""
    est = db.get(m.DadosClimatologicosInmet, estacao_id)
    if not est:
        return {"encontrado": False}
    return {"encontrado": True, "nome_estacao": est.nome_estacao, "uf": est.uf,
            "temp_bulbo_seco": est.temp_maxima_historica, "umidade_relativa": est.ur_media_historica}


@router.get("/bancos-expositor")
def listar_bancos(db: Session = Depends(get_db)):
    bancos = db.query(m.BancoExpositor).all()
    return [{**model_to_dict(b), "modelos": list_to_dict(b.modelos)} for b in bancos]


@router.post("/bancos-expositor")
def criar_banco(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = m.BancoExpositor(nome=payload["nome"])
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.delete("/bancos-expositor/{banco_id}")
def excluir_banco(banco_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.BancoExpositor, banco_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.post("/modelos-expositor")
def criar_modelo_expositor(payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = m.ModeloExpositor(**payload)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.put("/modelos-expositor/{item_id}")
def atualizar_modelo_expositor(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    obj = db.get(m.ModeloExpositor, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    for k, v in payload.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return model_to_dict(obj)


@router.delete("/modelos-expositor/{item_id}")
def excluir_modelo_expositor(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(m.ModeloExpositor, item_id)
    if not obj:
        raise HTTPException(404, "Não encontrado")
    db.delete(obj)
    db.commit()
    return {"ok": True}
