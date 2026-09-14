# -*- coding: utf-8 -*-
"""Tela F — Compilação Geral. Layout invertido da Tela 5 (campo = linha, câmara = coluna) — só
Câmara Completo e Câmara Simples entram como coluna (Expositor não tem forçador/dimensões nesse
formato). Blocos "Unidades/Rack" e "Condensadores" são por SISTEMA (não por câmara) — o frontend
mescla a célula por todas as câmaras daquele sistema."""
import io
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from .. import models as m
from ..database import get_db
from ..utils import chave_ordem_camara, resposta_excel_projeto
from ..calc_service import calcular_camara_completo_seguro as calcular_camara_completo, calcular_camara_simples_seguro as calcular_camara_simples
from ..calculos.comum import folga_percentual, carga_gas_estimada, W_PARA_KCAL_H
from ..exportacao.compilacao_geral_export import gerar_excel_compilacao_geral
from .compilacao import _eletrica_forcador
from .unidades_condensadoras import _eletrica_da_tensao
from .. import campo_catalogo as cc
from .. import id_comercial as idc

router = APIRouter(prefix="/api", tags=["compilacao-geral"])

# ---- Nomenclatura completa do forçador (código comercial) — mesma lógica de
# componentes.js:_carregarPainelNomenclaturaForcador, portada pro backend porque a Tela F precisa
# do valor pronto (não interativo) pra exibir/exportar. ----
_DEGELO_PALAVRAS = {"Natural": ["degelo a ar", "degelo natural"], "Elétrico": ["degelo elétrico", "degelo eletrico"],
                     "Gás quente": ["gás quente", "gas quente"]}


def _parse_opcoes(texto):
    if not texto:
        return []
    out = []
    for linha in texto.split("\n"):
        linha = linha.strip()
        if not linha:
            continue
        partes = linha.split("=", 1)
        codigo = partes[0].strip()
        rotulo = partes[1].strip() if len(partes) > 1 else codigo
        out.append({"codigo": codigo, "rotulo": rotulo or codigo})
    return out


def _tipo_degelo_da_opcao(rotulo):
    low = rotulo.lower()
    for tipo, palavras in _DEGELO_PALAVRAS.items():
        if any(p in low for p in palavras):
            return tipo
    return None


def _nomenclatura_completa_forcador(db, considerado, tensao_comando=None):
    """Código comercial do forçador pelo motor genérico de Campos configuráveis (campo_catalogo.py),
    o mesmo das Unidades Condensadoras. O campo de degelo é modo Automático (campo_busca_sistema=
    "tipo_degelo", substitui o coringa '*'/'x' do modelo). Tensão usa a Tensão Elétrica de Comando
    do projeto (não a de Equipamentos, essa é da UC/Rack/Condensador) — forçadores e expositores
    usam Comando."""
    if not considerado or not considerado.get("modelo_resultante"):
        return None
    linha_id = considerado["linha_id"]
    campos = cc.listar_campos(db, "Forcador", linha_id)
    if not campos:
        return considerado["modelo_resultante"]
    contexto = {"tipo_degelo": considerado.get("tipo_degelo_selecionado"), "tensao_comando": tensao_comando}
    for chave in ("fpi", "num_ventiladores", "diametro_ventilador_mm"):
        valor = considerado.get(chave)
        if valor is not None:
            contexto[chave] = str(valor)
    selecoes = considerado.get("nomenclatura_selecionada") or {}
    # modelo pode trazer coringa 'x' (além de '*') — normaliza pra '*' que é o que montar_codigo troca
    modelo_base = re.sub(r"[x]", "*", considerado["modelo_resultante"], count=1)
    return cc.montar_codigo(db, "Forcador", linha_id, modelo_base=modelo_base,
                             contexto=contexto, selecoes_manuais=selecoes)


def _temp_condensacao(projeto, sistema):
    if projeto is None or projeto.temp_ambiente is None or sistema.delta_condensacao is None:
        return None
    return round(projeto.temp_ambiente + sistema.delta_condensacao, 1)


def _bloco_carga(projeto, sistema, camara, calc, tipo):
    return {
        "sistema": sistema.nome,
        "temp_ambiente": projeto.temp_ambiente if projeto else None,
        "delta_condensacao": sistema.delta_condensacao,
        "temp_condensacao": _temp_condensacao(projeto, sistema),
        "temp_evaporacao": sistema.temp_evaporacao,
        "temp_interna": camara.temp_interna,
        "dt_evaporacao": calc.get("dt_camara"),
        "largura": camara.largura if tipo == "completo" else None,
        "comprimento": camara.comprimento if tipo == "completo" else None,
        "pedireito": camara.pedireito,
        "carga_termica_kcal_h": calc.get("capacidade_requerida"),
    }


def _bloco_memorial(calc, tipo):
    if tipo != "completo":
        return None  # Câmara Simples não tem memorial Q1-Q7 detalhado (carga tabelada por faixa)
    return {"q1_produto": calc.get("q1_produto"), "q2_embalagem": calc.get("q2_embalagem"),
            "q3_penetracao": calc.get("q3_penetracao"), "q4_infiltracao": calc.get("q4_infiltracao"),
            "q5_pessoas": calc.get("q5_pessoas"), "q6_iluminacao": calc.get("q6_iluminacao"),
            "q7_equipamentos": calc.get("q7_equipamentos"), "q8_forcadores": calc.get("q8_forcadores"),
            "total_24h": calc.get("carga_termica_total_24h")}


RESPONSABILIDADE_DADOS_ENTRADA_PADRAO = (
    "Os dados de entrada abaixo (produto, movimentação, temperaturas, ocupação, iluminação, "
    "equipamentos e portas) foram fornecidos pelo cliente e são de sua inteira responsabilidade. "
    "O dimensionamento assume que refletem as condições reais de operação; qualquer divergência "
    "entre estes dados e a operação real altera a carga térmica calculada e o desempenho do sistema."
)


def _bloco_dados_entrada(camara, tipo, projeto):
    """Dados de entrada fornecidos pelo cliente (Câmara Completo) — expostos na Tela F como prova/
    registro de responsabilidade. Câmara Simples usa carga tabelada por área, não tem esse
    memorial de produto/operação, então devolve None."""
    if tipo != "completo":
        return None
    equipamentos = "; ".join(
        f"{e.tipo_equipamento.nome} ({e.qtd or 0}x, {e.tempo or 0}h/24h)"
        for e in camara.equipamentos if e.tipo_equipamento
    ) or None
    def _porta_str(p):
        fonte = (f"Adjacente {p.temp_adjacente if p.temp_adjacente is not None else '?'}°C/"
                 f"{p.umidade_adjacente if p.umidade_adjacente is not None else '?'}%"
                 if p.fonte_ar == "Adjacente" else "Externo")
        return (f"{p.quantidade or 1}× {p.largura or 0}×{p.altura or 0}m, "
                f"{p.freq_abertura_min_h or 0}min/h, {p.protecao or '—'}, {fonte}")
    portas_detalhe = "; ".join(_porta_str(p) for p in camara.portas) or None
    num_portas_total = sum((p.quantidade or 1) for p in camara.portas) or None
    adjacente = camara.fonte_ar == "Adjacente"
    return {
        "produto": camara.produto.nome if camara.produto else None,
        "temp_entrada": camara.temp_entrada, "temp_saida": camara.temp_saida,
        "temp_interna": camara.temp_interna,
        "mov_diaria": camara.mov_diaria, "qtd_estocada": camara.qtd_estocada,
        "tempo_processo": camara.tempo_processo,
        "embalagem_tipo": camara.tipo_embalagem.nome if camara.tipo_embalagem else None,
        "massa_embalagem": camara.massa_embalagem,
        "num_pessoas": camara.num_pessoas, "tempo_pessoas": camara.tempo_pessoas,
        "qtd_luminarias": camara.qtd_luminarias, "potencia_luminaria": camara.potencia_luminaria,
        "horas_iluminacao_carga": camara.horas_iluminacao_carga,
        "equipamentos": equipamentos,
        "num_portas": num_portas_total, "portas": portas_detalhe,
        "fonte_ar_paredes": camara.fonte_ar or "Externo",
        # Ambiente Externo: sem "adjacente" real — mostra a temp./UR externa do projeto como
        # consulta (não editável aqui, só referência de onde a fonte de ar realmente vem).
        "temp_adjacente": camara.temp_adjacente if adjacente else (projeto.temp_ambiente if projeto else None),
        "umidade_adjacente": camara.umidade_adjacente if adjacente else (projeto.ur_externa if projeto else None),
    }


def _bloco_forcadores(db, camara, calc, tensao_comando):
    considerado = next((f for f in calc["forcadores"] if f.get("considerado") and f.get("modelo_resultante")), None)
    eletrica = _eletrica_forcador(camara, calc, tensao_comando)
    if not considerado:
        return {"quantidade": None, "fornecedor": None, "modelo_evp": None, "modelo_comercial": None,
                "fabricante_valvula": None, "modelo_valvula": None, "modelo_valvula_base": None, "valvula_qtd_unit": None,
                "gas_refrigerante": None, "capacidade_unit_kcal_h": None, "diametro_ventilador_mm": None,
                "num_ventiladores": None, "vazao_ar_m3h": None, "tensao": None, "tipo_degelo": None,
                "corrente_ventiladores_a": None, "potencia_resist_degelo_w": None, "corrente_resist_degelo_a": None,
                "flecha_ar_m": None, "trocas_de_ar": None, "quantidade_gas_kg": None, "folga_tecnica_pct": None}
    # Válvula de Expansão da linha considerada — mesmo rótulo padrão da Tela 5 ("Nx TEN2 orif. 02").
    # modelo_valvula_base/valvula_qtd_unit (sem o "Nx" embutido) existem à parte pra Tela 10 poder
    # agrupar pelo modelo puro e multiplicar a quantidade real (ver bug real corrigido: Tela 10
    # duplicava a mesma válvula em linhas separadas por causa do "Nx" na descrição).
    from .compilacao import _rotulo_valvula, _rotulo_valvula_base
    valv = next((v for v in considerado.get("valvulas", []) if v.get("considerado")), None)
    rotulo_valv = _rotulo_valvula(valv)
    rotulo_valv_base = _rotulo_valvula_base(valv)
    return {
        "quantidade": considerado.get("quantidade"), "fornecedor": considerado.get("fabricante"),
        # Modelo EVP usa a nomenclatura COMPLETA (código comercial composto), não só o código base
        # do catálogo — mesma composição já usada no painel de nomenclatura das Telas 2/3.
        "modelo_evp": _nomenclatura_completa_forcador(db, considerado, tensao_comando) or considerado.get("modelo_resultante"),
        # Modelo Comercial do forçador — ainda sem fonte de dado definida (usuário vai decidir depois
        # qual composição/valor usar aqui, mesmo espírito do Modelo Comercial do Rack).
        "modelo_comercial": None,
        "fabricante_valvula": (valv or {}).get("fabricante") or camara.sistema.fabricante_valvula,
        "modelo_valvula": rotulo_valv if rotulo_valv != "—" else None,
        "modelo_valvula_base": rotulo_valv_base if rotulo_valv_base != "—" else None,
        "valvula_qtd_unit": (valv or {}).get("quantidade") or 1,
        "gas_refrigerante": camara.sistema.gas_refrigerante,
        "capacidade_unit_kcal_h": considerado.get("capacidade_corrigida_unitaria"),
        "diametro_ventilador_mm": considerado.get("diametro_ventilador_mm"),
        "num_ventiladores": considerado.get("num_ventiladores"),
        "vazao_ar_m3h": considerado.get("vazao_ar_m3h"), "tensao": tensao_comando,
        "tipo_degelo": considerado.get("tipo_degelo_selecionado"),
        "corrente_ventiladores_a": eletrica.get("vent_a"),
        "potencia_resist_degelo_w": eletrica.get("degelo_w"), "corrente_resist_degelo_a": eletrica.get("degelo_a"),
        "flecha_ar_m": considerado.get("flecha_ar_m"), "trocas_de_ar": considerado.get("trocas_de_ar"),
        "quantidade_gas_kg": considerado.get("carga_gas_kg"), "folga_tecnica_pct": considerado.get("folga_real"),
    }


def _carga_requerida_sistema(itens_camaras):
    return round(sum((c["bloco_carga"]["carga_termica_kcal_h"] or 0) for c in itens_camaras), 1)


def _carga_gas_estimada_sistema(camaras_out, tanque_liquido_l):
    """Soma da carga de gás de TODOS os forçadores considerados do sistema (por unidade x
    quantidade de cada câmara), usada pela fórmula de carga_gas_estimada (comum.py) — mesmo
    espírito de _forcadores_sistema_total, mas somando quantidade_gas_kg em vez de capacidade
    -- aprovado 2026-08-11."""
    soma = 0.0
    tem_dado = False
    for c in camaras_out:
        f = c["forcador"]
        if f.get("quantidade_gas_kg") and f.get("quantidade"):
            soma += f["quantidade_gas_kg"] * f["quantidade"]
            tem_dado = True
    if not tem_dado:
        return None
    return carga_gas_estimada(soma, tanque_liquido_l)


def _forcadores_sistema_total(camaras_out, carga_termica_kcal_h):
    """Capacidade fornecida por TODOS os forçadores do sistema (soma de capacidade_unit_kcal_h x
    quantidade de cada câmara) contra a carga térmica do sistema -- não existia antes (_bloco_
    forcadores só calcula por câmara isolada). Usa a mesma fórmula de folga_percentual já usada em
    todo o resto do app (calc_service.py), pra ficar consistente com a folga por câmara (aprovado
    2026-08-10, item pedido pra Tela 12 — Comparativo de Revisões)."""
    capacidade_total = 0.0
    for c in camaras_out:
        f = c["forcador"]
        if f.get("capacidade_unit_kcal_h") and f.get("quantidade"):
            capacidade_total += f["capacidade_unit_kcal_h"] * f["quantidade"]
    if not capacidade_total:
        return {"capacidade_fornecida_kcal_h": None, "folga_tecnica_pct": None}
    return {
        "capacidade_fornecida_kcal_h": round(capacidade_total, 1),
        "folga_tecnica_pct": round(folga_percentual(capacidade_total, carga_termica_kcal_h), 1),
    }


def _bloco_rack_uc(db, sistema, carga_requerida, camaras_out):
    """Rack Paralelo (dado próprio, Tela 6) ou Unidade Condensadora (dado já existente na seleção
    da Tela 1 — parcial: falta COP, capacidade unitária, vazão mássica nesse caso)."""
    if sistema.tipo_compressao == "4.1.2":  # Rack Paralelo
        rack = sistema.rack_paralelo
        if not rack:
            return {"tipo_equipamento": "Rack Paralelo", "fonte": "rack_vazio"}
        # Dados calculados (compressores, Tela 6) reaproveitados do mesmo endpoint do Resumo do Rack
        # — antes vinham de colunas mortas em RackParalelo (corrente_nominal_a, potencia_total_w
        # etc.), nunca escritas em lugar nenhum do app, então ficavam sempre em branco aqui.
        from .rack_paralelo import _modelo_comercial_rack, resumo_compressores, _extrair_numero
        dados_resumo = resumo_compressores(rack.id, db)
        resumo = dados_resumo["resumo"]
        completo = bool(dados_resumo["posicoes"]) and all(p["resultado"] is not None for p in dados_resumo["posicoes"])
        grupos = resumo["grupos_modelo"]
        modelo_compressor = " + ".join(f"{g['quantidade']}x {g['modelo']}" for g in grupos) if grupos else None
        carga_total_fornecida = resumo["capacidade_total_kcal_h"] if completo else None
        # N racks idênticos em paralelo: cada rack atende carga_requerida ÷ N; a folga é por rack.
        n_paralelo = max(rack.quantidade_paralelo or 1, 1)
        folga = (round(folga_percentual(carga_total_fornecida, carga_requerida / n_paralelo), 1)
                 if carga_total_fornecida else None)
        # Capacidade/conexões/óleo por grupo de modelo (posições podem ter modelos diferentes,
        # aprovado 2026-08-11: mostrar TODOS os grupos, "Nx valor + Mx valor", nunca "—" ambíguo
        # como antes; conexões usam a string INTEIRA da tabela Bitzer, sem extrair só a polegada).
        capacidade_compressor_kcal_h = (
            " + ".join(f"{g['quantidade']}x {g['capacidade_unitaria_kcal_h']:,.0f}".replace(",", ".")
                       for g in grupos if g.get("capacidade_unitaria_kcal_h") is not None) or None)
        conexao_succao = (" + ".join(f"{g['quantidade']}x {g['conexao_succao']}" for g in grupos if g.get("conexao_succao")) or None)
        conexao_descarga = (" + ".join(f"{g['quantidade']}x {g['conexao_descarga']}" for g in grupos if g.get("conexao_descarga")) or None)
        soma_oleo = sum(_extrair_numero(g["carga_oleo"]) * g["quantidade"] for g in grupos
                         if g.get("carga_oleo") and _extrair_numero(g["carga_oleo"]) is not None)
        carga_oleo_l = round(soma_oleo, 2) if soma_oleo else None
        projeto = sistema.projeto
        return {
            "tipo_equipamento": "Rack Paralelo", "fonte": "rack",
            # Rack não tem "modelo técnico" (sob medida, sem catálogo comercial — só UC tem).
            # "Modelo Comercial" é gerado automaticamente, não é mais texto livre.
            "quantidade_compressores": rack.quantidade_compressores, "modelo_tecnico": None,
            "modelo_comercial": _modelo_comercial_rack(rack, sistema),
            "tensao": projeto.tensao_equipamentos if projeto else None,
            "linha_compressor": rack.linha_compressor, "fabricante_compressor": rack.fabricante_compressor,
            "modelo_compressor": modelo_compressor,
            "cop_compressor": resumo["cop"] if completo else None,
            "capacidade_compressor_kcal_h": capacidade_compressor_kcal_h,
            "quantidade_paralelo": n_paralelo,
            "carga_total_fornecida_kcal_h": carga_total_fornecida,  # capacidade fornecida POR RACK (unitária)
            "carga_total_fornecida_sistema_kcal_h": round(carga_total_fornecida * n_paralelo, 1) if carga_total_fornecida else None,
            "calor_total_rejeitado_kcal_h": resumo["calor_rejeitado_total_kcal_h"] if completo else None,
            "calor_total_rejeitado_sistema_kcal_h": round(resumo["calor_rejeitado_total_kcal_h"] * n_paralelo, 1) if (completo and resumo["calor_rejeitado_total_kcal_h"]) else None,
            "potencia_total_w": resumo["potencia_total_w"] if completo else None,
            "corrente_nominal_a": resumo["corrente_total_a"] if completo else None,
            "corrente_maxima_trabalho_a": resumo.get("corrente_maxima_total_a") or rack.corrente_maxima_trabalho_a,
            "vazao_massica_kg_h": resumo["vazao_total_kg_h"] if completo else None,
            "carga_oleo_l": carga_oleo_l,
            "conexao_descarga": conexao_descarga, "conexao_succao": conexao_succao,
            "estrutura_equipamento": idc.nome_por_codigo(db, sistema.estrutura_compressao),
            "gas_refrigerante": sistema.gas_refrigerante,
            "temp_linha_liquido": sistema.temp_apos_subresfriamento or sistema.temp_apos_condensador,
            "tanque_liquido_l": rack.tanque_liquido_l,
            "carga_gas_estimada_kg": _carga_gas_estimada_sistema(camaras_out, rack.tanque_liquido_l),
            "tipo_partida": idc.nome_por_codigo(db, sistema.partida), "folga_tecnica_pct": folga,
        }

    # Unidade Condensadora Comercial — reaproveita a seleção já feita na Tela 1
    projeto = sistema.projeto
    from .unidades_condensadoras import obter_selecao
    resp = obter_selecao(sistema.id, db)
    escolhida = next((s for s in resp["selecoes"] if s.get("considerado") and s.get("unidade_id")), None)
    if not escolhida:
        return {"tipo_equipamento": "Unidade Condensadora Comercial", "fonte": "uc_vazio"}
    uc = db.get(m.UnidadeCondensadora, escolhida["unidade_id"])
    eletrica = _eletrica_da_tensao(uc, projeto.tensao_equipamentos if projeto else None)
    capacidade_kcal_h = escolhida["capacidade_kcal_h"]
    n_paralelo = max(escolhida.get("quantidade_paralelo", 1) or 1, 1)
    # N UCs idênticas em paralelo: cada uma atende carga_requerida ÷ N; folga por unidade.
    folga = round(folga_percentual(capacidade_kcal_h, carga_requerida / n_paralelo), 1) if capacidade_kcal_h else None
    return {
        "tipo_equipamento": "Unidade Condensadora Comercial", "fonte": "uc",
        # Modelo técnico usa o código comercial (compra) já calculado por obter_selecao() —
        # o mesmo valor exibido na Tela 1 ("Código comercial (compra): ...").
        "quantidade_compressores": uc.numero_compressores,
        "quantidade_paralelo": n_paralelo,
        "carga_total_fornecida_sistema_kcal_h": round(capacidade_kcal_h * n_paralelo, 1) if capacidade_kcal_h else None,
        "modelo_tecnico": escolhida.get("codigo_comercial") or uc.modelo,
        "modelo_comercial": None,
        "tensao": eletrica.tensao if eletrica else None, "linha_compressor": uc.tipo_compressor,
        "fabricante_compressor": uc.fabricante_compressor,
        "modelo_compressor": (eletrica.modelo_compressor if eletrica and eletrica.modelo_compressor else uc.modelo),
        "cop_compressor": None, "capacidade_compressor_kcal_h": None,
        "carga_total_fornecida_kcal_h": capacidade_kcal_h, "calor_total_rejeitado_kcal_h": None,
        "potencia_total_w": None,
        "corrente_nominal_a": eletrica.rla_a if eletrica else None,
        "corrente_maxima_trabalho_a": eletrica.mcc_a if eletrica else None,
        "vazao_massica_kg_h": None, "carga_oleo_l": None,
        "conexao_descarga": uc.conexao_liquido, "conexao_succao": uc.conexao_succao,
        "estrutura_equipamento": idc.nome_por_codigo(db, sistema.estrutura_compressao),
        "gas_refrigerante": sistema.gas_refrigerante,
        "temp_linha_liquido": sistema.temp_apos_subresfriamento or sistema.temp_apos_condensador,
        "tanque_liquido_l": None, "carga_gas_estimada_kg": None,
        "tipo_partida": idc.nome_por_codigo(db, sistema.partida), "folga_tecnica_pct": folga,
    }


def _bloco_condensador(db, sistema):
    """Rack Paralelo: condensador remoto (catálogo da Tela C, selecionado na Tela 6 — reaproveita
    o mesmo endpoint da Tela 6, não recalcula nada). Unidade Condensadora: condensador é "onboard"
    (embutido na própria UC) — não tem modelo próprio (não é um equipamento separado) nem
    capacidade/folga captadas isoladamente ainda — só ventiladores."""
    if sistema.tipo_compressao == "4.1.2":  # Rack Paralelo
        rack = sistema.rack_paralelo
        if not rack:
            return {"tipo_equipamento": "Condensador Remoto", "fonte": "rack_vazio",
                    "capacidade_condensador_kcal_h": None, "folga_tecnica_pct": None}
        from .rack_paralelo import selecao_condensador
        dados = selecao_condensador(rack.id, db)
        sel = dados.get("selecao")
        e = sel.get("escolhido") if sel else None
        if not e:
            return {"tipo_equipamento": "Condensador Remoto", "fonte": "rack_sem_selecao",
                    "capacidade_condensador_kcal_h": None, "folga_tecnica_pct": None}
        projeto = sistema.projeto
        qtd_cond = sel.get("quantidade_condensadores") or 1
        n_paralelo = dados.get("quantidade_paralelo") or 1   # N racks em paralelo
        codigo = e.get("codigo_comercial") or e.get("modelo")
        modelo_com_qtd = f"{qtd_cond}x {codigo}" if codigo else None
        return {
            "tipo_equipamento": "Condensador Remoto", "fonte": "rack",
            "modelo_condensador": modelo_com_qtd,
            "quantidade_condensadores": qtd_cond,
            "quantidade_paralelo": n_paralelo,
            "quantidade_condensadores_total": qtd_cond * n_paralelo,
            "fabricante_linha": f"{rack.fabricante_condensador or '—'} / {rack.linha_condensador or '—'}",
            "temp_ambiente": projeto.temp_ambiente if projeto else None,
            "delta_condensacao": sistema.delta_condensacao,
            "temp_condensacao": dados.get("temp_condensacao"),
            "qtd_ventiladores": e.get("qtd_ventiladores"),
            "diametro_ventilador_mm": e.get("diametro_ventilador_mm"),
            "tensao": dados.get("tensao_equipamentos"),
            "corrente_nominal_ventiladores_a": e.get("corrente_ventiladores_a"),
            "capacidade_condensador_kcal_h": e.get("capacidade_corrigida_total_kcal_h") or e.get("capacidade_corrigida_kcal_h"),
            "folga_tecnica_pct": sel.get("folga_real_pct"),
        }
    projeto = sistema.projeto
    from .unidades_condensadoras import obter_selecao
    resp = obter_selecao(sistema.id, db)
    escolhida = next((s for s in resp["selecoes"] if s.get("considerado") and s.get("unidade_id")), None)
    if not escolhida:
        return {"tipo_equipamento": "Condensador Onboard", "fonte": "uc_vazio",
                "capacidade_condensador_kcal_h": None, "folga_tecnica_pct": None}
    uc = db.get(m.UnidadeCondensadora, escolhida["unidade_id"])
    eletrica = _eletrica_da_tensao(uc, projeto.tensao_equipamentos if projeto else None)
    return {
        "tipo_equipamento": "Condensador Onboard", "fonte": "uc",
        "modelo_condensador": None,  # não é um equipamento separado — embutido na própria UC
        "temp_ambiente": projeto.temp_ambiente if projeto else None,
        "delta_condensacao": sistema.delta_condensacao, "temp_condensacao": _temp_condensacao(projeto, sistema),
        "qtd_ventiladores": uc.vent_qtd, "tensao": eletrica.vent_tensao if eletrica else None,
        "corrente_nominal_ventiladores_a": eletrica.vent_corrente_a if eletrica else None,
        "capacidade_condensador_kcal_h": None,  # não captado separadamente do restante da UC ainda
        "folga_tecnica_pct": None,
    }


def _montar_compilacao_geral(db: Session, projeto_id: int):
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        raise HTTPException(404, "Projeto não encontrado")
    # Ordenação canônica: sistemas por nome; colunas de câmara por Sucção › Elétrica.
    sistemas = sorted(db.query(m.SistemaRefrigeracao).filter_by(projeto_id=projeto_id)
                      .options(selectinload(m.SistemaRefrigeracao.camaras_completo).selectinload(m.CamaraCompleto.forcadores),
                               selectinload(m.SistemaRefrigeracao.camaras_completo).selectinload(m.CamaraCompleto.equipamentos),
                               selectinload(m.SistemaRefrigeracao.camaras_completo).selectinload(m.CamaraCompleto.portas),
                               selectinload(m.SistemaRefrigeracao.camaras_simples).selectinload(m.CamaraSimples.forcadores),
                               selectinload(m.SistemaRefrigeracao.expositores).selectinload(m.Expositor.modelo_expositor),
                               selectinload(m.SistemaRefrigeracao.racks))
                      .all(), key=lambda s: chave_ordem_camara(s.nome, "", ""))
    tensao_comando = projeto.tensao_comando

    saida_sistemas = []
    carga_por_sistema = []
    for sistema in sistemas:
        # (câmara, tipo) ordenadas por Sucção › Elétrica antes de virar coluna
        camaras = [(c, "completo") for c in sistema.camaras_completo] + \
                  [(c, "simples") for c in sistema.camaras_simples]
        camaras.sort(key=lambda ct: chave_ordem_camara(sistema.nome, ct[0].linha_succao, ct[0].linha_eletrica))
        camaras_out = []
        for c, tipo in camaras:
            calc = calcular_camara_completo(db, c) if tipo == "completo" else calcular_camara_simples(db, c)
            camaras_out.append({
                "camara_id": c.id, "tipo": tipo, "codigo": None, "nome": c.nome,
                "dados_entrada": _bloco_dados_entrada(c, tipo, projeto),
                "bloco_carga": _bloco_carga(projeto, sistema, c, calc, tipo),
                "memorial": _bloco_memorial(calc, tipo),
                "forcador": _bloco_forcadores(db, c, calc, tensao_comando),
            })
        carga_requerida_sistema = _carga_requerida_sistema(camaras_out)
        # Carga térmica é totalizada POR SISTEMA, nunca somada entre sistemas — cada sistema opera
        # numa temperatura de evaporação diferente, então um total único somando HTA+HTB+LTD+MTC
        # não representa nenhuma grandeza física real (não é a carga de nenhuma máquina).
        carga_por_sistema.append({
            "sistema_id": sistema.id, "sistema_nome": sistema.nome,
            "carga_termica_kcal_h": carga_requerida_sistema,
            "qt_w": round(carga_requerida_sistema / W_PARA_KCAL_H, 1) if carga_requerida_sistema else 0.0,
        })
        saida_sistemas.append({
            "sistema_id": sistema.id, "sistema_nome": sistema.nome,
            "camaras": camaras_out,
            "rack_uc": _bloco_rack_uc(db, sistema, carga_requerida_sistema, camaras_out),
            "condensador": _bloco_condensador(db, sistema),
            "forcadores_total": _forcadores_sistema_total(camaras_out, carga_requerida_sistema),
        })

    return projeto, {
        "sistemas": saida_sistemas,
        "responsabilidade_dados_entrada": projeto.observacao_dados_entrada or RESPONSABILIDADE_DADOS_ENTRADA_PADRAO,
        "totais": {
            "carga_termica_por_sistema": carga_por_sistema,
        },
    }


@router.get("/compilacao-geral")
def compilacao_geral(projeto_id: int, db: Session = Depends(get_db)):
    _projeto, dados = _montar_compilacao_geral(db, projeto_id)
    return dados


@router.get("/compilacao-geral/exportar/excel")
def exportar_compilacao_geral_excel(projeto_id: int, db: Session = Depends(get_db)):
    projeto, dados = _montar_compilacao_geral(db, projeto_id)
    conteudo = gerar_excel_compilacao_geral(projeto, dados)
    return resposta_excel_projeto(conteudo, f"compilacao_geral_{projeto.codigo_projeto or projeto_id}.xlsx", projeto)
