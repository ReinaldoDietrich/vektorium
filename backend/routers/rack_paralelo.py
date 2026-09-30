# -*- coding: utf-8 -*-
"""Tela 6 — Rack Paralelo: Informações Rack + Lista de Materiais Rack. Um registro de RackParalelo
por sistema com tipo_compressao = "Rack Paralelo" — criado automaticamente (get-or-create) na
primeira vez que a Tela 6 é aberta pra aquele sistema, já com a Lista de Materiais padrão."""
import json
import re
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models as m
from .. import campo_catalogo as cpc
from ..database import get_db
from ..utils import model_to_dict, list_to_dict
from ..calculos.comum import folga_percentual
from . import _bloqueio_projeto as bp
from . import _bloqueio_fechada as bf
from ..calc_puro_uc_rack import calcular_compressores_de_dados
from ..calculos import condensador as cc_calc

router = APIRouter(prefix="/api/rack-paralelo", tags=["rack-paralelo"])


def _gas_normalizado(s):
    """Remove separadores/caixa pra comparar o gás do sistema (ex.: 'R-404A') com o gás gravado no
    catálogo de polinômios (ex.: 'R404A') — mesmo dado, formatos diferentes entre as duas telas."""
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _volts_fases(texto):
    """Extrai (volts, fases) tolerando os formatos usados no app: '380V/3F/60Hz' (Tensão de
    Equipamentos do projeto, Tela 1) e '380V-3-60Hz' (Tensao gravada em PolinomioCompressor, sem
    letra F pras fases) — mesmo dado, dois separadores diferentes. Devolve (None, None) se não achar
    volts, pra nunca "quase-casar" por acidente."""
    if not texto:
        return None, None
    m_v = re.search(r"(\d+)\s*V", texto, re.I)
    if not m_v:
        return None, None
    resto = texto[m_v.end():]
    m_fh = re.search(r"[^0-9]*(\d+)[^0-9]*(\d+)\s*H", resto, re.I)
    fases = int(m_fh.group(1)) if m_fh else None
    return int(m_v.group(1)), fases

# Lista de Materiais Rack padrão — mesma lista/ordem da planilha do usuário. (categoria, descricao, modelo)
MATERIAIS_PADRAO = [
    ("Geral", "Resistência de Cárter", None),
    ("Descarga", "Coletor Descarga", "COBRE (kg)"),
    ("Descarga", "Válvula retenção compressor", None),
    ("Descarga", "Flexivel", None),
    ("Descarga", "Valvula retenção separador de oleo", None),
    ("Descarga", "Valvula esfera separador de oleo", None),
    ("Descarga", "Manometro", None),
    ("Descarga", "Pressostato de Alta", None),
    ("Descarga", "Mangueiras", None),
    ("Líquido", "Tanque de Líquido", None),
    ("Líquido", "Carcaça Filtro Secador", None),
    ("Líquido", "Elemento Filtrante Líquido", None),
    ("Líquido", "Visor de Liquído", None),
    ("Líquido", "Válvulas esfera Tanque de liquido", None),
    ("Líquido", "Válvulas esfera (Flauta)", None),
    ("Líquido", "Distribuidor de Líquido", None),
    ("Sucção", "Coletor Sucção", "COBRE (kg)"),
    ("Sucção", "Coletor Sucção", "AÇO"),
    ("Sucção", "Acumulador de Sucção", None),
    ("Sucção", "Carcaça Filtro Sucção", None),
    ("Sucção", "Elemento Filtrante Sucção", None),
    ("Sucção", "Válvulas esfera Sucção (Flauta)", None),
    ("Sucção", "Manometro", None),
    ("Sucção", "Pressostato Duplo", None),
    ("Sistema de Óleo", "Separador Óleo", None),
    ("Sistema de Óleo", "Boia de Óleo", None),
    ("Sistema de Óleo", "Boia de Óleo - Adaptador", None),
    ("Sistema de Óleo", "Filtro de oleo", None),
    ("Sistema de Óleo", "Valvula Tanque 1/4", None),
    ("Diversos", "Estrutura Rack", "AÇO"),
    ("Diversos", "Carenagem Fechamento", "AÇO"),
    ("Diversos", "Elétrica Geral", "-"),
    ("Diversos", "Tubulação", "COBRE"),
    ("Diversos", "Isolamento", "Espuma Elastomerica"),
    ("Diversos", "Embalagem", "Engradado de Madeira"),
    ("Diversos", "Frete dos componentes", "Fornecedor/Fabrica Thermo"),
    ("Diversos", "Mão de Obra", "Montador Fabrica"),
    ("Diversos", "Nitrogênio", "Montagens"),
    ("Diversos", "Kanban", "Montagens"),
]

CAMPOS_RACK = {
    "quantidade_compressores", "quantidade_paralelo", "folga_tecnica_pct", "filtro_motor_compressor", "linha_compressor", "fabricante_compressor",
    "corrente_maxima_trabalho_a", "carga_oleo_l", "conexao_descarga", "conexao_succao", "hp_total",
    "tanque_liquido_l", "carga_gas_estimada_kg",
    "fabricante_condensador", "linha_condensador", "tipo_condensador", "filtro_fpi_condensador",
    "filtro_polos_rpm_condensador", "folga_condensador_pct", "protecao_aletas_condensador",
    "quantidade_condensadores", "notas_condensador",
}
# "Modelo técnico" não existe pra Rack (fabricado sob medida, sem catálogo comercial — só Unidade
# Condensadora tem). "Modelo Comercial" não é mais texto livre, é gerado automaticamente (ver
# _modelo_comercial_rack) — ficou de fora de CAMPOS_RACK de propósito, não é mais editável via PUT.
# "Tensão" também saiu de CAMPOS_RACK: passa a ser sempre a Tensão de Equipamentos do projeto
# (Tela 1), nunca um valor próprio do rack — ver _serializar.
# Modelo Compressor/COP/Capacidade unitária/Carga Total Fornecida/Calor Rejeitado/Potência Total/
# Corrente Nominal/Vazão Mássica saíram de CAMPOS_RACK: passam a ser sempre derivados da Seleção de
# Compressores (ver resumo_compressores), nunca digitados — o que o polinômio não entrega (Corrente
# Máxima, Carga de Óleo, Conexões, Tanque de Líquido, Carga de Gás Estimada) continua manual até
# existir catálogo com esse dado; HP Total é sempre manual por definição.


# ---------- Opções de condensador do rack (N por rack; a considerada espelha as colunas do rack) ----------

def _condensador_considerado(rack: "m.RackParalelo"):
    for c in rack.condensadores:
        if c.considerado:
            return c
    return rack.condensadores[0] if rack.condensadores else None


def _sync_rack_do_considerado(rack: "m.RackParalelo"):
    """Copia os 9 campos da opção CONSIDERADA para as colunas espelho do rack (fonte que a
    compilação/consumo/resumo já leem, sem mudança)."""
    c = _condensador_considerado(rack)
    if c:
        for campo in m.CAMPOS_CONDENSADOR:
            setattr(rack, campo, getattr(c, campo))


def _garantir_condensador(db: Session, rack: "m.RackParalelo"):
    """Todo rack tem >=1 opção. Rack pré-migração/novo: cria uma considerada a partir das colunas
    atuais do rack (espelho)."""
    if not rack.condensadores:
        db.add(m.RackCondensadorSelecao(rack_id=rack.id, considerado=True,
                                        **{c: getattr(rack, c) for c in m.CAMPOS_CONDENSADOR}))
        db.flush()


def _modelo_comercial_rack(rack: "m.RackParalelo", sistema: "m.SistemaRefrigeracao",
                            capacidade_total_kcal_h=None):
    """RK + capacidade(kW) + qtd. compressores + letra do fabricante do compressor + CC/SC
    (carenagem) + CR (condensador remoto — sempre, Rack Paralelo não tem variante onboard nesse
    app, ver _bloco_condensador) + CP/SP (com/sem supervisão) — código próprio do usuário, sem
    relação com nomenclatura de catálogo (rack é sob medida). Todos os componentes vêm de dados
    já existentes no sistema/rack — nenhum campo novo. Só entra na composição o que já está
    preenchido; se não tiver nada ainda, devolve None.
    capacidade_total_kcal_h vem da Seleção de Compressores (soma das capacidades escolhidas
    automaticamente) — Carga Total Fornecida deixou de ser digitada, então não dá mais pra ler
    direto de rack.carga_total_fornecida_kcal_h (ver _serializar).
    CP/SP reaproveita SistemaRefrigeracao.automacao ("Gerenciamento" = com supervisão, "Eletromecânico"
    = sem) — ajustar se esse não for o conceito de "supervisão" pretendido."""
    if not rack:
        return None
    partes = ["RK"]
    tem_dado_real = False
    if capacidade_total_kcal_h:
        from ..calculos.comum import W_PARA_KCAL_H
        partes.append(str(round(capacidade_total_kcal_h / 1000 / W_PARA_KCAL_H)))
        tem_dado_real = True
    if rack.quantidade_compressores:
        partes.append(str(int(rack.quantidade_compressores)))
        tem_dado_real = True
    if rack.fabricante_compressor:
        partes.append(rack.fabricante_compressor.strip()[0].upper())
        tem_dado_real = True
    if sistema and sistema.estrutura_compressao:
        partes.append("CC" if sistema.estrutura_compressao == "4.1.2.1.1" else "SC")  # Carenado
        tem_dado_real = True
    partes.append("CR")
    if sistema and sistema.automacao:
        partes.append("CP" if sistema.automacao == "1.3.2" else "SP")  # Gerenciamento Eletrônico
        tem_dado_real = True
    return "".join(partes) if tem_dado_real else None


def _carga_requerida_sistema(db: Session, sistema: m.SistemaRefrigeracao) -> float:
    """Mesma soma de carga térmica requerida usada na seleção de UC (Tela 1) — total das câmaras
    completo/simples + expositores do sistema. Bug corrigido: essa função dizia incluir expositores
    no docstring mas nunca somava sistema.expositores de verdade, deixando a carga requerida do
    Rack sistematicamente menor que a da UC pro mesmo sistema."""
    from ..calc_service import calcular_camara_completo_seguro as calcular_camara_completo, calcular_camara_simples_seguro as calcular_camara_simples
    from .expositores import _carga_termica as _carga_expositor
    total = 0.0
    for c in sistema.camaras_completo:
        total += calcular_camara_completo(db, c)["capacidade_requerida"]
    for c in sistema.camaras_simples:
        total += calcular_camara_simples(db, c)["capacidade_requerida"]
    for e in sistema.expositores:
        total += _carga_expositor(e)
    return total


def _n_paralelo(rack: m.RackParalelo) -> int:
    """Nº de racks IDÊNTICOS em paralelo (default 1). Cada rack atende carga_sistema ÷ N."""
    return max(rack.quantidade_paralelo or 1, 1)


def _carga_por_rack(db: Session, rack: m.RackParalelo) -> float:
    """Demanda que CADA rack em paralelo precisa atender = carga total do sistema ÷ N (aprovado
    2026-08-13). Único ponto onde a demanda é dividida: folga técnica, distribuição entre posições
    e envelope seguem idênticos, só recebendo a carga já dividida."""
    return _carga_requerida_sistema(db, rack.sistema) / _n_paralelo(rack)


def _carga_gas_estimada_sistema(db: Session, sistema: m.SistemaRefrigeracao, tanque_liquido_l):
    """Soma da carga de gás de todos os forçadores CONSIDERADOS do sistema (por unidade x
    quantidade de cada câmara) + tanque de líquido, ou x1,5 sem tanque (ver carga_gas_estimada,
    calculos/comum.py) -- aprovado 2026-08-11, usado no Resumo do Rack (mesma fórmula da
    Compilação Geral, Tela 8)."""
    from ..calc_service import calcular_camara_completo_seguro as calcular_camara_completo, calcular_camara_simples_seguro as calcular_camara_simples
    from ..calculos.comum import carga_gas_estimada
    soma = 0.0
    tem_dado = False
    for c in sistema.camaras_completo:
        calc = calcular_camara_completo(db, c)
        f = next((x for x in calc["forcadores"] if x.get("considerado") and x.get("modelo_resultante")), None)
        if f and f.get("carga_gas_kg") and f.get("quantidade"):
            soma += f["carga_gas_kg"] * f["quantidade"]
            tem_dado = True
    for c in sistema.camaras_simples:
        calc = calcular_camara_simples(db, c)
        f = next((x for x in calc["forcadores"] if x.get("considerado") and x.get("modelo_resultante")), None)
        if f and f.get("carga_gas_kg") and f.get("quantidade"):
            soma += f["carga_gas_kg"] * f["quantidade"]
            tem_dado = True
    if not tem_dado:
        return None
    return carga_gas_estimada(soma, tanque_liquido_l)


def _serializar(db: Session, rack: m.RackParalelo) -> dict:
    # carga_requerida aqui é POR RACK (carga do sistema ÷ N em paralelo) — é contra ela que a folga
    # de UM rack faz sentido. carga_sistema_total_kcal_h fica à parte, pra referência na tela.
    n_paralelo = _n_paralelo(rack)
    carga_sistema_total = _carga_requerida_sistema(db, rack.sistema)
    carga_requerida = carga_sistema_total / n_paralelo
    capacidade_total = None
    if rack.quantidade_compressores:
        dados_comp = listar_compressores(rack.id, db)
        capacidade_total = sum((p["resultado"]["capacidade_kcal_h"] if p["resultado"] else 0)
                                for p in dados_comp["posicoes"]) or None
    folga_real = round(folga_percentual(capacidade_total, carga_requerida), 1) if capacidade_total else None
    projeto = rack.sistema.projeto if rack.sistema else None
    return {**model_to_dict(rack), "materiais": list_to_dict(rack.materiais),
            "condensadores": list_to_dict(rack.condensadores),
            "modelo_tecnico": None,
            "modelo_comercial": _modelo_comercial_rack(rack, rack.sistema, capacidade_total),
            "tensao": projeto.tensao_equipamentos if projeto else None,
            "quantidade_paralelo": n_paralelo,
            "carga_sistema_total_kcal_h": round(carga_sistema_total, 1),
            "carga_requerida_kcal_h": round(carga_requerida, 1), "folga_real_pct": folga_real}


def _get_or_create(db: Session, sistema_id: int) -> m.RackParalelo:
    sistema = db.get(m.SistemaRefrigeracao, sistema_id)
    if not sistema:
        raise HTTPException(404, "Sistema não encontrado")
    if sistema.rack_paralelo:
        rack = sistema.rack_paralelo
        if not rack.condensadores:            # rack pré-migração: garante a opção considerada
            _garantir_condensador(db, rack)
            db.commit()
        return rack
    rack = m.RackParalelo(sistema_id=sistema_id)
    db.add(rack)
    db.flush()
    for categoria, descricao, modelo in MATERIAIS_PADRAO:
        db.add(m.MaterialRack(rack_id=rack.id, categoria=categoria, descricao=descricao, modelo=modelo))
    _garantir_condensador(db, rack)           # rack novo nasce com 1 opção de condensador considerada
    db.commit()
    db.refresh(rack)
    return rack


def _garantir_um_considerado(db: Session, sistema: "m.SistemaRefrigeracao"):
    if sistema.racks and not any(r.considerado for r in sistema.racks):
        sistema.racks[0].considerado = True
        db.commit()


@router.get("")
def obter(sistema_id: int, db: Session = Depends(get_db)):
    """Lista TODOS os racks do sistema (alternativas com `considerado`). Cria o 1º se não houver."""
    _get_or_create(db, sistema_id)                       # garante ao menos 1 rack
    sistema = db.get(m.SistemaRefrigeracao, sistema_id)
    _garantir_um_considerado(db, sistema)
    return {"racks": [_serializar(db, r) for r in sistema.racks]}


@router.post("")
def criar_rack(sistema_id: int, db: Session = Depends(get_db)):
    """Novo rack (opção alternativa, NÃO considerado) — na tela nasce retraído."""
    sistema = db.get(m.SistemaRefrigeracao, sistema_id)
    if not sistema:
        raise HTTPException(404, "Sistema não encontrado")
    bp.verificar_projeto_da(sistema)
    rack = m.RackParalelo(sistema_id=sistema_id, considerado=False)
    db.add(rack)
    db.flush()
    for categoria, descricao, modelo in MATERIAIS_PADRAO:
        db.add(m.MaterialRack(rack_id=rack.id, categoria=categoria, descricao=descricao, modelo=modelo))
    _garantir_condensador(db, rack)
    db.commit()
    db.refresh(rack)
    return _serializar(db, rack)


@router.put("/{rack_id}/considerar")
def considerar_rack(rack_id: int, db: Session = Depends(get_db)):
    rack = db.get(m.RackParalelo, rack_id)
    if not rack:
        raise HTTPException(404, "Rack não encontrado")
    bp.verificar_projeto_da(rack)
    bf.verificar_pai_aberto(rack)
    for r in rack.sistema.racks:
        r.considerado = (r.id == rack_id)
    db.commit()
    return {"ok": True}


@router.delete("/{rack_id}")
def excluir_rack(rack_id: int, db: Session = Depends(get_db)):
    rack = db.get(m.RackParalelo, rack_id)
    if not rack:
        return {"ok": True}
    bp.verificar_projeto_da(rack)
    bf.verificar_entidade_aberta(rack)
    sistema = rack.sistema
    if len(sistema.racks) <= 1:
        raise HTTPException(400, "O sistema precisa ter ao menos um rack.")
    era = rack.considerado
    db.delete(rack)
    db.flush()
    if era and sistema.racks:                            # apagou o considerado → promove o 1º restante
        sistema.racks[0].considerado = True
    db.commit()
    return {"ok": True}


@router.post("/{rack_id}/editar")
def abrir_edicao(rack_id: int, db: Session = Depends(get_db)):
    rack = db.get(m.RackParalelo, rack_id)
    if not rack:
        raise HTTPException(404, "Rack não encontrado")
    bp.verificar_projeto_da(rack)
    bf.editar_entidade(db, rack)
    return _serializar(db, rack)


@router.post("/{rack_id}/salvar")
def fechar_entidade(rack_id: int, db: Session = Depends(get_db)):
    rack = db.get(m.RackParalelo, rack_id)
    if not rack:
        raise HTTPException(404, "Rack não encontrado")
    bp.verificar_projeto_da(rack)
    snapshot = model_to_dict(rack)
    bf.salvar_entidade(db, rack, snapshot=snapshot, nome_model="RackParalelo")
    return _serializar(db, rack)


@router.put("/{rack_id}")
def atualizar(rack_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    rack = db.get(m.RackParalelo, rack_id)
    if not rack:
        raise HTTPException(404, "Rack não encontrado")
    bp.verificar_projeto_da(rack)
    bf.verificar_entidade_aberta(rack)
    for k, v in payload.items():
        if k in CAMPOS_RACK:
            setattr(rack, k, v)
    if "nomenclatura_condensador_selecionada" in payload:
        rack.nomenclatura_condensador_selecionada = json.dumps(payload["nomenclatura_condensador_selecionada"] or {})
    # Se o PUT mexeu em campos de condensador, propaga pra opção CONSIDERADA (mantém espelho ↔ opção).
    if any(k in payload for k in m.CAMPOS_CONDENSADOR):
        _garantir_condensador(db, rack)
        c = _condensador_considerado(rack)
        if c:
            for campo in m.CAMPOS_CONDENSADOR:
                setattr(c, campo, getattr(rack, campo))
    db.commit()
    return _serializar(db, rack)


# ---------- CRUD das opções de condensador (N por rack) ----------

@router.post("/{rack_id}/condensadores")
def add_condensador(rack_id: int, db: Session = Depends(get_db)):
    """Nova opção de condensador (vazia, NÃO considerada) — na tela nasce retraída."""
    rack = db.get(m.RackParalelo, rack_id)
    if not rack:
        raise HTTPException(404, "Rack não encontrado")
    bp.verificar_projeto_da(rack)
    bf.verificar_pai_aberto(rack)
    opt = m.RackCondensadorSelecao(rack_id=rack_id, considerado=False)
    db.add(opt)
    db.commit()
    db.refresh(opt)
    return model_to_dict(opt)


@router.put("/condensadores/{opt_id}")
def atualizar_condensador(opt_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    opt = db.get(m.RackCondensadorSelecao, opt_id)
    if not opt:
        raise HTTPException(404, "Opção de condensador não encontrada")
    bp.verificar_projeto_da(opt.rack)
    bf.verificar_pai_aberto(opt.rack)
    for k, v in payload.items():
        if k == "nomenclatura_condensador_selecionada":
            opt.nomenclatura_condensador_selecionada = json.dumps(v or {})
        elif k in m.CAMPOS_CONDENSADOR:
            setattr(opt, k, v)
    if opt.considerado:                       # editou a considerada -> atualiza o espelho do rack
        _sync_rack_do_considerado(opt.rack)
    db.commit()
    return model_to_dict(opt)


@router.put("/condensadores/{opt_id}/considerar")
def considerar_condensador(opt_id: int, db: Session = Depends(get_db)):
    opt = db.get(m.RackCondensadorSelecao, opt_id)
    if not opt:
        raise HTTPException(404, "Opção de condensador não encontrada")
    bp.verificar_projeto_da(opt.rack)
    bf.verificar_pai_aberto(opt.rack)
    for c in opt.rack.condensadores:
        c.considerado = (c.id == opt_id)
    _sync_rack_do_considerado(opt.rack)
    db.commit()
    return {"ok": True}


@router.delete("/condensadores/{opt_id}")
def remove_condensador(opt_id: int, db: Session = Depends(get_db)):
    opt = db.get(m.RackCondensadorSelecao, opt_id)
    if not opt:
        return {"ok": True}
    bp.verificar_projeto_da(opt.rack)
    bf.verificar_pai_aberto(opt.rack)
    rack = opt.rack
    if len(rack.condensadores) <= 1:
        raise HTTPException(400, "O rack precisa ter ao menos uma opção de condensador.")
    era = opt.considerado
    db.delete(opt)
    db.flush()
    if era and rack.condensadores:            # se apagou a considerada, promove a primeira restante
        rack.condensadores[0].considerado = True
    _sync_rack_do_considerado(rack)
    db.commit()
    return {"ok": True}


@router.put("/materiais/{item_id}")
def atualizar_material(item_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    item = db.get(m.MaterialRack, item_id)
    if not item:
        raise HTTPException(404, "Item não encontrado")
    bp.verificar_projeto_da(item.rack)
    bf.verificar_pai_aberto(item.rack)
    for campo in ("modelo", "quantidade"):
        if campo in payload:
            setattr(item, campo, payload[campo])
    db.commit()
    return {"ok": True}


# ---------- Seleção de compressores por polinômio (1 a 5 posições) ----------

def _te_tc_projeto(sistema: m.SistemaRefrigeracao):
    """Te = temp_evaporacao do sistema. Tc = temp. ambiente do projeto + delta_condensacao (Rack
    Paralelo sempre tem condensador remoto -- ver _modelo_comercial_rack)."""
    projeto = sistema.projeto
    te = sistema.temp_evaporacao
    tc = None
    if projeto is not None and projeto.temp_ambiente is not None and sistema.delta_condensacao is not None:
        tc = projeto.temp_ambiente + sistema.delta_condensacao
    return te, tc


def _sincronizar_posicoes(db: Session, rack: m.RackParalelo):
    """Garante uma linha CompressorRack por posição de 1 até quantidade_compressores (cria as que
    faltam, remove as que sobram se o usuário diminuiu a quantidade -- perde a selecao da posicao
    removida, mas nunca mistura posicao com outro rack)."""
    n = int(rack.quantidade_compressores or 0)
    n = max(0, min(5, n))
    existentes = {c.posicao: c for c in rack.compressores}
    for pos in range(1, n + 1):
        if pos not in existentes:
            db.add(m.CompressorRack(rack_id=rack.id, posicao=pos))
    for pos, c in existentes.items():
        if pos > n:
            db.delete(c)
    db.commit()
    db.refresh(rack)


def _percentuais_posicoes(rack: m.RackParalelo):
    """Devolve {posicao: percentual} pras N posicoes -- so a posicao 1 (master) e editavel, o
    saldo (100 - master) e dividido em partes iguais entre as demais."""
    posicoes = sorted(rack.compressores, key=lambda c: c.posicao)
    n = len(posicoes)
    if n == 0:
        return {}
    master = next((c for c in posicoes if c.posicao == 1), None)
    pct_master = master.percentual_sistema if (master and master.percentual_sistema is not None) else (100.0 / n)
    resultado = {1: pct_master}
    restantes = n - 1
    if restantes > 0:
        pct_resto = (100.0 - pct_master) / restantes
        for c in posicoes:
            if c.posicao != 1:
                resultado[c.posicao] = pct_resto
    return resultado


def _extrair_numero(texto: str):
    """Extrai o valor numérico de um campo de texto de catálogo tipo '9.1 A' (Dados Físicos
    Compressores Bitzer são todos String, formato livre de planilha) -- None se não achar número."""
    if not texto:
        return None
    match = re.search(r"[\d.,]+", texto)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def _normalizar_modelo_polinomio(modelo: str) -> str:
    """Casa o nome de modelo do catálogo de Polinômios (ex.: "2CES-3Y-20D", com sufixo de corrente
    tipo "-20D"/"-35D"/"-20P"/"-35P" — confirmado pelo usuário 2026-07-18 que "D" é referência de
    corrente, não gás; "P" segue o mesmo padrão) com o nome-base usado em Dados Físicos Compressores
    Bitzer (ex.: "2CES-3(Y)"). Modelos de outras subfamílias (H/P/Z/SL não presentes no R01a) não
    casam — esperado, ficam sem filtro extra (fail-open)."""
    base = re.sub(r"-\d+[A-Za-z]+$", "", modelo)  # remove sufixo de corrente
    base = re.sub(r"Y$", "", base)                 # remove marcador de variante Y solto no fim
    return base


def _envelope_bitzer_por_motor(db: Session, linha: str):
    """Tela 6 - Classificação de Sistemas e Envelope Compressores (Configurações): pra cada
    motor_compressor (1/2/3) cadastrado, devolve a faixa "Regra" de Temp. Evaporação da família
    (Semi-Hermético ou Duplo Estágio) daquela linha — INDEPENDENTE da Classificação do Sistema
    (Alta/Média/Baixa). A faixa de operação de um compressor é definida pelo motor dele, não pelo
    rótulo do sistema (ver discussão real 2026-07-18: "a regra que quero é quanto à faixa de
    operação, e não sistema Alta/Média/Baixa"). Devolve {motor_compressor: (te_min, te_max) | None}
    — None = célula "Não Aplicável" na planilha de origem (ex.: Duplo Estágio pros motores 1/2) —
    ou seja, esse motor NÃO tem envelope válido nessa família, exclui sempre. Motor ausente do dict
    inteiro (não devia acontecer, os 3 motores sempre têm linha na tabela) fica sem filtro."""
    campo_min = "semi_hermetico_te_min" if linha == "Semi-Hermético" else "duplo_estagio_te_min"
    campo_max = "semi_hermetico_te_max" if linha == "Semi-Hermético" else "duplo_estagio_te_max"
    faixas = {}
    for row in db.query(m.ClassificacaoSistemaCompressor).all():
        if row.motor_compressor is None:
            continue
        te_min, te_max = getattr(row, campo_min), getattr(row, campo_max)
        faixas[row.motor_compressor] = (te_min, te_max) if (te_min is not None and te_max is not None) else None
    return faixas


def _serializar_listar_compressores(db: Session, rack: m.RackParalelo) -> dict:
    _sincronizar_posicoes(db, rack)
    carga_requerida = _carga_por_rack(db, rack)
    folga = rack.folga_tecnica_pct or 0
    te, tc = _te_tc_projeto(rack.sistema)
    percentuais = _percentuais_posicoes(rack)
    projeto = rack.sistema.projeto
    tensao_projeto = projeto.tensao_equipamentos if projeto else None
    return {
        "carga_requerida": carga_requerida, "folga": folga, "te": te, "tc": tc,
        "fabricante_compressor": rack.fabricante_compressor, "linha_compressor": rack.linha_compressor,
        "gas_refrigerante": rack.sistema.gas_refrigerante, "tensao_projeto": tensao_projeto,
        "motor_fixo": rack.filtro_motor_compressor, "n_paralelo": _n_paralelo(rack),
        "posicoes": [{"id": c.id, "posicao": c.posicao, "percentual": percentuais.get(c.posicao, 0)}
                      for c in sorted(rack.compressores, key=lambda x: x.posicao)],
    }


@router.get("/{rack_id}/compressores")
def listar_compressores(rack_id: int, db: Session = Depends(get_db)):
    rack = db.get(m.RackParalelo, rack_id)
    if not rack:
        raise HTTPException(404, "Rack não encontrado")
    dados = _serializar_listar_compressores(db, rack)
    return calcular_compressores_de_dados(db, dados)


@router.put("/{rack_id}/compressores/{posicao}")
def atualizar_posicao(rack_id: int, posicao: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Só percentual_sistema (posição 1) é editável aqui — fabricante/linha/gás/tensão/modelo da
    posição não existem mais como escolha própria: fabricante/linha vêm do cabeçalho do rack, gás e
    tensão do sistema/projeto, e o modelo é escolhido automaticamente (ver listar_compressores)."""
    c = (db.query(m.CompressorRack).filter_by(rack_id=rack_id, posicao=posicao).first())
    if not c:
        raise HTTPException(404, "Posição não encontrada")
    bp.verificar_projeto_da(c.rack)
    bf.verificar_pai_aberto(c.rack)
    if posicao == 1 and "percentual_sistema" in payload:
        c.percentual_sistema = payload["percentual_sistema"]
    db.commit()
    return {"ok": True}


# ---------- Seleção de Condensador Remoto (Fase 2, catálogo da Tela C) ----------

@router.get("/{rack_id}/condensador-opcoes")
def condensador_opcoes(rack_id: int, db: Session = Depends(get_db)):
    """Fabricantes e linhas de condensador disponíveis pro rack, já filtrados pelo Tipo Condensador
    (Plano/V/Onboard) escolhido aqui na Tela 6."""
    rack = db.get(m.RackParalelo, rack_id)
    if not rack:
        raise HTTPException(404, "Rack não encontrado")
    linhas = db.query(m.LinhaCondensadorRemoto).filter(m.LinhaCondensadorRemoto.ativo_comercial.is_(True)).all()
    if rack.tipo_condensador:
        linhas = [l for l in linhas if (l.tipo_estrutura or "") == rack.tipo_condensador]
    por_fabricante = {}
    for l in linhas:
        fab = l.fabricante.nome if l.fabricante else "(sem fabricante)"
        por_fabricante.setdefault(fab, set()).add(l.nome)
    return {
        "fabricantes": sorted(por_fabricante.keys()),
        "linhas_por_fabricante": {k: sorted(v) for k, v in por_fabricante.items()},
    }


def _calcular_opcao_condensador(db, opt, contexto_base, calor_rejeitado, tipo_condensador, tensao_eq):
    """Calcula a seleção de condensador para UMA opção (RackCondensadorSelecao)."""
    if not opt.fabricante_condensador or not opt.linha_condensador:
        return {"aviso": "Escolha Fabricante e Linha.", "selecao": None, "linha_id": None,
                "dt_catalogo_c": None, "filtros_disponiveis": {"fpis": [], "polos_rpm": []}}
    ctx = {**contexto_base, "aleta": "Protegida" if opt.protecao_aletas_condensador else "Padrão"}
    q = (db.query(m.LinhaCondensadorRemoto)
         .join(m.Fabricante, m.LinhaCondensadorRemoto.fabricante_id == m.Fabricante.id)
         .filter(m.Fabricante.nome == opt.fabricante_condensador,
                 m.LinhaCondensadorRemoto.nome == opt.linha_condensador))
    linhas_cond = q.all()
    if tipo_condensador:
        linhas_cond = [l for l in linhas_cond if (l.tipo_estrutura or "") == tipo_condensador]
    linha = max(linhas_cond, key=lambda l: l.id) if linhas_cond else None
    if not linha:
        return {"aviso": "Linha não encontrada no catálogo.", "selecao": None, "linha_id": None,
                "dt_catalogo_c": None, "filtros_disponiveis": {"fpis": [], "polos_rpm": []}}
    modelos = linha.modelos
    polos_ac = sorted({str(int(md.polos_ou_rpm)) for md in modelos
                       if (md.tipo_motor or "").upper() == "AC" and md.polos_ou_rpm not in (None, "")},
                      key=lambda v: int(v))
    tem_ec = any((md.tipo_motor or "").upper() == "EC" for md in modelos)
    filtros_disponiveis = {
        "fpis": sorted({md.fpi for md in modelos if md.fpi is not None}),
        "polos_rpm": (["AC"] if polos_ac else []) + polos_ac + (["EC"] if tem_ec else []),
    }
    fatores_por_tipo = {}
    for f in linha.fatores:
        fatores_por_tipo.setdefault(f.tipo, []).append({"chave": f.chave, "fator": f.fator})
    selecoes_manuais = json.loads(opt.nomenclatura_condensador_selecionada) if opt.nomenclatura_condensador_selecionada else {}
    selecao = cc_calc.selecionar_condensador(
        modelos, fatores_por_tipo, ctx, calor_rejeitado, opt.folga_condensador_pct,
        filtro_fpi=opt.filtro_fpi_condensador, filtro_polos_rpm=opt.filtro_polos_rpm_condensador,
        delta_catalogo=linha.dt_catalogo_c, tensao_equipamentos=tensao_eq,
        quantidade=opt.quantidade_condensadores or 1)
    def _ctx_cand(cand):
        return {
            "tensao_equipamentos": tensao_eq,
            "fpi": str(cand["fpi"]) if cand.get("fpi") is not None else None,
            "tipo_motor": cand.get("tipo_motor"),
            "num_fileiras": str(cand["num_fileiras"]) if cand.get("num_fileiras") is not None else None,
            "qtd_ventiladores": str(cand["qtd_ventiladores"]) if cand.get("qtd_ventiladores") is not None else None,
            "polos_ou_rpm": str(cand["polos_ou_rpm"]) if cand.get("polos_ou_rpm") is not None else None,
        }
    if selecao.get("escolhido"):
        esc = selecao["escolhido"]
        esc["codigo_comercial"] = cpc.montar_codigo(
            db, "CondensadorRemoto", linha.id, modelo_base=esc["modelo"],
            contexto=_ctx_cand(esc), selecoes_manuais=selecoes_manuais)
    for cand in selecao.get("candidatos", []):
        cand["codigo_comercial"] = cpc.montar_codigo(
            db, "CondensadorRemoto", linha.id, modelo_base=cand["modelo"],
            contexto=_ctx_cand(cand), selecoes_manuais=selecoes_manuais)
    return {"selecao": selecao, "linha_id": linha.id, "dt_catalogo_c": linha.dt_catalogo_c,
            "filtros_disponiveis": filtros_disponiveis, "nomenclatura_selecionada": selecoes_manuais}


@router.get("/{rack_id}/condensador")
def selecao_condensador(rack_id: int, db: Session = Depends(get_db)):
    rack = db.get(m.RackParalelo, rack_id)
    if not rack:
        raise HTTPException(404, "Rack não encontrado")
    sistema = rack.sistema
    projeto = sistema.projeto if sistema else None

    calor_rejeitado = resumo_compressores(rack_id, db)["resumo"]["calor_rejeitado_total_kcal_h"]
    n_paralelo = _n_paralelo(rack)
    tensao_eq = projeto.tensao_equipamentos if projeto else None
    contexto_base = {
        "delta_condensacao": sistema.delta_condensacao, "gas": sistema.gas_refrigerante,
        "altitude": projeto.altitude_m if projeto else None,
        "temp_entrada_ar": projeto.temp_ambiente if projeto else None,
    }
    tipo_condensador = rack.tipo_condensador

    base = {
        "fabricante_condensador": rack.fabricante_condensador,
        "linha_condensador": rack.linha_condensador,
        "tipo_condensador": tipo_condensador,
        "filtro_fpi_condensador": rack.filtro_fpi_condensador,
        "filtro_polos_rpm_condensador": rack.filtro_polos_rpm_condensador,
        "folga_condensador_pct": rack.folga_condensador_pct,
        "protecao_aletas_condensador": rack.protecao_aletas_condensador,
        "notas_condensador": rack.notas_condensador,
        "quantidade_paralelo": n_paralelo,
        "quantidade_condensadores_total": (rack.quantidade_condensadores or 1) * n_paralelo,
        "calor_rejeitado_kcal_h": calor_rejeitado,
        "contexto": {**contexto_base, "aleta": "Protegida" if rack.protecao_aletas_condensador else "Padrão"},
        "filtros_disponiveis": {"fpis": [], "polos_rpm": []},
        "selecao": None,
        "tensao_equipamentos": tensao_eq,
    }
    if sistema.delta_condensacao is not None and projeto and projeto.temp_ambiente is not None:
        base["temp_condensacao"] = sistema.delta_condensacao + projeto.temp_ambiente
        base["temp_apos_condensador"] = base["temp_condensacao"] - 3
    else:
        base["temp_condensacao"] = None
        base["temp_apos_condensador"] = None

    _garantir_condensador(db, rack)
    opcoes_resultado = {}
    filtros_merge = {"fpis": set(), "polos_rpm": []}
    for opt in rack.condensadores:
        res = _calcular_opcao_condensador(db, opt, contexto_base, calor_rejeitado, tipo_condensador, tensao_eq)
        opcoes_resultado[str(opt.id)] = res
        if res.get("filtros_disponiveis"):
            filtros_merge["fpis"].update(res["filtros_disponiveis"].get("fpis", []))
            for p in res["filtros_disponiveis"].get("polos_rpm", []):
                if p not in filtros_merge["polos_rpm"]:
                    filtros_merge["polos_rpm"].append(p)
        if opt.considerado:
            base["selecao"] = res.get("selecao")
            base["linha_id"] = res.get("linha_id")
            base["dt_catalogo_c"] = res.get("dt_catalogo_c")
            base["nomenclatura_selecionada"] = res.get("nomenclatura_selecionada")
            if res.get("selecao"):
                base["filtros_disponiveis"] = res["filtros_disponiveis"]
            if res.get("aviso") and not base.get("aviso"):
                base["aviso"] = res["aviso"]
    base["filtros_disponiveis"] = {
        "fpis": sorted(filtros_merge["fpis"]),
        "polos_rpm": filtros_merge["polos_rpm"],
    }
    base["opcoes_resultado"] = opcoes_resultado
    return base


@router.get("/{rack_id}/resumo-compressores")
def resumo_compressores(rack_id: int, db: Session = Depends(get_db)):
    from ..calculos.comum import W_PARA_KCAL_H
    dados = listar_compressores(rack_id, db)
    total_kcal_h = sum((p["resultado"]["capacidade_kcal_h"] if p["resultado"] else 0) for p in dados["posicoes"])
    total_w = sum((p["resultado"]["potencia_w"] if p["resultado"] else 0) for p in dados["posicoes"])
    total_a = sum((p["resultado"]["corrente_a"] if p["resultado"] else 0) for p in dados["posicoes"])
    total_vazao = sum((p["resultado"]["vazao_kg_h"] if p["resultado"] else 0) for p in dados["posicoes"])
    completo = all(p["resultado"] is not None for p in dados["posicoes"]) and bool(dados["posicoes"])
    # Grupos de modelo: agrupa as posições pelo modelo escolhido, na ordem em que aparecem (master
    # primeiro). Como as posições 2..N sempre têm o mesmo percentual entre si (ver
    # _percentuais_posicoes), só existem 2 valores de modelo possíveis no rack inteiro — se o master
    # coincidir com as demais, vira 1 grupo só (nunca duplica quantidade nem mostra tensão aqui).
    grupos_por_modelo = {}
    for p in dados["posicoes"]:
        if not p["modelo"]:
            continue
        g = grupos_por_modelo.setdefault(p["modelo"], {"modelo": p["modelo"], "quantidade": 0,
                                                         "capacidade_unitaria_kcal_h": None})
        g["quantidade"] += 1
        if p["resultado"]:
            g["capacidade_unitaria_kcal_h"] = round(p["resultado"]["capacidade_kcal_h"], 1)
    grupos_modelo = list(grupos_por_modelo.values())

    # Dados físicos (peso, conexões, carga de óleo) — só existem cadastrados pra Bitzer (Tela 6 -
    # Dados Físicos Compressores Bitzer, Configurações). Casa pelo mesmo nome-base usado no filtro
    # de envelope (_normalizar_modelo_polinomio), já que o Polinômio tem sufixo de corrente
    # ("2CES-3Y-20D") que os Dados Físicos não têm ("2CES-3(Y)").
    rack_obj = db.get(m.RackParalelo, rack_id)
    corrente_maxima_total_a = None
    if rack_obj and rack_obj.fabricante_compressor == "Bitzer" and grupos_modelo:
        fisicos_por_base = {re.sub(r"\(Y\)$", "", f.modelo): f
                             for f in db.query(m.DadosFisicosCompressorBitzer).all()}
        soma_max = 0.0
        tem_max = False
        for g in grupos_modelo:
            f = fisicos_por_base.get(_normalizar_modelo_polinomio(g["modelo"]))
            g["peso"] = f.peso if f else None
            g["conexao_succao"] = f.conexao_succao if f else None
            g["conexao_descarga"] = f.conexao_pressao if f else None
            g["carga_oleo"] = f.qtd_enchimento_oleo if f else None
            corrente_max = _extrair_numero(f.corrente_maxima_operacao) if f else None
            g["corrente_maxima_operacao_a"] = corrente_max
            if corrente_max is not None:
                soma_max += corrente_max * g["quantidade"]
                tem_max = True
        corrente_maxima_total_a = round(soma_max, 2) if tem_max else None
    # Calor rejeitado no condensador = balanço de energia do ciclo: capacidade de refrigeração +
    # trabalho absorvido pelo compressor (potência elétrica convertida pra kcal/h) — Qc = Qe + W,
    # relação padrão de termodinâmica de refrigeração pra compressores herméticos/semi-herméticos
    # (perdas do motor ficam dentro da carcaça e são absorvidas pelo fluido — ASHRAE Refrigeration
    # Handbook), não um dado extra do polinômio.
    calor_rejeitado = total_kcal_h + total_w * W_PARA_KCAL_H if completo else None
    cop = round(total_kcal_h / (total_w * W_PARA_KCAL_H), 2) if completo and total_w else None
    folga_real = (round(folga_percentual(total_kcal_h, dados["carga_requerida_kcal_h"]), 1)
                  if completo and dados["carga_requerida_kcal_h"] else None)
    carga_gas_estimada_kg = (_carga_gas_estimada_sistema(db, rack_obj.sistema, rack_obj.tanque_liquido_l)
                              if rack_obj else None)
    return {
        **dados,
        "resumo": {
            # Totais POR RACK (um equipamento). Para o total do sistema, multiplicar por
            # quantidade_paralelo (N racks idênticos em paralelo) — feito nos consumidores (consumo,
            # compilação, composição/BOM).
            "quantidade_paralelo": dados.get("quantidade_paralelo", 1),
            "capacidade_total_kcal_h": round(total_kcal_h, 1),
            "potencia_total_w": round(total_w, 1),
            "corrente_total_a": round(total_a, 2),
            "vazao_total_kg_h": round(total_vazao, 1),
            "calor_rejeitado_total_kcal_h": round(calor_rejeitado, 1) if calor_rejeitado is not None else None,
            "cop": cop,
            "grupos_modelo": grupos_modelo,
            "carga_gas_estimada_kg": carga_gas_estimada_kg,
            "folga_real_pct": folga_real,
            "atende_demanda": completo and total_kcal_h >= dados["demanda_total_kcal_h"],
            "corrente_maxima_total_a": corrente_maxima_total_a,
        },
        "nota": ("As capacidades calculadas pelo polinômio devem ser conferidas no software do "
                 "fabricante antes de qualquer decisão de projeto vinculante — o polinômio tem "
                 "limitação nas condições de superaquecimento e subresfriamento consideradas."),
    }
