# -*- coding: utf-8 -*-
"""Tela E — Painéis Térmicos e Portas. Motor de cálculo: área/qtd. de placas/Id. de painel, Id. de
porta (PRC/PFE/PIS/PVV/PSC/SL) e os 4 modos de resumo. Réplica fiel da planilha "Tabela
Quantificação Painéis e Portas.xlsx" (fórmulas das colunas J/K/L de Painéis e B/O de Portas),
com a correção de Modelo (Correr/Embutir, cada um com prefixo próprio) combinada com o usuário."""
import math
import re
from . import models as m
from .utils import model_to_dict


def _camara_de(item):
    return item.camara_completo or item.camara_simples


def _grupo_de(item):
    """Resolve (id_planta, camara_nome, chave_grupo) pra um painel/porta. Câmara real: id_planta =
    código da câmara, chave_grupo = o mesmo. Ambiente Não Climatizado: sem Id. Planta (None), mas
    cada nome distinto vira seu próprio grupo nos resumos (chave_grupo prefixada p/ não colidir com
    id_planta de câmara real nem com outro ambiente do mesmo nome porém digitado diferente)."""
    camara = _camara_de(item)
    if camara:
        codigo = _codigo_camara(camara)
        return codigo, camara.nome, codigo
    nome = getattr(item, "ambiente_nao_climatizado_nome", None)
    if nome:
        return None, nome, f"AMB::{nome}"
    return None, None, "—"


def _codigo_camara(camara):
    """Mesma lógica de _codigo() em camaras_completo.py/camaras_simples.py — reaproveitada aqui
    pro Id. Planta (col B): prefixo do sistema + linha de sucção + linha elétrica."""
    if not camara:
        return None
    sistema = getattr(camara, "sistema", None)
    prefixo = (sistema.nome[:3].upper() if sistema and sistema.nome else "???")
    return f"{prefixo}{camara.linha_succao or '?'}{camara.linha_eletrica or '?'}"


def _volume_camara(camara):
    if camara is None:
        return None
    if isinstance(camara, m.CamaraCompleto):
        return (camara.largura or 0) * (camara.comprimento or 0) * (camara.pedireito or 0)
    return (camara.area or 0) * (camara.pedireito or 0)


def _piso_dupla_camada(espessura):
    """Opções de espessura de piso "(N + N mm)" precisam de 2 placas físicas por posição (área
    considerada dobra) — "(Placa única)" não. Ver fórmula original da coluna L (Área Considerada)."""
    if not espessura:
        return False
    return "+" in espessura and "única" not in espessura


def _proximo_sufixo(sufixos, id_painel_base):
    """Próximo rótulo "Id + a/b/c..." pra um painel que reaproveitou sobra de OUTRO painel do mesmo
    Id. base. Sequência por Id. (a, b, c...). Igual para Parede e Teto."""
    sufixos[id_painel_base] = sufixos.get(id_painel_base, 0) + 1
    return f"{id_painel_base} + {chr(ord('a') + sufixos[id_painel_base] - 1)}"


def _reaproveitar_sobra(chave_pool, qtd_placas_normal, sobra_normal, largura_placa, limite_min, pools, saida, idx_atual, comp_atual=None):
    """Reaproveitamento de sobra de placa (Parede/Teto), na ordem de lançamento — pool de peças por
    `chave_pool` (Parede: tipo+espessura; Teto: tipo+espessura), melhor-encaixe (menor peça já
    suficiente). Só entra em jogo quando o cálculo normal já desperdiça alguma coisa (sobra_normal > 0);
    a reutilização só ocorre se cobrir a falta INTEIRA (economiza exatamente 1 placa), nunca parcial.
    `comp_atual` é o comprimento/altura da placa desta linha: a sobra só serve se seu comprimento for
    MAIOR OU IGUAL ao necessário (a peça mais comprida é cortada pra atender a mais curta — por isso
    ordenar do maior p/ o menor maximiza o reuso). O saldo (m) é exibido na linha que GEROU a sobra e
    abatido ao vivo a cada consumo (zera na tela se cair abaixo do limite). Retorna (qtd_placas_final,
    origem_idx_da_peca_consumida_ou_None, saldo_desta_linha) — quem chama decide o rótulo "+ a/b/c"
    (só marca quando origem != a própria linha, ou seja, reuso de OUTRO painel)."""
    pool = pools.setdefault(chave_pool, [])
    if sobra_normal <= 0:
        # nada a reaproveitar — este item já é eficiente, não gera nem consome sobra
        return qtd_placas_normal, None, None

    falta = round(largura_placa - sobra_normal, 4)
    candidatos = [pc for pc in pool if pc["valor"] >= falta
                  and (comp_atual is None or pc.get("comp") is None or pc["comp"] >= comp_atual - 1e-9)]
    if candidatos:
        peca = min(candidatos, key=lambda pc: pc["valor"])   # melhor-encaixe: menor peça já suficiente
        origem = peca["origem_idx"]
        peca["valor"] = round(peca["valor"] - falta, 4)
        if peca["valor"] < limite_min:
            pool.remove(peca)
            saida[origem]["saldo_m"] = 0
        else:
            saida[origem]["saldo_m"] = peca["valor"]
        return qtd_placas_normal - 1, origem, None

    # não achou peça suficiente: mantém o cálculo normal; a sobra deste item vira peça nova (se
    # já nascer abaixo do limite, nem entra na pool e o saldo exibido é 0)
    if sobra_normal >= limite_min:
        pool.append({"origem_idx": idx_atual, "valor": round(sobra_normal, 4), "comp": comp_atual})
        return qtd_placas_normal, None, round(sobra_normal, 4)
    return qtd_placas_normal, None, 0


def _comp_placa_teto(comprimento, vao):
    """Divide o comprimento do teto (dimensao_2) até a peça caber no vão máx. entre apoios do
    material: menor N inteiro com comprimento/N <= vao. Retorna (comp_placa_2casas, N). Sem vão
    cadastrado ou comprimento <= vão -> N=1 (nada muda). Vão em metros (mesma unidade das medidas)."""
    if not comprimento:
        return None, 1
    if vao and comprimento > vao:
        n = math.ceil(round(comprimento / vao, 6))
    else:
        n = 1
    return round(comprimento / n, 2), n


def calcular_paineis(db, projeto: m.Projeto) -> list:
    paineis = (db.query(m.PainelTermico).filter_by(projeto_id=projeto.id)
               .order_by(m.PainelTermico.ordem, m.PainelTermico.id).all())
    largura_placa = projeto.largura_placa_painel_m or 0
    piso_larg = projeto.piso_placa_largura_m or 0
    piso_comp = projeto.piso_placa_comprimento_m or 0
    limite_min = projeto.largura_min_aproveitamento_placa_m or 0

    # Vão máx. entre apoios (m) por espessura/material — a espessura do painel ("PIR 70mm") casa
    # com material da tabela cat_isolamento_parede_teto. Usado só pra Teto.
    vao_por_espessura = {iso.material: (iso.vao_maximo_apoios_mm / 1000.0)
                         for iso in db.query(m.IsolamentoParedeTeto).all() if iso.vao_maximo_apoios_mm}

    # Id. de painel (P01/T01...) agrupado por (tipo, espessura, dimensao_2 — Altura/Largura, NÃO
    # o perímetro/comprimento) — confirmado pelo usuário.
    grupos_id = {}
    contador = {"Parede": 0, "Teto": 0}
    pools_sobra = {}
    sufixos_sobra = {}
    saida = []
    for p in paineis:
        area = p.dimensao_1 * p.dimensao_2 if p.dimensao_1 is not None and p.dimensao_2 is not None else None
        qtd_placas = area_considerada = id_painel = id_painel_base = None
        saldo_m = None
        comp_placa_m = None

        def _garantir_id():
            chave = (p.tipo, p.espessura, p.dimensao_2)
            if p.tipo in contador and chave not in grupos_id:
                contador[p.tipo] += 1
                prefixo = "P" if p.tipo == "Parede" else "T"
                grupos_id[chave] = f"{prefixo}{contador[p.tipo]:02d}"
            return grupos_id.get(chave)

        if p.tipo == "Isolamento Piso":
            if area is not None and piso_larg and piso_comp:
                qtd_placas = math.ceil(round(area / (piso_larg * piso_comp), 4))
                area_considerada = qtd_placas * piso_larg * piso_comp
                if _piso_dupla_camada(p.espessura):
                    area_considerada *= 2

        elif p.tipo == "Teto":
            # Comprimento da placa = comprimento (dimensao_2) dividido até caber no vão máx.
            comp_placa_m, n_fileiras = _comp_placa_teto(p.dimensao_2, vao_por_espessura.get(p.espessura))
            id_painel = id_painel_base = _garantir_id()
            if p.dimensao_1 and largura_placa and comp_placa_m:
                qtd_normal_fileira = math.ceil(round(p.dimensao_1 / largura_placa, 4))
                sobra_fileira = round(qtd_normal_fileira * largura_placa - p.dimensao_1, 4)
                # Cada fileira é uma "linha" que gera/consome sobra; a linha do teto é pré-inserida
                # pra receber o saldo ao vivo. Pool por tipo+espessura (sem o comprimento na chave):
                # a sobra de uma placa mais comprida atende teto de placa mais curta — o comprimento
                # entra como filtro (>=) dentro de _reaproveitar_sobra via comp_atual.
                chave_pool = ("Teto", p.espessura)
                idx = len(saida)
                id_planta, camara_nome, chave_grupo = _grupo_de(p)
                row = {**model_to_dict(p), "id_painel": id_painel_base, "id_painel_base": id_painel_base,
                       "saldo_m": None, "id_planta": id_planta, "camara_nome": camara_nome,
                       "chave_grupo": chave_grupo, "largura_placa_m": largura_placa,
                       "area_total_m2": round(area, 2) if area is not None else None,
                       "qtd_placas": None, "area_considerada_m2": None, "comp_placa_m": comp_placa_m}
                saida.append(row)
                total_qtd = 0
                id_label = id_painel_base
                for _ in range(n_fileiras):
                    q, origem, saldo_gen = _reaproveitar_sobra(
                        chave_pool, qtd_normal_fileira, sobra_fileira, largura_placa,
                        limite_min, pools_sobra, saida, idx, comp_atual=comp_placa_m)
                    total_qtd += q
                    if saldo_gen is not None:
                        row["saldo_m"] = saldo_gen
                    if origem is not None and origem != idx:   # reuso de OUTRO painel -> ganha sufixo
                        id_label = _proximo_sufixo(sufixos_sobra, id_painel_base)
                row["id_painel"] = id_label
                row["qtd_placas"] = total_qtd
                row["area_considerada_m2"] = round(total_qtd * largura_placa * comp_placa_m, 2)
                continue  # linha já inserida
            # sem dimensao_1: cai pro append compartilhado abaixo (só Id. e comp_placa)

        else:  # Parede
            comp_placa_m = round(p.dimensao_2, 2) if p.dimensao_2 is not None else None
            if p.dimensao_1 and largura_placa:
                qtd_placas_normal = math.ceil(round(p.dimensao_1 / largura_placa, 4))
                sobra_normal = round(qtd_placas_normal * largura_placa - p.dimensao_1, 4)
                id_painel_base = _garantir_id()
                # Pool por tipo+espessura (sem a altura na chave): a sobra de uma parede mais alta
                # atende parede mais baixa — a altura entra como filtro (>=) via comp_atual (mesma
                # regra do teto, "altura menores ou iguais").
                qtd_placas, origem, saldo_m = _reaproveitar_sobra(
                    ("Parede", p.espessura), qtd_placas_normal, sobra_normal, largura_placa,
                    limite_min, pools_sobra, saida, len(saida), comp_atual=p.dimensao_2)
                id_painel = _proximo_sufixo(sufixos_sobra, id_painel_base) if origem is not None else id_painel_base
                area_considerada = qtd_placas * largura_placa * (p.dimensao_2 or 0)
            else:
                id_painel = id_painel_base = _garantir_id()

        id_planta, camara_nome, chave_grupo = _grupo_de(p)
        saida.append({
            **model_to_dict(p),
            "id_painel": id_painel,
            "id_painel_base": id_painel_base,
            "saldo_m": saldo_m,
            "id_planta": id_planta,
            "camara_nome": camara_nome,
            "chave_grupo": chave_grupo,
            "largura_placa_m": largura_placa,
            "area_total_m2": round(area, 2) if area is not None else None,
            "qtd_placas": qtd_placas,
            "area_considerada_m2": round(area_considerada, 2) if area_considerada is not None else None,
            "comp_placa_m": comp_placa_m,
        })
    return saida


def calcular_portas(db, projeto: m.Projeto) -> list:
    """Id. = PREFIXO-NN-MM: NN = nº do "padrão" (modelo+sentido+largura+altura), na ordem em que
    cada padrão apareceu pela primeira vez; MM = sequencial dentro desse mesmo padrão."""
    portas = (db.query(m.PortaFrigorifica).filter_by(projeto_id=projeto.id)
              .order_by(m.PortaFrigorifica.ordem, m.PortaFrigorifica.id).all())

    # Prefixo do Id e Descrição Inicial vêm do cadastro de Modelo Porta (Configurações), não mais
    # de um dicionário fixo. Modelo sem prefixo definido -> "P" (neutro, só até o usuário preencher).
    modelos_lkp = db.query(m.LookupPainelPorta).filter_by(categoria="Modelo Porta").all()
    prefixo_por_modelo = {x.valor: (x.prefixo_id or "").strip() for x in modelos_lkp}
    desc_ini_por_modelo = {x.valor: (x.descricao_inicial or "").strip() for x in modelos_lkp}

    padrao_num = {}       # (modelo,sentido,largura,altura) -> NN
    contador_padrao = {}  # prefixo -> próximo NN
    seq_padrao = {}       # (modelo,sentido,largura,altura) -> próximo MM

    saida = []
    for p in portas:
        prefixo = prefixo_por_modelo.get(p.modelo) or "P"
        chave_padrao = (p.modelo, p.sentido, p.vao_largura_mm, p.vao_altura_mm)
        if chave_padrao not in padrao_num:
            contador_padrao[prefixo] = contador_padrao.get(prefixo, 0) + 1
            padrao_num[chave_padrao] = contador_padrao[prefixo]
            seq_padrao[chave_padrao] = 0
        seq_padrao[chave_padrao] += 1
        id_porta = f"{prefixo}-{padrao_num[chave_padrao]:02d}-{seq_padrao[chave_padrao]:02d}"

        id_planta, camara_nome, chave_grupo = _grupo_de(p)
        saida.append({
            **model_to_dict(p),
            "id_porta": id_porta,
            "id_planta": id_planta,
            "camara_nome": camara_nome,
            "chave_grupo": chave_grupo,
            "descricao": _descricao_porta(p, desc_ini_por_modelo.get(p.modelo, "")),
        })
    return saida


def _valvulas_por_camara(db, projeto: m.Projeto):
    """Conta válvula sem/com aquecimento — uma vez por câmara que tem painel de parede/teto
    lançado (isolamento de piso não conta), pelo volume da câmara / limite configurável,
    arredondado pra cima. Temp. interna da câmara <= 0°C = com aquecimento; > 0°C = sem.
    Retorna (sem_total, com_total, por_id_planta) — o terceiro pro modo 'camara'."""
    limite_cfg = db.query(m.ConfiguracaoGlobal).filter_by(chave="limite_valvula_equalizacao_m3").first()
    limite_m3 = (limite_cfg.valor if limite_cfg else 2000) or 2000

    camaras = {}
    q = db.query(m.PainelTermico).filter_by(projeto_id=projeto.id).filter(m.PainelTermico.tipo != "Isolamento Piso")
    for p in q.all():
        camara = _camara_de(p)
        if camara:
            camaras[(type(camara).__name__, camara.id)] = camara

    sem_aquec = com_aquec = 0
    por_id_planta = {}
    for camara in camaras.values():
        vol = _volume_camara(camara) or 0
        qtd = math.ceil(vol / limite_m3) if vol else 0
        com = camara.temp_interna is not None and camara.temp_interna <= 0
        if com:
            com_aquec += qtd
        else:
            sem_aquec += qtd
        por_id_planta[_codigo_camara(camara)] = (qtd if com else 0, qtd if not com else 0)  # (com, sem)
    return sem_aquec, com_aquec, por_id_planta


def _linha(item, unidade, quantidade):
    """Toda linha do resumo tem UMA quantidade com SUA unidade (m² ou un) — nunca duas colunas
    concorrentes ("quantidade" ora significando placas, ora nada). Decisão do usuário: mais
    consistente ter sempre Unid. + Quantidade em vez de Quantidade/Área alternando de sentido."""
    return {"item": item, "unidade": unidade, "quantidade": round(quantidade, 2) if isinstance(quantidade, float) else quantidade}


def _paineis_por_espessura(itens, prefixo_item):
    """Agrupa painéis (parede/teto OU piso) por espessura — item já vem com o texto descritivo
    (ex.: "Painéis térmicos tipo EPS 100mm" / "Isolamento de Piso tipo EPS 200mm..."). Quantidade
    em m²: somar qtd. de placas de configurações (Id.Painel) diferentes não é um número que se
    compra — só a área é aditiva de verdade aqui. Quantidade em placas só aparece agrupada por
    Id.Painel (ver _paineis_por_id)."""
    grupos = {}
    for it in itens:
        esp = it["espessura"] or "—"
        g = grupos.setdefault(esp, {"espessura": esp, "area": 0.0})
        g["area"] += it.get("area_considerada_m2") or 0
    # Ordena por espessura CRESCENTE pelo número (mm), não alfabético ("PIR 70mm" antes de
    # "PIR 100mm"); sem número (ex.: "—") vai pro fim.
    def _chave_esp(g):
        m_num = re.search(r"\d+", g["espessura"] or "")
        return (int(m_num.group()) if m_num else 10**9, g["espessura"])
    linhas = [_linha(f"{prefixo_item}{g['espessura']}", "m²", g["area"])
              for g in sorted(grupos.values(), key=_chave_esp)]
    return linhas


def _paineis_por_id(itens, desc_por_espessura=None):
    """Por Id.Painel a quantidade que se compra de fato é em placas (un) — é o que se pede ao
    fornecedor pra essa peça específica. Área total (m²) do grupo vem junto (campo "area_m2"),
    exibida à direita de Quantidade nos modos por Id. Agrupa pelo Id. BASE (sem o sufixo "+ a/b/c"
    de reaproveitamento de sobra) — a compra é sempre do total já líquido, o sufixo é só
    informativo no lançamento item a item."""
    grupos = {}
    for it in itens:
        idp = it.get("id_painel_base") or it["id_painel"] or "—"
        g = grupos.setdefault(idp, {"id_painel": idp, "tipo": it["tipo"], "espessura": it["espessura"], "qtd": 0, "area": 0.0,
                                    "larg_placa_m": it.get("largura_placa_m"), "comp_placa_m": it.get("comp_placa_m")})
        g["qtd"] += it.get("qtd_placas") or 0
        g["area"] += it.get("area_considerada_m2") or 0
    linhas = []
    desc_por_espessura = desc_por_espessura or {}
    for g in sorted(grupos.values(), key=lambda g: g["id_painel"]):
        # Item = "{ID} - {Descrição fixa} - {Espessura} - {Larg. Placa}mm x {Comp. Placa}mm".
        # Peça: largura da placa (mm) x altura(parede)/comprimento de placa(teto) (mm). Só parede/teto.
        larg_mm = round((g["larg_placa_m"] or 0) * 1000)
        comp_mm = round((g["comp_placa_m"] or 0) * 1000)
        desc = desc_por_espessura.get(g["espessura"], "")
        partes = [p for p in [g["id_painel"], desc, g["espessura"], f"{larg_mm}mm x {comp_mm}mm"] if p]
        linha = _linha(" - ".join(partes), "un", g["qtd"])
        linha["area_m2"] = round(g["area"], 2)
        linhas.append(linha)
    return linhas


def _linhas_acessorios(parede_teto, sem_aquec, com_aquec):
    area_total = sum(p.get("area_considerada_m2") or 0 for p in parede_teto)
    return [
        _linha("Acessórios de Montagem", "m²", area_total),
        _linha("Válvula Equalização de Pressão sem Aquecimento", "un", sem_aquec),
        _linha("Válvula Equalização de Pressão com Aquecimento", "un", com_aquec),
    ]


def _linha_barreira_vapor(piso):
    # A barreira de vapor cobre a area FISICA real do piso -- em cameras com isolamento de piso
    # de dupla camada, "area_considerada_m2" ja vem dobrada (2 placas fisicas por posicao, ver
    # _piso_dupla_camada), entao aqui e' desfeita a dobra so pra essa linha (metade do valor).
    # Cameras com placa unica usam o valor cheio, que ja e' a area real.
    area_total = 0
    for p in piso:
        area = p.get("area_considerada_m2") or 0
        if _piso_dupla_camada(p.get("espessura")):
            area /= 2
        area_total += area
    return [_linha("Barreira de Vapor", "m²", area_total)]


def _portas_por_padrao(portas):
    """Portas nunca são agrupadas por espessura de fixação — mas portas com o MESMO padrão
    (mesmo modelo+sentido+largura+altura, ou seja, mesmo prefixo+NN do Id.) são somadas numa
    linha só (Quantidade), em vez de uma linha por porta individual. Id. mostrado sem o sufixo de
    sequência (MM). Descrição sempre antes do Id. na exibição."""
    grupos = {}
    ordem = []
    for p in portas:
        padrao = p["id_porta"].rsplit("-", 1)[0]
        tensao = p.get("tensao") or ""
        obs = p.get("observacoes") or ""
        # Tensão e Observação distintas viram linhas separadas (é o que se compra de fato).
        chave = (padrao, tensao, obs)
        if chave not in grupos:
            grupos[chave] = {"id_porta": padrao, "descricao": p["descricao"], "unidade": "un",
                             "quantidade": 0, "tensao": tensao, "observacoes": obs}
            ordem.append(chave)
        grupos[chave]["quantidade"] += (p.get("quantidade") or 1)
    return [grupos[k] for k in ordem]


def montar_resumo(db, projeto: m.Projeto, modo: str = "total") -> dict:
    """modo:
      'total'              — 1 tabela única (painéis por espessura, piso por espessura, portas lista geral)
      'painel_portas'       — painéis por Id.Painel, piso por espessura, portas por Id. de Câmara
      'painel_portas_geral' — igual acima, mas portas em lista geral (não separadas por câmara)
      'camara'              — tudo separado por Id. de Câmara
    Em qualquer modo: painéis/piso sempre agrupados por espessura (ou por Id.Painel nos modos
    painel_portas*); Acessórios de Montagem + Válvulas sempre como itens dentro da tabela de
    parede/teto; Barreira de Vapor sempre como item dentro da tabela de piso; portas nunca
    agrupadas por espessura de fixação."""
    paineis = calcular_paineis(db, projeto)
    portas = calcular_portas(db, projeto)
    sem_aquec, com_aquec, valvulas_por_camara = _valvulas_por_camara(db, projeto)

    parede_teto = [p for p in paineis if p["tipo"] in ("Parede", "Teto")]
    piso = [p for p in paineis if p["tipo"] == "Isolamento Piso"]
    # Descrição fixa por Espessura Parede/Teto (texto que o usuário define na config) — usada no
    # item do resumo "por Id.". Só parede/teto.
    desc_por_espessura = {x.valor: (x.descricao_inicial or "").strip()
                          for x in db.query(m.LookupPainelPorta).filter_by(categoria="Espessura Parede/Teto").all()}

    if modo == "total":
        return {
            "modo": modo,
            "paineis_parede_teto": _paineis_por_espessura(parede_teto, "Painéis térmicos tipo ")
                                    + (_linhas_acessorios(parede_teto, sem_aquec, com_aquec) if parede_teto else []),
            "isolamento_piso": _paineis_por_espessura(piso, "Isolamento de Piso tipo ")
                                + (_linha_barreira_vapor(piso) if piso else []),
            "portas": _portas_por_padrao(portas),
        }

    if modo in ("painel_portas", "painel_portas_geral"):
        saida = {
            "modo": modo,
            "paineis_parede_teto": _paineis_por_id(parede_teto, desc_por_espessura)
                                    + (_linhas_acessorios(parede_teto, sem_aquec, com_aquec) if parede_teto else []),
            "isolamento_piso": _paineis_por_espessura(piso, "Isolamento de Piso tipo ")
                                + (_linha_barreira_vapor(piso) if piso else []),
        }
        if modo == "painel_portas":
            por_camara_portas = {}
            for p in portas:
                chave = p["chave_grupo"]
                g = por_camara_portas.setdefault(chave, {"id_planta": p["id_planta"], "camara_nome": p["camara_nome"], "_portas": []})
                g["_portas"].append(p)
            portas_por_camara = []
            for g in por_camara_portas.values():
                brutas = g.pop("_portas")
                g["portas"] = _portas_por_padrao(brutas)
                portas_por_camara.append(g)
            saida["portas_por_camara"] = portas_por_camara
        else:
            saida["portas"] = _portas_por_padrao(portas)
        return saida

    if modo == "camara":
        por_camara = {}
        for p in paineis:
            chave = p["chave_grupo"]
            g = por_camara.setdefault(chave, {"id_planta": p["id_planta"], "camara_nome": p["camara_nome"],
                                               "_parede_teto": [], "_piso": [], "_portas": []})
            (g["_piso"] if p["tipo"] == "Isolamento Piso" else g["_parede_teto"]).append(p)
        for p in portas:
            chave = p["chave_grupo"]
            g = por_camara.setdefault(chave, {"id_planta": p["id_planta"], "camara_nome": p["camara_nome"],
                                               "_parede_teto": [], "_piso": [], "_portas": []})
            g["_portas"].append(p)
        for chave, g in por_camara.items():
            pt, pi, pr = g.pop("_parede_teto"), g.pop("_piso"), g.pop("_portas")
            com_c, sem_c = valvulas_por_camara.get(g["id_planta"], (0, 0))
            g["paineis_parede_teto"] = _paineis_por_espessura(pt, "Painéis térmicos tipo ") + (_linhas_acessorios(pt, sem_c, com_c) if pt else [])
            g["isolamento_piso"] = _paineis_por_espessura(pi, "Isolamento de Piso tipo ") + (_linha_barreira_vapor(pi) if pi else [])
            g["portas"] = _portas_por_padrao(pr)
        return {"modo": modo, "camaras": list(por_camara.values())}

    raise ValueError(f"modo inválido: {modo}")


def _descricao_porta(p: m.PortaFrigorifica, descricao_inicial: str) -> str:
    """Descrição composta 100% pelo cadastro (sem texto fixo por modelo/função):
    "{Descrição Inicial} {Modelo} {Sentido} - {Vão Larg}mm x {Vão Alt}mm - #{Esp. Fix}mm"."""
    modelo = p.modelo or ""
    sentido = p.sentido or ""
    larg = int(p.vao_largura_mm) if p.vao_largura_mm else "?"
    alt = int(p.vao_altura_mm) if p.vao_altura_mm else "?"
    fix = int(p.espessura_fixacao_mm) if p.espessura_fixacao_mm else "?"
    return f"{descricao_inicial} {modelo} {sentido} - {larg}mm x {alt}mm - #{fix}mm".strip()
