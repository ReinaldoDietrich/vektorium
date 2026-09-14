"""Tela 5 — Compilação. Devolve uma lista plana (Sistema, Linha de Sucção, métricas) — o
agrupamento visual (Sistema > Linha de Sucção, subtotais, total geral) é feito no front-end,
mesma lógica já validada no mockup_telas.html."""
import math
import re
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from .. import models as m
from ..database import get_db
from ..calc_service import calcular_camara_completo_seguro as calcular_camara_completo, calcular_camara_simples_seguro as calcular_camara_simples
from ..exportacao.compilacao_export import gerar_excel_compilacao
from ..utils import resposta_excel_projeto
from .expositores import _carga_termica as _carga_expositor, _modulacao, _codigo as _codigo_expositor
from .camaras_completo import _codigo as _codigo_completo
from .camaras_simples import _codigo as _codigo_simples
from . import _bloqueio_projeto as bp

router = APIRouter(prefix="/api", tags=["compilacao"])

# (chave, rótulo, campo no dict de resumo) — usado pra montar a tabela "Resumo de Potência por
# Sistema" (tela + exports) e pra filtrar quais colunas aparecem quando o usuário escolhe um
# subconjunto (item 5 — seleção de colunas). "Sistema" (rótulo da linha) não entra aqui, é fixo.
COLUNAS_RESUMO = [
    ("pot_total_instalada_w", "Pot. Total Instalada (W)", "potencia_total_instalada_w"),
    ("pot_maxima_w", "Pot. Máxima (W)", "potencia_total_w"),
    ("pot_maxima_kva", "Pot. Máxima (kVA)", "potencia_total_kva"),
    ("pot_demandada_w", "Pot. em Operação (W)", "potencia_demandada_w"),
    ("pot_demandada_kva", "Pot. em Operação (kVA)", "potencia_demandada_kva"),
    ("tensao", "Tensão", "tensao"),
    ("cabos", "Cabos", "cabos"),
    ("disjuntor", "Disjuntor Alimentação (Sugerido)", "disjuntor"),
]

# Mesmas chaves/ordem do Quadro de Linhas (exceto "Pot. Total Instalada", que não existe pra
# Compressão/Condensação — não há conceito de exclusão mútua degelo×ventilação aqui) — mantém as
# colunas alinhadas verticalmente entre as duas tabelas quando o usuário filtra cada uma. Rótulos
# levam a sigla da corrente-fonte (MCC/RLA), já que aqui os dois valores vêm direto do catálogo.
COLUNAS_RESUMO_COMPRESSAO = [
    ("pot_maxima_w", "Pot. Máxima - MCC (W)", "potencia_maxima_w"),
    ("pot_maxima_kva", "Pot. Máxima - MCC (kVA)", "potencia_maxima_kva"),
    ("pot_demandada_w", "Pot. em Operação - RLA (W)", "potencia_demandada_w"),
    ("pot_demandada_kva", "Pot. em Operação - RLA (kVA)", "potencia_demandada_kva"),
    ("tensao", "Tensão", "tensao"),
    ("cabos", "Cabos", "cabos"),
    ("disjuntor", "Disjuntor Alimentação (Sugerido)", "disjuntor"),
]


def _natural_key(s):
    """Chave de ordenação natural: 'HTA1A','HTA1B',...,'HTA1J' e '1,2,10' na ordem certa
    (não '1,10,2'). Quebra a string em pedaços de texto/número."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s or "")]


def _voltagem_num(tensao_str):
    if not tensao_str:
        return None
    try:
        return float(tensao_str.upper().split("V")[0].strip())
    except (ValueError, IndexError):
        return None


def _parse_tensao(tensao_str):
    """'380V/3F/60Hz' -> ('380V', '3F', '60Hz') — usado pra montar a coluna Tensão/Cabos do
    resumo de potência. Formato sempre igual (mesmas opções fixas da Tela 1)."""
    if not tensao_str:
        return None, None, None
    partes = tensao_str.split("/")
    volts = partes[0] if len(partes) > 0 else None
    fases = partes[1] if len(partes) > 1 else None
    hz = partes[2] if len(partes) > 2 else None
    return volts, fases, hz


def _coluna_disjuntor(tensao_str):
    """Mapeia a Tensão do projeto ('220V/1F/60Hz' etc.) pra sufixo de coluna da Tabela de
    Disjuntores (Tela 5 - Tabela de Disjuntores, Configurações): '127v_1p' | '220v_1p' |
    '220v_3p' | '380v_3p'. Sem tensão compatível cadastrada -> None (não inventa coluna)."""
    v = _voltagem_num(tensao_str)
    _, fases, _ = _parse_tensao(tensao_str)
    if v == 127:
        return "127v_1p"
    if v == 220:
        return "220v_3p" if fases == "3F" else "220v_1p"
    if v == 380:
        return "380v_3p"
    return None


def _folga_disjuntor_pct(db):
    for chave in ("Folga Corrente Disjuntores", "disjuntor_folga_adotada_corrente_pct"):
        cfg = db.query(m.ConfiguracaoGlobal).filter_by(chave=chave).first()
        if cfg:
            return cfg.valor
    return 5.0


def _disjuntor_comercial(db, corrente_a, tensao_str, tipo="termomagnetico"):
    """Busca o disjuntor comercial (Tela 5 - Tabela de Disjuntores) pra uma corrente calculada:
    aplica a Folga Corrente Disjuntores (Configurações Globais) e pega o menor disjuntor cuja
    Corrente Nominal já cobre isso, na coluna de tensão/fase certa. tipo='termomagnetico' (Ventilação/
    Degelo/alimentação geral) ou 'ddr' (Res. Porta/Res. Dreno — proteção diferencial residual)."""
    if not corrente_a:
        return None
    coluna = _coluna_disjuntor(tensao_str)
    if not coluna:
        return None
    folga_pct = _folga_disjuntor_pct(db)
    corrente_com_folga = corrente_a * (1 + folga_pct / 100)
    Modelo = m.TabelaDisjuntorTermomagnetico if tipo == "termomagnetico" else m.TabelaDisjuntorDDR
    campo = f"desc_proj_{coluna}"
    linha = (db.query(Modelo)
             .filter(Modelo.corrente_nominal_a >= corrente_com_folga)
             .order_by(Modelo.corrente_nominal_a.asc()).first())
    if not linha:
        return None
    return getattr(linha, campo)


def _cabos_str(fases, hz):
    if not fases:
        return "—"
    return f"{fases}+N+PE-{hz}" if hz else f"{fases}+N+PE"


def _config(db, chave, default=None):
    cfg = db.query(m.ConfiguracaoGlobal).filter_by(chave=chave).first()
    return cfg.valor if cfg else default


def _eletrica_dreno_portas(db, camara, v_equip, tem_vao_porta, qtd_forcadores, tipo_degelo):
    """Res. Dreno e Res. Portas só existem se a linha tem alguma resistência de degelo ligada —
    Natural não tem resistência nenhuma; Elétrico e Gás quente têm (a de degelo em si é só do
    Elétrico, tratada à parte em _eletrica_forcador)."""
    if tipo_degelo == "Natural":
        return {"portas_w": None, "portas_a": None, "drenos_w": None, "drenos_a": None}

    pot_dreno_wm = _config(db, "potencia_dreno_wm")
    compr_dreno_m = _config(db, "comprimento_dreno_m")
    drenos_w = round(pot_dreno_wm * compr_dreno_m * qtd_forcadores, 1) if pot_dreno_wm and compr_dreno_m else None
    drenos_a = round(drenos_w / v_equip, 1) if drenos_w and v_equip else None

    portas_w = portas_a = None
    if tem_vao_porta:
        pot_portas_wm = _config(db, "potencia_portas_wm")
        if pot_portas_wm:
            # Completo: portas vêm da tabela-filha camara.portas (os campos escalares num_portas/
            # porta_largura/porta_altura ficaram legados após a migração multi-porta — ver PortaCamara).
            # Simples ainda usa os escalares. Perímetro do vão = 2*(altura+largura) por porta × qtd.
            portas_filhas = getattr(camara, "portas", None)
            perimetro_total = 0.0
            if portas_filhas:
                for p in portas_filhas:
                    if p.altura and p.largura:
                        perimetro_total += (2 * p.altura + 2 * p.largura) * (p.quantidade or 1)
            elif camara.num_portas and camara.porta_altura and camara.porta_largura:
                perimetro_total = (2 * camara.porta_altura + 2 * camara.porta_largura) * camara.num_portas
            if perimetro_total:
                portas_w = round(pot_portas_wm * perimetro_total, 1)
                portas_a = round(portas_w / v_equip, 1) if v_equip else None

    return {"portas_w": portas_w, "portas_a": portas_a, "drenos_w": drenos_w, "drenos_a": drenos_a}


def _rotulo_valvula(valv):
    """Rótulo padrão da válvula (Telas 5 e 8): "Nx MODELO" sem fabricante; termostática inclui o
    orifício zero-padded — ex.: "2x TEN2 orif. 02" (padrão ditado pelo usuário)."""
    if not valv or not valv.get("modelo_selecao"):
        return "—"
    rotulo = f"{valv['quantidade']}x {valv['modelo_selecao']}"
    eh_termostatica = (valv.get("tipo_expansao") or "").lower().startswith("termo")
    orificio = str(valv.get("orificio") or "").strip()
    if eh_termostatica and orificio:
        rotulo += f" orif. {orificio.zfill(2) if orificio.isdigit() else orificio}"
    return rotulo


def _rotulo_valvula_base(valv):
    """Mesmo rótulo de _rotulo_valvula, mas SEM o prefixo "Nx" — usado onde o item de lista de
    materiais precisa ser o modelo puro (ex.: Tela 10), pra não duplicar a mesma válvula em linhas
    diferentes só por causa da quantidade por forçador (ver bug real: Tela 10 agrupava por
    descrição inteira, incluindo o "Nx", fazendo "TEN5 orif. 02" virar 2 itens quando forçadores
    diferentes usavam quantidades diferentes da mesma válvula)."""
    if not valv or not valv.get("modelo_selecao"):
        return "—"
    rotulo = valv["modelo_selecao"]
    eh_termostatica = (valv.get("tipo_expansao") or "").lower().startswith("termo")
    orificio = str(valv.get("orificio") or "").strip()
    if eh_termostatica and orificio:
        rotulo += f" orif. {orificio.zfill(2) if orificio.isdigit() else orificio}"
    return rotulo


def _valvula_considerada_str(calc):
    """Válvula(s) da linha de forçador considerada — coluna 'Válvulas de Expansão' da Tela 5."""
    forc = next((f for f in calc["forcadores"] if f.get("considerado")), None)
    valv = next((v for v in (forc or {}).get("valvulas", []) if v.get("considerado")), None)
    return _rotulo_valvula(valv)


def _eletrica_forcador(camara, calculo, tensao_comando):
    """Ventilação e Degelo (W,A) da linha de forçador 'considerada' (x Quantidade), na tensão de
    comando do projeto. Degelo só é retornado se o Tipo de Degelo escolhido for Elétrico — Natural
    e Gás quente não usam resistência de degelo (gás quente usa o próprio compressor pra isso)."""
    considerado = next((f for f in calculo["forcadores"] if f.get("considerado") and f.get("modelo_resultante")), None)
    tipo_degelo = considerado.get("tipo_degelo_selecionado") if considerado else None
    vazio = {"vent_w": None, "vent_a": None, "degelo_w": None, "degelo_a": None, "quantidade": 1, "tipo_degelo": tipo_degelo}
    if not considerado:
        return vazio
    linha_id = next((row.linha_id for row in camara.forcadores if row.considerado), None)
    modelo_obj = None
    if linha_id:
        linha = next((row.linha for row in camara.forcadores if row.linha_id == linha_id), None)
        if linha:
            modelo_obj = next((md for md in linha.modelos if md.modelo == considerado["modelo_resultante"]), None)
    qtd = considerado.get("quantidade") or 1
    if not modelo_obj:
        return {**vazio, "quantidade": qtd}
    eletrica = next((e for e in modelo_obj.eletricas if e.tensao == tensao_comando), None)
    if not eletrica:
        eletrica = modelo_obj.eletricas[0] if modelo_obj.eletricas else None
    if not eletrica:
        return {**vazio, "quantidade": qtd}
    usa_resistencia_degelo = tipo_degelo == "Elétrico"
    return {"vent_w": round((eletrica.motores_w or 0) * qtd, 1), "vent_a": round((eletrica.motores_a or 0) * qtd, 1),
            "degelo_w": eletrica.degelo_w if usa_resistencia_degelo else None,
            "degelo_a": eletrica.degelo_a if usa_resistencia_degelo else None,
            "quantidade": qtd, "tipo_degelo": tipo_degelo}


def _potencia_sistema(db, sistema, itens_sistema, fator_potencia, tensao_equip_str):
    """Potência Máxima Instalada: em cada linha com degelo Elétrico usa Degelo(W) — nunca junto com
    Ventilação(W), já que são mutuamente exclusivas no tempo (o forçador não roda durante o degelo
    elétrico) e a resistência é sempre maior. Isso já é o "pior caso" (sem diversidade na carga
    resistiva, prática usual pra esse tipo de carga) — número de referência pra disjuntor/cabo. NUNCA
    leva fator manual nenhum, é sempre a soma crua.

    Potência Demandada: estimativa mais realista — só as N linhas de maior Degelo(W) do sistema são
    consideradas em degelo simultâneo (N calculado a partir de Nº de Degelos/Dia × qtd. de linhas
    elétricas, dividido por 24h, arredondado pra cima); as demais linhas (elétricas fora do N e as
    demais) contam Ventilação normal. Essa lógica JÁ é o fator de demanda — não leva multiplicador
    manual em cima.

    kVA (das duas): só conversão de unidade via Fator de Potência, não é fator de demanda."""
    linhas_eletrico = [it for it in itens_sistema if it.get("tipo_degelo_selecionado") == "Elétrico" and it.get("degelo_w")]
    f1 = len(linhas_eletrico)
    qtd_degelo_dia = sistema.quantidade_degelo_dia or 4
    tempo_degelo_min = sistema.tempo_degelo_min or 60
    n_simultaneos = 0
    if f1 > 0 and qtd_degelo_dia > 0:
        total_degelos_dia = qtd_degelo_dia * f1
        n_simultaneos = min(math.ceil(total_degelos_dia / 24), f1)

    maiores_ids = {id(it) for it in sorted(linhas_eletrico, key=lambda it: it["degelo_w"], reverse=True)[:n_simultaneos]}

    potencia_total = 0.0
    potencia_total_bruta = 0.0
    potencia_demandada = 0.0
    corrente_total_a = 0.0
    for it in itens_sistema:
        base = (it.get("portas_w") or 0) + (it.get("drenos_w") or 0) + (it.get("ilum_w") or 0)
        eh_eletrico = it.get("tipo_degelo_selecionado") == "Elétrico" and it.get("degelo_w")
        potencia_total += base + ((it.get("degelo_w") or 0) if eh_eletrico else (it.get("vent_w") or 0))
        # Pot. Total Instalada — soma crua, sem a exclusão mútua ventilação x degelo (referência
        # "se somasse literalmente tudo que está instalado", maior que a Pot. Máxima).
        potencia_total_bruta += base + (it.get("vent_w") or 0) + (it.get("degelo_w") or 0)
        em_degelo_agora = eh_eletrico and id(it) in maiores_ids
        potencia_demandada += base + ((it.get("degelo_w") or 0) if em_degelo_agora else (it.get("vent_w") or 0))
        # Disjuntor geral do Quadro de Linhas — corrente de projeto (IB) do circuito de distribuição
        # = soma direta das correntes dos ramais que ele alimenta (NBR 5410), mesma lógica já usada
        # em "Alimentações Quadros (QD)", nunca a fórmula de potência trifásica equilibrada (P=
        # √3×V×I×cosφ): os ramais são monofásicos e este sistema não sabe em qual fase física
        # (A/B/C) cada um está — sem esse dado, o único valor seguro é o pior caso (tudo numa fase
        # só), que é justamente a soma direta em Amperes, sem nenhuma conversão de tensão.
        corrente_total_a += max(it.get("vent_a") or 0, it.get("degelo_a") or 0) + (it.get("portas_a") or 0) + (it.get("drenos_a") or 0) + (it.get("ilum_a") or 0)

    fp = fator_potencia or 0.92
    volts, fases, hz = _parse_tensao(tensao_equip_str)

    return {
        "sistema_id": sistema.id, "sistema_nome": sistema.nome,
        "quantidade_degelo_dia": qtd_degelo_dia, "tempo_degelo_min": tempo_degelo_min,
        "qtd_linhas_degelo_eletrico": f1, "n_simultaneos": n_simultaneos,
        "potencia_total_instalada_w": round(potencia_total_bruta, 1),
        "potencia_total_w": round(potencia_total, 1),
        "potencia_demandada_w": round(potencia_demandada, 1),
        "potencia_total_kva": round(potencia_total / (fp * 1000), 2) if fp else None,
        "potencia_demandada_kva": round(potencia_demandada / (fp * 1000), 2) if fp else None,
        "tensao": volts or "—", "cabos": _cabos_str(fases, hz),
        "horas_iluminacao_dia": sistema.horas_iluminacao_dia if sistema.horas_iluminacao_dia is not None else 10,
        "corrente_total_a": round(corrente_total_a, 1),
        "disjuntor": _disjuntor_comercial(db, corrente_total_a, tensao_equip_str, "termomagnetico"),
    }


def _potencia_de_corrente(v, i, fases, fp):
    """P(W) = V x I x FP (monofásico) ou √3 x V x I x FP (trifásico) — mesma fórmula usada no
    Consumo Elétrico (Tela 7) para derivar potência a partir da corrente de catálogo."""
    if not (v and i):
        return None
    mult = 3 ** 0.5 if fases == 3 else 1
    return mult * v * i * fp


def _disjuntor_de_potencia(db, p_w, tensao_equip_str, fator_potencia):
    """Disjuntor de alimentação do equipamento (Resumo de Potência — Compressão e Condensação),
    dimensionado pela Potência MÁXIMA já calculada (que pode combinar sub-circuitos em tensões
    diferentes — ex.: compressor + ventilador onboard da UC) — converte de volta pra corrente
    equivalente na Tensão de Equipamentos (a tensão real de alimentação do quadro desse
    equipamento) em vez de somar correntes de tensões distintas, que não seria válido."""
    if not p_w:
        return None
    v_equip = _voltagem_num(tensao_equip_str)
    _, fases_equip, _ = _parse_tensao(tensao_equip_str)
    if not v_equip:
        return None
    fp = fator_potencia or 0.92
    mult = 3 ** 0.5 if fases_equip == "3F" else 1
    corrente_equiv = p_w / (v_equip * fp * mult)
    return _disjuntor_comercial(db, corrente_equiv, tensao_equip_str, "termomagnetico")


def _potencia_compressao_sistema(db, sistema, tensao_equip_str, fator_potencia, itens):
    """Resumo de Potência — Compressão e Condensação: uma linha por sistema, usando MCC (Corrente
    Máx. de Operação) como equivalente à Potência Máxima Instalada e RLA (Corrente nominal) como
    equivalente à Potência Demandada — mesmo par de conceitos já usado no Quadro de Linhas, agora
    aplicado ao compressor/condensador em vez do forçador."""
    fp = fator_potencia or 0.92
    v_equip = _voltagem_num(tensao_equip_str)
    # eletrica.tensao/rack.tensao são texto simples (ex.: "380V"), sem o sufixo "/3F/60Hz" do
    # padrão usado em tensao_equip_str — não dá pra reaproveitar _parse_tensao neles. Fases vem de
    # cada catálogo (UC) ou é sempre trifásico (Rack); Hz cai pro Hz do projeto (não há campo próprio).
    _, _, hz_projeto = _parse_tensao(tensao_equip_str)

    if sistema.tipo_compressao == "4.1.2":  # Rack Paralelo
        rack = sistema.rack_paralelo
        if not rack:
            return {"sistema_id": sistema.id, "sistema_nome": sistema.nome,
                    "equipamento": "Rack Paralelo + Condensador Remoto — sem dados lançados (Tela 6)",
                    "potencia_maxima_w": None, "potencia_demandada_w": None,
                    "potencia_maxima_kva": None, "potencia_demandada_kva": None, "tensao": "—", "cabos": "—"}
        v = _voltagem_num(rack.tensao) or v_equip
        # Potência Demandada = potência REAL do rack (compressores, Tela 6, resumo_compressores) +
        # ventiladores do Condensador Remoto selecionado (Tela 6) — mesma fonte já usada no cálculo
        # de Consumo Elétrico (Tela D), nunca era puxada aqui (corrente_nominal_a é campo morto,
        # nunca preenchido em lugar nenhum do app). Potência Máxima Instalada usa a soma da Corrente
        # Máxima de Operação por modelo (Dados Físicos Compressores Bitzer, Configurações) — só
        # existe pra Bitzer e só pros modelos já preenchidos naquela tabela; sem isso (Copeland, ou
        # Bitzer sem o dado ainda cadastrado), cai pro campo manual corrente_maxima_trabalho_a.
        from .rack_paralelo import _modelo_comercial_rack, resumo_compressores
        from ..consumo.calculo_consumo import _dados_ventiladores_condensador
        dados_resumo = resumo_compressores(rack.id, db)
        posicoes = dados_resumo["posicoes"]
        completo = bool(posicoes) and all(p["resultado"] is not None for p in posicoes)
        p_comp_w = dados_resumo["resumo"]["potencia_total_w"] if completo else None
        p_vent_kw, _tipo_motor_vent, _fator_carga_vent = _dados_ventiladores_condensador(db, rack, v_equip)
        p_demand = None
        if p_comp_w is not None or p_vent_kw is not None:
            p_demand = (p_comp_w or 0) + (p_vent_kw or 0) * 1000
        corrente_max_catalogo = dados_resumo["resumo"].get("corrente_maxima_total_a")
        corrente_max = corrente_max_catalogo if corrente_max_catalogo is not None else rack.corrente_maxima_trabalho_a
        p_max = _potencia_de_corrente(v, corrente_max, 3, fp)
        modelo_comercial = _modelo_comercial_rack(rack, sistema)
        modelo = f" — {modelo_comercial}" if modelo_comercial else ""
        # N racks idênticos em paralelo: potência/kVA do sistema = por-rack × N; o disjuntor é
        # dimensionado por UM rack (N disjuntores idênticos, um por equipamento — aprovado 2026-08-13).
        n_par = max(rack.quantidade_paralelo or 1, 1)
        prefixo = f"{n_par}x " if n_par > 1 else ""
        p_max_sys = p_max * n_par if p_max else None
        p_demand_sys = p_demand * n_par if p_demand else None
        return {
            "sistema_id": sistema.id, "sistema_nome": sistema.nome,
            "equipamento": f"{prefixo}Rack Paralelo{modelo} + Condensador Remoto",
            "quantidade_paralelo": n_par,
            "potencia_maxima_w": round(p_max_sys, 1) if p_max_sys else None,
            "potencia_demandada_w": round(p_demand_sys, 1) if p_demand_sys else None,
            "potencia_maxima_kva": round(p_max_sys / (fp * 1000), 2) if p_max_sys else None,
            "potencia_demandada_kva": round(p_demand_sys / (fp * 1000), 2) if p_demand_sys else None,
            "tensao": rack.tensao or v_equip and f"{v_equip:g}V" or "—",
            "cabos": _cabos_str("3F", hz_projeto),
            "disjuntor": _disjuntor_de_potencia(db, p_max, tensao_equip_str, fp),
        }

    # Unidade Condensadora Comercial — reaproveita a seleção já considerada na Tela 1. Passa os
    # itens já computados (em vez de deixar obter_selecao recalcular do zero) para não cair em
    # recursão infinita — obter_selecao chama de volta _montar_itens_compilacao quando não recebe
    # itens prontos.
    from .unidades_condensadoras import obter_selecao, _eletrica_da_tensao
    resp = obter_selecao(sistema.id, db, itens_precomputados=itens)
    escolhida = next((s for s in resp["selecoes"] if s.get("considerado") and s.get("unidade_id")), None)
    if not escolhida:
        return {"sistema_id": sistema.id, "sistema_nome": sistema.nome,
                "equipamento": "Unidade Condensadora Comercial — nenhuma selecionada (Tela 1)",
                "potencia_maxima_w": None, "potencia_demandada_w": None,
                "potencia_maxima_kva": None, "potencia_demandada_kva": None, "tensao": "—", "cabos": "—"}
    uc = db.get(m.UnidadeCondensadora, escolhida["unidade_id"])
    eletrica = _eletrica_da_tensao(uc, tensao_equip_str)
    v = _voltagem_num(eletrica.tensao) if eletrica else v_equip
    fases = eletrica.fases if eletrica else 3
    # MCC/RLA no catálogo já são a corrente de TODOS os compressores da unidade somada (não por
    # compressor individual) — confirmado pelo usuário; não multiplicar por numero_compressores.
    p_max_comp = _potencia_de_corrente(v, eletrica.mcc_a if eletrica else None, fases, fp)
    p_demand_comp = _potencia_de_corrente(v, eletrica.rla_a if eletrica else None, fases, fp)
    # Condensador onboard — ventiladores, mesma corrente nas duas colunas (não tem "pico" separado).
    v_vent = _voltagem_num(eletrica.vent_tensao) if (eletrica and eletrica.vent_tensao) else v
    fases_vent = eletrica.vent_fases if (eletrica and eletrica.vent_fases) else 1
    p_vent = _potencia_de_corrente(v_vent, eletrica.vent_corrente_a if eletrica else None, fases_vent, fp)
    p_max = (p_max_comp or 0) + (p_vent or 0) if (p_max_comp or p_vent) else None
    p_demand = (p_demand_comp or 0) + (p_vent or 0) if (p_demand_comp or p_vent) else None
    fases_str = f"{fases}F" if (eletrica and fases) else None
    hz = eletrica.frequencia if (eletrica and eletrica.frequencia) else hz_projeto
    # N UCs idênticas em paralelo: potência/kVA do sistema = por-unidade × N; disjuntor por UMA
    # unidade (N disjuntores idênticos, um por equipamento — aprovado 2026-08-13).
    n_par = max(escolhida.get("quantidade_paralelo", 1) or 1, 1)
    prefixo = f"{n_par}x " if n_par > 1 else ""
    p_max_sys = p_max * n_par if p_max else None
    p_demand_sys = p_demand * n_par if p_demand else None
    return {
        "sistema_id": sistema.id, "sistema_nome": sistema.nome,
        # Nomenclatura comercial (código de compra), não o código técnico interno — mesmo valor
        # já exibido na Tela 1 e na Compilação Geral (Tela 9).
        "equipamento": f"{prefixo}Unidade Condensadora Comercial — {escolhida.get('codigo_comercial') or uc.modelo}",
        "quantidade_paralelo": n_par,
        "potencia_maxima_w": round(p_max_sys, 1) if p_max_sys else None,
        "potencia_demandada_w": round(p_demand_sys, 1) if p_demand_sys else None,
        "potencia_maxima_kva": round(p_max_sys / (fp * 1000), 2) if p_max_sys else None,
        "potencia_demandada_kva": round(p_demand_sys / (fp * 1000), 2) if p_demand_sys else None,
        "tensao": eletrica.tensao if eletrica else "—",
        "cabos": _cabos_str(fases_str, hz),
        "disjuntor": _disjuntor_de_potencia(db, p_max, tensao_equip_str, fp),
    }


def _observacao_padrao(resumo_sistemas, fator_potencia):
    linhas_degelo = []
    for r in resumo_sistemas:
        if r["qtd_linhas_degelo_eletrico"] > 0:
            if r["qtd_linhas_degelo_eletrico"] == 1:
                # Com 1 linha só, não há "simultaneidade" — é só a própria linha, sem outra pra
                # comparar. Evita a frase confusa "1 degelo elétrico simultâneo considerado".
                frase_n = "única linha com degelo elétrico do sistema, sem simultaneidade a considerar"
            else:
                frase_n = f"{r['n_simultaneos']} degelo(s) elétrico(s) simultâneo(s) considerado(s) entre as {r['qtd_linhas_degelo_eletrico']} linhas do sistema"
            linhas_degelo.append(
                f"Sistema {r['sistema_nome']}: {r['quantidade_degelo_dia']:g} degelo(s)/dia, "
                f"{r['tempo_degelo_min']:g}min/ciclo, {frase_n}.")
    item2 = ("Quantidade e tempo de degelo considerados — " + " ".join(linhas_degelo)
              if linhas_degelo else "Quantidade e tempo de degelo: não há linhas com degelo elétrico neste projeto.")
    item4 = (("Os controladores de degelo de cada sistema devem ser parametrizados para nunca exceder "
              "o número de degelos simultâneos considerado acima — caso o agendamento real de degelos "
              "fique desbalanceado, os valores de Potência Demandada apresentados não corresponderão "
              "à potência efetivamente medida em campo.")
             if linhas_degelo else "Não há linhas com degelo elétrico neste projeto.")
    return (
        "1) Iluminação: a carga elétrica de iluminação de cada câmara é estimada — Câmara Completo a "
        "partir do cálculo de carga térmica (qtd./potência de luminárias); Câmara Simples a partir de "
        "referências de W/m², lm/m² e potência de lâmpada (Configurações). Desligável por projeto "
        "('Considerar Iluminação Ambiente', Tela 1) — não afeta Expositor, sempre considerado.\n"
        f"2) {item2}\n"
        "3) Potência Máxima Instalada: soma sem fator de diversidade nas cargas resistivas de degelo "
        "(prática usual para esse tipo de carga), considerando a carga de degelo no lugar da carga de "
        "ventilação nas linhas com degelo elétrico (mutuamente exclusivas no tempo).\n"
        f"4) Potência Demandada: estimativa considerando degelos elétricos simultâneos por sistema, "
        f"calculada a partir da frequência/duração de degelo configuradas. {item4}\n"
        "5) Este é um cálculo estimado para fins de referência de projeto — os valores finais de "
        "disjuntores, cabos e demanda contratada devem ser conferidos e assumidos por engenheiro "
        "eletricista responsável antes da execução da obra.\n"
        f"6) Fator de Potência considerado para a conversão de W para kVA: {fator_potencia:g} (valor "
        "típico assumido para carga mista resistiva/motor — ajustável, conferir com o fabricante dos "
        "equipamentos selecionados)."
    )


def _disjuntores_gerais(db, projeto, resumo_sistemas, resumo_compressao, potencia_maxima_compressao_w, fator_potencia):
    """Disjuntor geral (Alimentação Geral) de cada resumo — Quadro de Linhas usa a soma direta de
    correntes (IB do circuito de distribuição, NBR 5410, ver _potencia_sistema); Compressão/
    Condensação usa a soma de potência (equipamentos trifásicos balanceados, ver
    _potencia_compressao_sistema) — reaproveitado pela tela (GET) e pela exportação Excel."""
    fp = fator_potencia or 0.92
    fonte_quadro = projeto.quadro_linhas_tensao_fonte if projeto else "equipamentos"
    tensao_quadro_linhas = (projeto.tensao_comando if fonte_quadro == "comando" else projeto.tensao_equipamentos) if projeto else None
    tensao_equip = projeto.tensao_equipamentos if projeto else None
    corrente_total_quadro_linhas = sum(r.get("corrente_total_a") or 0 for r in resumo_sistemas)
    return (_disjuntor_comercial(db, corrente_total_quadro_linhas, tensao_quadro_linhas, "termomagnetico"),
            _disjuntor_de_potencia(db, potencia_maxima_compressao_w, tensao_equip, fp))


@router.get("/compilacao")
def compilacao(projeto_id: int, fator_potencia: float = 0.92, db: Session = Depends(get_db)):
    _projeto, _sistemas, itens, resumo_sistemas, resumo_compressao, observacao, eh_qd = _montar_itens_compilacao(db, projeto_id, fator_potencia)
    potencia_total_w = round(sum(r["potencia_total_w"] for r in resumo_sistemas), 1)
    potencia_demandada_w = round(sum(r["potencia_demandada_w"] for r in resumo_sistemas), 1)
    potencia_maxima_compressao_w = round(sum((r["potencia_maxima_w"] or 0) for r in resumo_compressao), 1)
    potencia_demandada_compressao_w = round(sum((r["potencia_demandada_w"] or 0) for r in resumo_compressao), 1)
    fp = fator_potencia or 0.92
    disjuntor_geral_quadro_linhas, disjuntor_geral_compressao = _disjuntores_gerais(
        db, _projeto, resumo_sistemas, resumo_compressao, potencia_maxima_compressao_w, fator_potencia)
    return {"itens": itens, "resumo_sistemas": resumo_sistemas, "resumo_compressao": resumo_compressao,
            "potencia_total_w": potencia_total_w,
            "potencia_demandada_w": potencia_demandada_w,
            "potencia_maxima_compressao_w": potencia_maxima_compressao_w,
            "potencia_demandada_compressao_w": potencia_demandada_compressao_w,
            "disjuntor_geral_quadro_linhas": disjuntor_geral_quadro_linhas,
            "disjuntor_geral_compressao": disjuntor_geral_compressao,
            "potencia_geral_maxima_w": round(potencia_total_w + potencia_maxima_compressao_w, 1),
            "potencia_geral_maxima_kva": round((potencia_total_w + potencia_maxima_compressao_w) / (fp * 1000), 2),
            "potencia_geral_demandada_w": round(potencia_demandada_w + potencia_demandada_compressao_w, 1),
            "potencia_geral_demandada_kva": round((potencia_demandada_w + potencia_demandada_compressao_w) / (fp * 1000), 2),
            "observacao": observacao,
            "eh_qd": eh_qd,
            "observacao_customizada": _projeto.observacao_compilacao_eletrica is not None,
            "quadro_linhas_tensao_fonte": _projeto.quadro_linhas_tensao_fonte or "equipamentos",
            "tensao_comando": _projeto.tensao_comando or "—",
            "colunas_resumo": [{"chave": c[0], "rotulo": c[1], "campo": c[2]} for c in COLUNAS_RESUMO],
            "colunas_resumo_compressao": [{"chave": c[0], "rotulo": c[1], "campo": c[2]} for c in COLUNAS_RESUMO_COMPRESSAO]}


@router.put("/compilacao/observacao")
def salvar_observacao(projeto_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_da(projeto)
    projeto.observacao_compilacao_eletrica = payload.get("texto") or None
    db.commit()
    return {"ok": True}


@router.delete("/compilacao/observacao")
def restaurar_observacao(projeto_id: int, db: Session = Depends(get_db)):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    bp.verificar_projeto_da(projeto)
    projeto.observacao_compilacao_eletrica = None
    db.commit()
    return {"ok": True}


def _montar_itens_compilacao(db: Session, projeto_id: int, fator_potencia: float = 0.92):
    sistemas = sorted(db.query(m.SistemaRefrigeracao).filter_by(projeto_id=projeto_id)
                      .options(selectinload(m.SistemaRefrigeracao.camaras_completo).selectinload(m.CamaraCompleto.forcadores),
                               selectinload(m.SistemaRefrigeracao.camaras_completo).selectinload(m.CamaraCompleto.portas),
                               selectinload(m.SistemaRefrigeracao.camaras_simples).selectinload(m.CamaraSimples.forcadores),
                               selectinload(m.SistemaRefrigeracao.expositores).selectinload(m.Expositor.modelo_expositor),
                               selectinload(m.SistemaRefrigeracao.expositores).selectinload(m.Expositor.setor),
                               selectinload(m.SistemaRefrigeracao.racks))
                      .all(), key=lambda s: _natural_key(s.nome))
    projeto = db.get(m.Projeto, projeto_id)
    tensao_comando = projeto.tensao_comando if projeto else None
    tensao_equip = projeto.tensao_equipamentos if projeto else None
    v_equip = _voltagem_num(tensao_equip)
    v_comando = _voltagem_num(tensao_comando)
    # "Quadro de Linhas" (coluna Tensão/Cabos do Resumo de Potência por Sistema) — fonte escolhida
    # pelo projetista ELÉTRICO (Tela 5), não fixa em tensão de equipamentos. Não afeta a regra fixa
    # do forçador (Ventilação/Degelo por linha, que continua usando tensao_comando pra achar a linha
    # elétrica certa no catálogo) nem o Resumo de Compressão/Condensação (tensão de equipamentos).
    fonte_quadro = projeto.quadro_linhas_tensao_fonte if projeto else "equipamentos"
    tensao_quadro_linhas = tensao_comando if fonte_quadro == "comando" else tensao_equip
    # Iluminação AMBIENTE (Completo/Simples) — nunca afeta Expositor, que é obrigatória (embutida
    # na carga elétrica própria do equipamento).
    considerar_ilum = projeto.considerar_iluminacao_ambiente if (projeto and projeto.considerar_iluminacao_ambiente is not None) else True

    itens = []
    for s in sistemas:
        for c in s.camaras_completo:
            calc = calcular_camara_completo(db, c)
            eletrica = _eletrica_forcador(c, calc, tensao_comando)
            dreno_porta = _eletrica_dreno_portas(db, c, v_equip, tem_vao_porta=True,
                                                  qtd_forcadores=eletrica["quantidade"], tipo_degelo=eletrica["tipo_degelo"])
            # None (não 0) quando iluminação não é considerada — mesmo padrão de "—" das demais
            # colunas elétricas (Portas/Drenos/Degelo) quando não se aplica.
            ilum_w = calc.get("potencia_total_iluminacao_w") if considerar_ilum else None
            itens.append({
                "metodo": "completo", "sistema_id": s.id, "sistema_nome": s.nome,
                "temp_evaporacao": s.temp_evaporacao, "gas_refrigerante": s.gas_refrigerante,
                "linha_succao": c.linha_succao, "codigo": _codigo_completo(c), "nome": c.nome,
                "modulacao_area": f"{round((c.largura or 0) * (c.comprimento or 0), 2):g}m²",
                "carga_termica": calc["capacidade_requerida"],
                "forcadores": next((f"{f.get('quantidade', 1)}x {f['fabricante']} {f['modelo_resultante']}"
                                     for f in calc["forcadores"] if f.get("considerado") and f.get("modelo_resultante")), "—"),
                "delta_t": f"{calc['dt_camara']:.0f}°C" if calc.get("dt_camara") is not None else "—",
                "folga_real": next((f"{f['folga_real']}%" for f in calc["forcadores"] if f.get("considerado") and f.get("folga_real") is not None), "—"),
                "vazao_ar": next((f"{(f.get('vazao_ar_m3h') or 0) * f.get('quantidade', 1):g}m³/h" for f in calc["forcadores"] if f.get("considerado")), "—"),
                "trocas_ar": next((f"{f['trocas_de_ar']}/h" for f in calc["forcadores"] if f.get("considerado") and f.get("trocas_de_ar") is not None), "—"),
                "valvulas": _valvula_considerada_str(calc),
                "vent_w": eletrica["vent_w"], "vent_a": eletrica["vent_a"],
                "portas_w": dreno_porta["portas_w"], "portas_a": dreno_porta["portas_a"],
                "drenos_w": dreno_porta["drenos_w"], "drenos_a": dreno_porta["drenos_a"],
                "degelo_w": eletrica["degelo_w"], "degelo_a": eletrica["degelo_a"],
                "ilum_w": ilum_w, "ilum_a": round(ilum_w / v_equip, 1) if (ilum_w is not None and v_equip) else None,
                "tipo_degelo_selecionado": eletrica["tipo_degelo"],
            })
        for c in s.camaras_simples:
            calc = calcular_camara_simples(db, c)
            eletrica = _eletrica_forcador(c, calc, tensao_comando)
            dreno_porta = _eletrica_dreno_portas(db, c, v_equip, tem_vao_porta=True,
                                                  qtd_forcadores=eletrica["quantidade"], tipo_degelo=eletrica["tipo_degelo"])
            ilum_w_simples = calc.get("potencia_ilum_w") if considerar_ilum else None
            itens.append({
                "metodo": "simplificado", "sistema_id": s.id, "sistema_nome": s.nome,
                "temp_evaporacao": s.temp_evaporacao, "gas_refrigerante": s.gas_refrigerante,
                "linha_succao": c.linha_succao, "codigo": _codigo_simples(c), "nome": c.nome,
                "modulacao_area": f"{round(c.area or 0, 2):g}m²",
                "carga_termica": calc["capacidade_requerida"],
                "forcadores": next((f"{f.get('quantidade', 1)}x {f['fabricante']} {f['modelo_resultante']}"
                                     for f in calc["forcadores"] if f.get("considerado") and f.get("modelo_resultante")), "—"),
                "delta_t": f"{calc['dt_camara']:.0f}°C" if calc.get("dt_camara") is not None else "—",
                "folga_real": next((f"{f['folga_real']}%" for f in calc["forcadores"] if f.get("considerado") and f.get("folga_real") is not None), "—"),
                "vazao_ar": next((f"{(f.get('vazao_ar_m3h') or 0) * f.get('quantidade', 1):g}m³/h" for f in calc["forcadores"] if f.get("considerado")), "—"),
                "trocas_ar": next((f"{f['trocas_de_ar']}/h" for f in calc["forcadores"] if f.get("considerado") and f.get("trocas_de_ar") is not None), "—"),
                "valvulas": _valvula_considerada_str(calc),
                "vent_w": eletrica["vent_w"], "vent_a": eletrica["vent_a"],
                "portas_w": dreno_porta["portas_w"], "portas_a": dreno_porta["portas_a"],
                "drenos_w": dreno_porta["drenos_w"], "drenos_a": dreno_porta["drenos_a"],
                "degelo_w": eletrica["degelo_w"], "degelo_a": eletrica["degelo_a"],
                "ilum_w": ilum_w_simples, "ilum_a": round(ilum_w_simples / v_equip, 1) if (ilum_w_simples is not None and v_equip) else None,
                "tipo_degelo_selecionado": eletrica["tipo_degelo"],
            })
        for e in s.expositores:
            carga = _carga_expositor(e)
            vent_w_expositor = e.modelo_expositor.carga_eletrica_w if e.modelo_expositor else None
            itens.append({
                "metodo": "expositor", "sistema_id": s.id, "sistema_nome": s.nome,
                "temp_evaporacao": s.temp_evaporacao, "gas_refrigerante": s.gas_refrigerante,
                "linha_succao": e.linha_succao, "codigo": _codigo_expositor(e),
                "nome": e.modelo_expositor.nome if e.modelo_expositor else (e.nome or "—"),
                "setor": e.setor.nome if e.setor else "—",
                "modulacao_area": _modulacao(e), "carga_termica": carga or 0,
                "forcadores": "—", "delta_t": "—", "folga_real": "—", "vazao_ar": "—", "trocas_ar": "—", "valvulas": "—",
                "vent_w": vent_w_expositor,
                "vent_a": round(vent_w_expositor / v_comando, 1) if (vent_w_expositor and v_comando) else None,
                "portas_w": None, "portas_a": None, "drenos_w": None, "drenos_a": None,
                "degelo_w": None, "degelo_a": None, "ilum_w": None, "ilum_a": None,
                "tipo_degelo_selecionado": None,
            })

    # Disjuntores por circuito (Tela 5 - Tabela de Disjuntores, Configurações) — Ventilação/Degelo
    # usam a tabela Termomagnético, Res. Porta/Res. Dreno/Iluminação usam DDR (proteção diferencial
    # residual — mesma utilização cadastrada na tabela real); todos na Tensão de Comando, mesma
    # fonte já usada pra achar a linha elétrica do forçador (ver acima). "Alimentação Quadro" só
    # existe se o projeto for QD (Quadro Distribuído) — QL já tem o disjuntor geral no Resumo de
    # Potência (Quadro de Linhas).
    eh_qd = bool(projeto and projeto.tipo_comando == "1.1.1")  # Quadro Distribuído (QD)
    for it in itens:
        it["disjuntor_ventilacao"] = _disjuntor_comercial(db, it.get("vent_a"), tensao_comando, "termomagnetico")
        it["disjuntor_degelo"] = _disjuntor_comercial(db, it.get("degelo_a"), tensao_comando, "termomagnetico")
        it["disjuntor_res_porta"] = _disjuntor_comercial(db, it.get("portas_a"), tensao_comando, "ddr")
        it["disjuntor_res_dreno"] = _disjuntor_comercial(db, it.get("drenos_a"), tensao_comando, "ddr")
        it["disjuntor_iluminacao"] = _disjuntor_comercial(db, it.get("ilum_a"), tensao_comando, "ddr")
        if eh_qd:
            maior_vent_degelo = max(it.get("vent_a") or 0, it.get("degelo_a") or 0)
            alimentacao_a = maior_vent_degelo + (it.get("portas_a") or 0) + (it.get("drenos_a") or 0) + (it.get("ilum_a") or 0)
            it["alimentacao_quadro_a"] = round(alimentacao_a, 1) if alimentacao_a else None
            it["disjuntor_alimentacao_quadro"] = _disjuntor_comercial(db, alimentacao_a, tensao_comando, "termomagnetico")

    # Ordena a compilação pelo código da câmara (HTA1A, HTA1B, HTA1C...) — ordenação natural para
    # "1, 2, 10" não virar "1, 10, 2". Vale para a tela e para os exports (Excel/PDF), que usam
    # esta mesma lista.
    itens.sort(key=lambda it: (_natural_key(it["sistema_nome"]), _natural_key(it["codigo"])))

    resumo_sistemas = [_potencia_sistema(db, s, [it for it in itens if it["sistema_id"] == s.id], fator_potencia, tensao_quadro_linhas)
                        for s in sistemas]
    resumo_compressao = [_potencia_compressao_sistema(db, s, tensao_equip, fator_potencia, itens) for s in sistemas]
    observacao = projeto.observacao_compilacao_eletrica if (projeto and projeto.observacao_compilacao_eletrica) else _observacao_padrao(resumo_sistemas, fator_potencia)
    return projeto, sistemas, itens, resumo_sistemas, resumo_compressao, observacao, eh_qd


def _colunas_selecionadas_generico(colunas, todas):
    if not colunas:
        return todas
    chaves = set(colunas.split(","))
    return [c for c in todas if c[0] in chaves]


def _colunas_resumo_selecionadas(colunas: str = None):
    return _colunas_selecionadas_generico(colunas, COLUNAS_RESUMO)


def _colunas_resumo_compressao_selecionadas(colunas: str = None):
    return _colunas_selecionadas_generico(colunas, COLUNAS_RESUMO_COMPRESSAO)


def _totais_gerais(resumo_sistemas, resumo_compressao, fator_potencia):
    fp = fator_potencia or 0.92
    potencia_total_w = sum(r["potencia_total_w"] for r in resumo_sistemas)
    potencia_demandada_w = sum(r["potencia_demandada_w"] for r in resumo_sistemas)
    potencia_maxima_compressao_w = sum((r["potencia_maxima_w"] or 0) for r in resumo_compressao)
    potencia_demandada_compressao_w = sum((r["potencia_demandada_w"] or 0) for r in resumo_compressao)
    return {
        "potencia_geral_maxima_w": round(potencia_total_w + potencia_maxima_compressao_w, 1),
        "potencia_geral_maxima_kva": round((potencia_total_w + potencia_maxima_compressao_w) / (fp * 1000), 2),
        "potencia_geral_demandada_w": round(potencia_demandada_w + potencia_demandada_compressao_w, 1),
        "potencia_geral_demandada_kva": round((potencia_demandada_w + potencia_demandada_compressao_w) / (fp * 1000), 2),
    }


@router.get("/compilacao/exportar/excel")
def exportar_compilacao_excel(projeto_id: int, fator_potencia: float = 0.92, colunas: str = None,
                               colunas_compressao: str = None, db: Session = Depends(get_db)):
    projeto, sistemas, itens, resumo_sistemas, resumo_compressao, observacao, eh_qd = _montar_itens_compilacao(db, projeto_id, fator_potencia)
    totais_gerais = _totais_gerais(resumo_sistemas, resumo_compressao, fator_potencia)
    potencia_maxima_compressao_w = sum((r.get("potencia_maxima_w") or 0) for r in resumo_compressao)
    disjuntor_geral_quadro_linhas, disjuntor_geral_compressao = _disjuntores_gerais(
        db, projeto, resumo_sistemas, resumo_compressao, potencia_maxima_compressao_w, fator_potencia)
    conteudo = gerar_excel_compilacao(projeto, sistemas, itens, resumo_sistemas, observacao,
                                       _colunas_resumo_selecionadas(colunas), resumo_compressao,
                                       _colunas_resumo_compressao_selecionadas(colunas_compressao), totais_gerais,
                                       eh_qd, disjuntor_geral_quadro_linhas, disjuntor_geral_compressao)
    return resposta_excel_projeto(conteudo, f"compilacao_{projeto.codigo_projeto or projeto_id}.xlsx", projeto)


@router.get("/compilacao/status-fechada")
def status_fechada(projeto_id: int, db: Session = Depends(get_db)):
    """Retorna entidades abertas (fechada=False) para o banner de aviso na Tela 5/12."""
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404)
    abertas = []
    secoes = [("Dados Gerais", projeto.fechada_dados_gerais),
              ("Clima", projeto.fechada_clima),
              ("Estrutural", projeto.fechada_estrutural)]
    for nome, fechada in secoes:
        if not fechada:
            abertas.append({"tipo": "secao_projeto", "nome": nome})
    modelos = [
        (m.SistemaRefrigeracao, "Sistema"),
        (m.CamaraCompleto, "Câmara Completa"),
        (m.CamaraSimples, "Câmara Simples"),
        (m.Expositor, "Expositor"),
        (m.RackParalelo, "Rack Paralelo"),
        (m.PainelTermico, "Painel Térmico"),
        (m.PortaFrigorifica, "Porta Frigorífica"),
    ]
    for modelo, rotulo in modelos:
        for ent in db.query(modelo).filter_by(projeto_id=projeto_id).all():
            if not getattr(ent, "fechada", True):
                nome = getattr(ent, "nome", None) or getattr(ent, "descricao", None) or str(ent.id)
                abertas.append({"tipo": rotulo, "nome": nome, "id": ent.id})
    uc_model = m.UnidadeCondensadoraSelecao
    for uc in db.query(uc_model).join(m.SistemaRefrigeracao).filter(m.SistemaRefrigeracao.projeto_id == projeto_id).all():
        if not getattr(uc, "fechada", True):
            abertas.append({"tipo": "UC Seleção", "nome": str(uc.id), "id": uc.id})
    return {"abertas": abertas, "total_abertas": len(abertas)}
