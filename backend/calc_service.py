"""Orquestra os módulos de cálculo (Q1-Q8) lendo as entidades do banco — usado pelos routers
de Câmara Completo e Câmara Simples para devolver o memorial de cálculo completo."""
import json
import re
from contextvars import ContextVar
from sqlalchemy.orm import Session
from . import models as m
from .calculos import camara_completo as cc
from .calculos import camara_simples as cs
from .calculos import infiltracao as inf
from .calculos import forcador as fc
from .calculos import valvula as vl
from .calculos.comum import volume_camara, capacidade_requerida, folga_percentual
from .calculos.clima import resolver_clima_estacao
from .calculos.luminotecnico import calcular_luminotecnico
from . import campo_catalogo as cpc
from . import calc_remoto_client as _remoto

_token_usuario: ContextVar[str | None] = ContextVar("_token_usuario", default=None)


def definir_token_usuario(token: str | None):
    _token_usuario.set(token)
from . import id_comercial as idc


def _extrair_potencia_w(texto):
    """Extrai o número de watts do texto exato do nó da árvore (ex.: "36W" -> 36.0)."""
    if not texto:
        return None
    match = re.search(r"[\d.,]+", texto)
    if not match:
        return None
    return float(match.group(0).replace(",", "."))


def _lampada_por_potencia_texto(db: Session, potencia_luminaria_texto):
    """Busca em "Cadastro Lâmpadas" (Configurações) o registro cuja Potência (W) bate com o número
    extraído do texto de Potência escolhido na árvore (ex.: "36W" -> 36)."""
    potencia_w = _extrair_potencia_w(potencia_luminaria_texto)
    if potencia_w is None:
        return None
    return db.query(m.LookupLampada).filter_by(potencia_w=potencia_w).first()


def _calc_luminotecnico_camara(db: Session, camara):
    """Bloco informativo do Estudo Luminotécnico (Tela 11) — só quando Tipo Ambiente + Potência
    Luminária estão escolhidos. Nunca influencia o Q6/carga térmica (ver calor_iluminacao acima)."""
    if not (camara.tipo_ambiente_lumino_id and camara.potencia_luminaria_texto):
        return None
    ambiente = camara.tipo_ambiente_lumino
    lampada = _lampada_por_potencia_texto(db, camara.potencia_luminaria_texto)
    if not lampada:
        return None
    return calcular_luminotecnico(getattr(camara, "largura", None), getattr(camara, "comprimento", None),
                                   camara.pedireito, camara.qtd_luminarias or 0,
                                   ambiente.lux_recomendado, lampada.potencia_w, lampada.fluxo_lumens)


def _config(db: Session, chave: str, default=None):
    cfg = db.query(m.ConfiguracaoGlobal).filter_by(chave=chave).first()
    return cfg.valor if cfg else default


def _modelo_comercial_forcador(db, linha_id, modelo, tipo_degelo, tensao_comando, nomenclatura_selecionada,
                                dados_modelo=None):
    """Código comercial (de compra) do forçador — mesma composição do painel de nomenclatura da câmara
    (componentes.js) e do "Modelo EVP" da Tela 8: motor genérico de Campos (campo_catalogo.montar_codigo),
    campo de degelo Automático substituindo o coringa '*'/'x', tensão = Tensão de Comando do projeto.
    dados_modelo: dados técnicos do modelo escolhido no catálogo (fpi, num_ventiladores,
    diametro_ventilador_mm) — fonte pros Campos em modo Automático ligados a essas colunas. Convertidos
    pra string aqui porque CampoCatalogoOpcao.valor é String e a comparação é exata (ver campo_catalogo.py)."""
    if not modelo:
        return None
    modelo_base = re.sub(r"[x]", "*", modelo, count=1)  # coringa 'x' vira '*', que montar_codigo troca
    dados_modelo = dados_modelo or {}
    contexto = {"tipo_degelo": tipo_degelo, "tensao_comando": tensao_comando}
    for chave in ("fpi", "num_ventiladores", "diametro_ventilador_mm"):
        valor = dados_modelo.get(chave)
        if valor is not None:
            contexto[chave] = str(valor)
    return cpc.montar_codigo(db, "Forcador", linha_id, modelo_base=modelo_base,
                             contexto=contexto, selecoes_manuais=nomenclatura_selecionada or {})


def _valvulas_do_forcador(db, row, coletores_por_forcador: int, cap_req_kcal_h=None, sistema=None,
                          modelos_cadastrados=None) -> list:
    """Válvulas de expansão vinculadas a essa opção de forçador. O modelo/capacidade não vêm de
    catálogo interno — o dimensionamento é feito no app do próprio fabricante (Coolselector2/
    VEE Selector/CPQ) e o resultado é digitado/importado direto na seleção (a mecânica pode ser
    completada pela Tela A - Tabelas de Válvulas de Expansão).

    Fabricante/Tipo de Expansão SEMPRE seguem a configuração ATUAL do Sistema (Tela 1 §3) — o valor
    gravado na linha é só um snapshot do provisionamento e fica como fallback. Sem isso, mudar o
    sistema na Tela 1 (ou mover a câmara de sistema) deixava o layout num tipo e o dropdown de
    modelos em outro (bug real: layout Eletrônica exibindo modelo Termostático TEN2)."""
    qtd_valv = vl.qtd_valvulas(row.quantidade or 1, coletores_por_forcador)
    fab_atual = (sistema.fabricante_valvula if sistema else None)
    # tipo_expansao do Sistema é o CÓDIGO da árvore (aprovado 2026-08-08) — resolve pro nome atual
    # aqui, na hora de exibir/repassar, pra manter o texto idêntico ao que já aparecia antes.
    tipo_atual = idc.nome_por_codigo(db, sistema.tipo_expansao) if sistema and sistema.tipo_expansao else None
    out = []
    for v in row.valvulas:
        # Abert. Válv. = (Carga Térmica ÷ Qtd. Coletores) ÷ Capacidade Unit., em % — fórmula
        # definida pelo usuário. Qtd. Coletores = qtd. forçadores × coletores/forçador (mesma
        # conta de qtd_valvulas: 1 válvula por coletor). Sem capacidade digitada/importada, cai
        # no valor gravado (importações antigas traziam a % pronta do relatório).
        abert = None
        if cap_req_kcal_h and v.capacidade_unit_kcal_h and qtd_valv:
            abert = round((cap_req_kcal_h / qtd_valv) / v.capacidade_unit_kcal_h * 100, 1)
        out.append({"id": v.id, "fabricante": fab_atual or v.fabricante,
                    "tipo_expansao": tipo_atual or v.tipo_expansao,
                    "modelo_selecao": v.modelo_selecao,
                    # Modelo gravado (importado/manual) que não existe na Tela A - Tabelas de
                    # Válvulas de Expansão — o frontend avisa: "Válvula não cadastrada no sistema."
                    "modelo_nao_cadastrado": bool(v.modelo_selecao) and modelos_cadastrados is not None
                                              and v.modelo_selecao not in modelos_cadastrados,
                    "carga_abertura_pct": abert if abert is not None else v.carga_abertura_pct,
                    "conexao_entrada": v.conexao_entrada, "conexao_saida": v.conexao_saida,
                    "folga_desejada": v.folga_desejada, "considerado": v.considerado, "quantidade": qtd_valv,
                    "capacidade_unit_kcal_h": v.capacidade_unit_kcal_h, "orificio": v.orificio,
                    "tensao": v.tensao, "tipo_motor": v.tipo_motor, "controlador": v.controlador})
    return out


def _modelo_para_calculo(modelo: m.ModeloForcador) -> dict:
    return {
        "id": modelo.id,
        "modelo": modelo.modelo,
        "dt_referencia": modelo.dt_referencia_c,
        "capacidades": [(c.temp_evaporacao_c, c.capacidade_kcal_h) for c in modelo.capacidades],
        "vazao_ar_m3h": modelo.vazao_ar_m3h,
        "fpi": modelo.fpi,
        "flecha_ar_m": modelo.flecha_ar_m,
        "altura_max_instalacao_m": modelo.altura_max_instalacao_m,
        "pdl_referencia_m": modelo.pdl_referencia_m,
        "coletores_por_forcador": modelo.coletores_por_forcador or 1,
        "tipo_degelo": modelo.tipo_degelo,
        "carga_gas_kg": modelo.carga_gas_kg,
        "pot_resistencia_degelo_w": modelo.pot_resistencia_degelo_w,
        "diametro_ventilador_mm": modelo.diametro_ventilador_mm,
        "num_ventiladores": modelo.num_ventiladores,
        "motores_w": modelo.eletricas[0].motores_w if modelo.eletricas else None,
    }


# ---- Fase 3 (split projeto local / catálogo remoto) — Etapa 1 ----
# `_serializar_camara_completo`: só lê dado de PROJETO (câmara/sistema/projeto), zero consulta a
# catálogo — é o que o app local vai enviar pro servidor remoto no futuro (payload serializável).
# `calcular_camara_completo_de_dados`: mesma lógica de `calcular_camara_completo`, mas lendo do
# dict serializado em vez de navegar relationships do ORM ligado ao projeto — só toca `db` pra
# resolver catálogo (produto, isolamento, forçador, válvula, etc.), nunca dado de projeto.
# Construídas AO LADO da função original (que continua em uso) até prova de equivalência total.
def _serializar_camara_completo(camara: m.CamaraCompleto) -> dict:
    sistema = camara.sistema
    projeto = sistema.projeto if sistema else None
    return {
        "sistema_id": camara.sistema_id,
        "linha_succao": camara.linha_succao, "linha_eletrica": camara.linha_eletrica,
        "temp_interna": camara.temp_interna, "largura": camara.largura,
        "comprimento": camara.comprimento, "pedireito": camara.pedireito,
        "utilizar_valv_reg_pressao": camara.utilizar_valv_reg_pressao,
        "dt_evaporacao_desejado": camara.dt_evaporacao_desejado,
        "produto_id": camara.produto_id, "qtd_estocada": camara.qtd_estocada,
        "mov_diaria": camara.mov_diaria, "tempo_processo": camara.tempo_processo,
        "temp_entrada": camara.temp_entrada, "temp_saida": camara.temp_saida,
        "tipo_embalagem_id": camara.tipo_embalagem_id, "massa_embalagem": camara.massa_embalagem,
        "isolamento_parede_id": camara.isolamento_parede_id, "isolamento_teto_id": camara.isolamento_teto_id,
        "isolamento_piso_id": camara.isolamento_piso_id,
        "fonte_ar": camara.fonte_ar, "temp_adjacente": camara.temp_adjacente,
        "umidade_adjacente": camara.umidade_adjacente,
        "num_pessoas": camara.num_pessoas, "tempo_pessoas": camara.tempo_pessoas,
        "qtd_luminarias": camara.qtd_luminarias, "potencia_luminaria": camara.potencia_luminaria,
        "horas_iluminacao_carga": camara.horas_iluminacao_carga,
        "tipo_ambiente_lumino_id": camara.tipo_ambiente_lumino_id,
        "potencia_luminaria_texto": camara.potencia_luminaria_texto,
        "fator_seguranca": camara.fator_seguranca, "tempo_func_compressores": camara.tempo_func_compressores,
        "portas": [{"quantidade": p.quantidade, "largura": p.largura, "altura": p.altura,
                     "freq_abertura_min_h": p.freq_abertura_min_h, "protecao": p.protecao,
                     "fonte_ar": p.fonte_ar, "temp_adjacente": p.temp_adjacente,
                     "umidade_adjacente": p.umidade_adjacente} for p in camara.portas],
        "equipamentos": [{"tipo_equipamento_id": e.tipo_equipamento_id, "qtd": e.qtd, "tempo": e.tempo}
                          for e in camara.equipamentos],
        "forcadores": [{"id": row.id, "fabricante_id": row.fabricante_id, "linha_id": row.linha_id,
                          "folga_desejada": row.folga_desejada, "considerado": row.considerado,
                          "quantidade": row.quantidade, "tipo_degelo": row.tipo_degelo,
                          "codigo_curto": row.codigo_curto,
                          "nomenclatura_selecionada": row.nomenclatura_selecionada,
                          "valvulas": [{"id": v.id, "fabricante": v.fabricante, "tipo_expansao": v.tipo_expansao,
                                         "modelo_selecao": v.modelo_selecao, "carga_abertura_pct": v.carga_abertura_pct,
                                         "conexao_entrada": v.conexao_entrada, "conexao_saida": v.conexao_saida,
                                         "folga_desejada": v.folga_desejada, "considerado": v.considerado,
                                         "capacidade_unit_kcal_h": v.capacidade_unit_kcal_h, "orificio": v.orificio,
                                         "tensao": v.tensao, "tipo_motor": v.tipo_motor,
                                         "controlador": v.controlador} for v in row.valvulas]}
                         for row in camara.forcadores],
        # Sistema/Projeto — sempre dado de projeto, nunca catálogo.
        "sistema_gas_refrigerante": sistema.gas_refrigerante if sistema else None,
        "sistema_temp_evaporacao": sistema.temp_evaporacao if sistema else None,
        "sistema_delta_condensacao": sistema.delta_condensacao if sistema else None,
        "sistema_fabricante_valvula": sistema.fabricante_valvula if sistema else None,
        "sistema_tipo_expansao": sistema.tipo_expansao if sistema else None,
        "projeto_temp_ambiente": projeto.temp_ambiente if projeto else None,
        "projeto_ur_externa": projeto.ur_externa if projeto else None,
        "projeto_altitude_m": projeto.altitude_m if projeto else None,
        "projeto_tensao_comando": projeto.tensao_comando if projeto else None,
        "projeto_tensao_equipamentos": projeto.tensao_equipamentos if projeto else None,
        "projeto_estacao_climatologica": projeto.estacao_climatologica if projeto else None,
        "projeto_criterio_climatico": projeto.criterio_climatico if projeto else None,
    }


def calcular_camara_completo_de_dados(db: Session, dados: dict) -> dict:
    modelos_valvula_cadastrados = {r[0] for r in db.query(m.TabelaValvulaExpansao.modelo).all()}
    volume = volume_camara(dados["largura"], dados["comprimento"], dados["pedireito"])

    if dados["fonte_ar"] == "Adjacente":
        temp_fonte = dados["temp_adjacente"] if dados["temp_adjacente"] is not None else 25
        ur_fonte = dados["umidade_adjacente"] if dados["umidade_adjacente"] is not None else 60
    else:
        temp_fonte = dados["projeto_temp_ambiente"] or 0
        ur_fonte = dados["projeto_ur_externa"] or 60
    altitude_m = dados["projeto_altitude_m"] or 0

    produto = db.get(m.Produto, dados["produto_id"]) if dados["produto_id"] else None
    tipo_embalagem = db.get(m.TipoEmbalagem, dados["tipo_embalagem_id"]) if dados["tipo_embalagem_id"] else None
    isolamento_parede = db.get(m.IsolamentoParedeTeto, dados["isolamento_parede_id"]) if dados["isolamento_parede_id"] else None
    isolamento_teto = db.get(m.IsolamentoParedeTeto, dados["isolamento_teto_id"]) if dados["isolamento_teto_id"] else None
    isolamento_piso = db.get(m.IsolamentoPiso, dados["isolamento_piso_id"]) if dados["isolamento_piso_id"] else None

    # ---- Q1 Produto ----
    q1 = 0.0
    if produto:
        q1 = cc.calor_produto(dados["mov_diaria"] or 0, dados["qtd_estocada"] or 0, produto.calor_esp_antes,
                               produto.calor_esp_depois, produto.calor_latente, produto.calor_respiracao,
                               dados["temp_entrada"] or 0, dados["temp_saida"] or 0, produto.ponto_congelamento)

    # ---- Q2 Embalagem ----
    q2 = 0.0
    if tipo_embalagem:
        q2 = cc.calor_embalagem(dados["massa_embalagem"] or 0, tipo_embalagem.calor_especifico,
                                 dados["temp_entrada"] or 0, dados["temp_saida"] or 0)

    # ---- Q3 Penetração ----
    q3, areas = 0.0, {}
    bulbo_umido = None
    if dados["projeto_estacao_climatologica"]:
        _, bulbo_umido, _ = resolver_clima_estacao(dados["projeto_estacao_climatologica"], dados["projeto_criterio_climatico"] or "pico_sazonal")
    fatores_insolacao_cadastrados = [f.fator for f in db.query(m.FatorInsolacao).all()]
    fator_insolacao = (sum(fatores_insolacao_cadastrados) / len(fatores_insolacao_cadastrados)
                        if fatores_insolacao_cadastrados else 1.10)
    if dados["largura"] and dados["comprimento"] and dados["pedireito"]:
        u_parede = isolamento_parede.u_valor if isolamento_parede else 0
        u_teto = isolamento_teto.u_valor if isolamento_teto else 0
        u_piso = isolamento_piso.u_valor if isolamento_piso else 0
        q3, areas = cc.calor_penetracao(u_parede, u_teto, u_piso, dados["largura"], dados["comprimento"],
                                         dados["pedireito"], temp_fonte,
                                         dados["temp_interna"] or 0, bulbo_umido, fator_insolacao)

    # ---- Q4 Infiltração ----
    ur_int = 95
    classe_produto = None
    if produto and produto.classe:
        classe_produto = db.query(m.ClasseProduto).filter_by(classe=produto.classe).first()
        if classe_produto and classe_produto.ur_min and classe_produto.ur_max:
            ur_int = (classe_produto.ur_min + classe_produto.ur_max) / 2
    q4 = 0.0
    for porta in dados["portas"]:
        if porta["fonte_ar"] == "Adjacente":
            t_porta = porta["temp_adjacente"] if porta["temp_adjacente"] is not None else 25
            ur_porta = porta["umidade_adjacente"] if porta["umidade_adjacente"] is not None else 60
        else:
            t_porta = dados["projeto_temp_ambiente"] or 0
            ur_porta = dados["projeto_ur_externa"] or 60
        q4 += inf.calor_infiltracao(porta["quantidade"] or 1, porta["largura"], porta["altura"],
                                     porta["freq_abertura_min_h"], porta["protecao"],
                                     t_porta, dados["temp_interna"] or 0, ur_int, ur_porta, altitude_m)

    # ---- Q5 Pessoas ----
    q5 = cc.calor_pessoas(dados["num_pessoas"] or 0, dados["tempo_pessoas"] or 0, dados["temp_interna"] or 0)

    # ---- Q6 Iluminação ----
    horas_ilum = dados["horas_iluminacao_carga"] if dados["horas_iluminacao_carga"] is not None else 24
    potencia_unit_ilum = _extrair_potencia_w(dados["potencia_luminaria_texto"])
    if potencia_unit_ilum is None:
        potencia_unit_ilum = dados["potencia_luminaria"] or 0
    q6, potencia_total_ilum = cc.calor_iluminacao(dados["qtd_luminarias"] or 0, potencia_unit_ilum, horas_ilum)

    # ---- Q7 Equipamentos ----
    itens_equip = []
    for e in dados["equipamentos"]:
        te = db.get(m.TipoEquipamento, e["tipo_equipamento_id"])
        if te:
            itens_equip.append({"potencia_tipica_w": te.potencia_tipica_w,
                                 "fator_calor_rejeitado": te.fator_calor_rejeitado,
                                 "fator_simultaneidade": te.fator_simultaneidade,
                                 "qtd": e["qtd"], "tempo": e["tempo"]})
    q7 = cc.calor_equipamentos(itens_equip)

    q8 = 0.0
    carga_total_24h = q1 + q2 + q3 + q4 + q5 + q6 + q7
    cap_req = capacidade_requerida(carga_total_24h, dados["fator_seguranca"], dados["tempo_func_compressores"])
    cap_req_unitaria = cap_req

    dt_camara_real = (dados["temp_interna"] or 0) - (dados["sistema_temp_evaporacao"] or 0)
    obs_valv_reg = None
    if dados["utilizar_valv_reg_pressao"] == "Sim" and dados["dt_evaporacao_desejado"]:
        dt_camara = dados["dt_evaporacao_desejado"]
        temp_evap = (dados["temp_interna"] or 0) - dados["dt_evaporacao_desejado"]
        obs_valv_reg = ("Temperatura de Saturação controlada. Considerada Temperatura de Evaporação "
                         f"{temp_evap:.1f}°C e Dt Evaporação {dt_camara:.1f}°C.")
    else:
        dt_camara = dt_camara_real
        temp_evap = dados["sistema_temp_evaporacao"]

    alertas = []
    forcadores_out = []
    linha_considerada_modelo = None
    _valv_refs = []
    carga_base_24h = carga_total_24h

    for row in dados["forcadores"]:
        qtd = row["quantidade"] or 1
        linha = db.get(m.LinhaForcador, row["linha_id"]) if row["linha_id"] else None
        fabricante = db.get(m.Fabricante, row["fabricante_id"]) if row["fabricante_id"] else None
        if linha is None:
            alertas.append("Catálogo do forçador (linha_id %s) não foi encontrado — provavelmente excluído. "
                            "Refaça a seleção do forçador nesta câmara." % row["linha_id"])
            item0 = {"id": row["id"], "fabricante": fabricante.nome if fabricante else None,
                      "linha": None, "linha_id": row["linha_id"], "erro_catalogo_ausente": True,
                      "folga_desejada": row["folga_desejada"], "considerado": row["considerado"],
                      "quantidade": qtd, "tipo_degelo_selecionado": row["tipo_degelo"],
                      "codigo_curto": row["codigo_curto"],
                      "valvulas": _valvulas_do_forcador_dados(row["valvulas"], row["quantidade"], 1, cap_req,
                          dados["sistema_fabricante_valvula"],
                          idc.nome_por_codigo(db, dados["sistema_tipo_expansao"]) if dados["sistema_tipo_expansao"] else None,
                          modelos_valvula_cadastrados)}
            forcadores_out.append(item0)
            _valv_refs.append((item0, row, 1))
            continue
        modelos_calc = [_modelo_para_calculo(md) for md in linha.modelos]
        fator_gas_obj = None
        if dados["sistema_gas_refrigerante"]:
            fator_gas_obj = (db.query(m.FatorCorrecaoGasForcador)
                              .filter_by(linha_id=row["linha_id"], gas=dados["sistema_gas_refrigerante"]).first())
        fatores = [fator_gas_obj.fator] if fator_gas_obj and fator_gas_obj.fator else None
        item = {"id": row["id"], "fabricante": fabricante.nome if fabricante else None, "linha": linha.nome,
                "linha_id": row["linha_id"],
                "folga_desejada": row["folga_desejada"], "considerado": row["considerado"],
                "quantidade": qtd, "tipo_degelo_selecionado": row["tipo_degelo"],
                "nomenclatura_selecionada": json.loads(row["nomenclatura_selecionada"]) if row["nomenclatura_selecionada"] else {},
                "fator_gas_aplicado": fator_gas_obj.fator if fator_gas_obj else None,
                "fator_gas_pendente": bool(dados["sistema_gas_refrigerante"] and not (fator_gas_obj and fator_gas_obj.fator is not None)),
                "tensao_comando": dados["projeto_tensao_comando"],
                "tensao_equipamentos": dados["projeto_tensao_equipamentos"],
                "gas": dados["sistema_gas_refrigerante"],
                "observacao_valv_reg_pressao": obs_valv_reg}
        escolhido = fc.selecionar_modelo_autoconsistente(
            modelos_calc, temp_evap, dt_camara, qtd, carga_base_24h,
            dados["fator_seguranca"], dados["tempo_func_compressores"],
            row["folga_desejada"], fatores_correcao=fatores)
        if escolhido:
            trocas = fc.trocas_de_ar(escolhido["vazao_ar_m3h"], qtd, volume)
            item.update({
                "modelo_resultante": escolhido["modelo"],
                "modelo_comercial": _modelo_comercial_forcador(db, row["linha_id"], escolhido["modelo"],
                    row["tipo_degelo"], dados["projeto_tensao_comando"], item["nomenclatura_selecionada"],
                    dados_modelo={"fpi": escolhido.get("fpi"), "num_ventiladores": escolhido.get("num_ventiladores"),
                                  "diametro_ventilador_mm": escolhido.get("diametro_ventilador_mm")}),
                "capacidade_tabelada_kcal_h": round(fc.interpolar_capacidade(escolhido["capacidades"], temp_evap), 1) if temp_evap is not None else None,
                "capacidade_corrigida_unitaria": round(escolhido["capacidade_corrigida"], 1),
                "capacidade_instalada_total": round(escolhido["capacidade_corrigida"] * qtd, 1),
                "folga_real": round(escolhido["folga_real"], 1),
                "trocas_de_ar": round(trocas, 1) if trocas else None,
                "vazao_ar_m3h": escolhido["vazao_ar_m3h"], "tipo_degelo_catalogo": escolhido["tipo_degelo"],
                "tipo_degelo_opcoes_comerciais": cpc.opcoes_automatico(db, "Forcador", row["linha_id"], "tipo_degelo"),
                "carga_gas_kg": escolhido["carga_gas_kg"], "pot_resistencia_degelo_w": escolhido["pot_resistencia_degelo_w"],
                "diametro_ventilador_mm": escolhido["diametro_ventilador_mm"], "flecha_ar_m": escolhido["flecha_ar_m"],
                "altura_max_instalacao_m": escolhido["altura_max_instalacao_m"],
                "pdl_referencia_m": escolhido["pdl_referencia_m"], "num_ventiladores": escolhido["num_ventiladores"],
                "fpi": escolhido["fpi"],
                "coletores_por_forcador": escolhido["coletores_por_forcador"],
            })
            if escolhido["flecha_ar_m"] and (dados["comprimento"] or 0) > escolhido["flecha_ar_m"]:
                alertas.append("Flecha de ar do forçador (%.1fm) insuficiente para o comprimento da câmara (%.1fm) — linha %s" % (
                    escolhido["flecha_ar_m"], dados["comprimento"] or 0, linha.nome))
            if escolhido["altura_max_instalacao_m"] and dados["pedireito"] and dados["pedireito"] > escolhido["altura_max_instalacao_m"]:
                alertas.append("Altura de instalação incompatível com o pé-direito (linha %s)" % linha.nome)
            if escolhido["pdl_referencia_m"] and dados["pedireito"] and dados["pedireito"] > escolhido["pdl_referencia_m"]:
                alertas.append("Pé-direito da câmara (%.2fm) acima do PDL Máximo do catálogo (%.2fm) — linha %s" % (
                    dados["pedireito"], escolhido["pdl_referencia_m"], linha.nome))
            if trocas and (trocas < 30 or trocas > 60):
                alertas.append("Trocas de ar/hora fora da faixa recomendada (30-60/h) na linha %s" % linha.nome)
            if item["fator_gas_pendente"]:
                alertas.append("Fator de correção do gás %s ainda não preenchido para a linha %s — capacidade corrigida sem esse ajuste" % (dados["sistema_gas_refrigerante"], linha.nome))
            if escolhido["folga_real"] < row["folga_desejada"]:
                alertas.append("Folga insuficiente na linha %s: mesmo o maior modelo disponível (%dx %s) só atinge %.1f%% de folga (desejado %.0f%%) — aumente a quantidade" % (
                    linha.nome, qtd, escolhido["modelo"], escolhido["folga_real"], row["folga_desejada"]))
            if row["considerado"]:
                linha_considerada_modelo = escolhido
        item["codigo_curto"] = row["codigo_curto"]
        tipo_expansao_nome = idc.nome_por_codigo(db, dados["sistema_tipo_expansao"]) if dados["sistema_tipo_expansao"] else None
        item["valvulas"] = _valvulas_do_forcador_dados(row["valvulas"], row["quantidade"],
            escolhido["coletores_por_forcador"] if escolhido else 1, cap_req,
            dados["sistema_fabricante_valvula"], tipo_expansao_nome, modelos_valvula_cadastrados)
        _valv_refs.append((item, row, escolhido["coletores_por_forcador"] if escolhido else 1))
        forcadores_out.append(item)

    if linha_considerada_modelo is not None:
        q8 = linha_considerada_modelo["q8_candidato"]
        carga_total_24h = carga_base_24h + q8
        cap_req = linha_considerada_modelo["capacidade_requerida_candidato"]
        cap_req_unitaria = cap_req
        tipo_expansao_nome = idc.nome_por_codigo(db, dados["sistema_tipo_expansao"]) if dados["sistema_tipo_expansao"] else None
        for _item, _row, _colet in _valv_refs:
            _item["valvulas"] = _valvulas_do_forcador_dados(_row["valvulas"], _row["quantidade"], _colet, cap_req,
                dados["sistema_fabricante_valvula"], tipo_expansao_nome, modelos_valvula_cadastrados)

    if produto and produto.classe and dt_camara is not None:
        classe = classe_produto or db.query(m.ClasseProduto).filter_by(classe=produto.classe).first()
        if classe and not (classe.dt_evap_min <= abs(dt_camara) <= classe.dt_evap_max):
            alertas.append("Umidade relativa pode ser incompatível com a Classe %s do produto (ΔT esperado %.0f-%.0f°C)"
                            % (classe.classe, classe.dt_evap_min, classe.dt_evap_max))
    if dados["temp_interna"] is not None and dados["temp_interna"] < 0 and isolamento_piso \
            and "concreto" in (isolamento_piso.material or "").lower():
        alertas.append("Piso em concreto não é recomendado para temperatura interna negativa")
    if volume and dados["pedireito"] and dados["pedireito"] > 10 and volume > 5000 and (dados["temp_interna"] or 0) < 0:
        alertas.append("Sugestão automática: considerar ventilação de piso (pé-direito>10m, volume>5.000m³, T<0°C)")

    return {
        "q1_produto": round(q1, 1), "q2_embalagem": round(q2, 1), "q3_penetracao": round(q3, 1),
        "q4_infiltracao": round(q4, 1), "q5_pessoas": round(q5, 1), "q6_iluminacao": round(q6, 1),
        "q7_equipamentos": round(q7, 1), "q8_forcadores": round(q8, 1), "carga_termica_total_24h": round(carga_total_24h, 1),
        "capacidade_requerida": round(cap_req, 1), "capacidade_requerida_unitaria": round(cap_req_unitaria, 1),
        "potencia_total_iluminacao_w": potencia_total_ilum,
        "luminotecnico": _calc_luminotecnico_camara_dados(db, dados),
        "areas": areas, "dt_camara": dt_camara,
        "dt_camara_real": round(dt_camara_real, 1) if dt_camara_real is not None else None,
        "temp_evaporacao_sistema": dados["sistema_temp_evaporacao"],
        "temp_condensacao": round(dados["projeto_temp_ambiente"] + dados["sistema_delta_condensacao"], 1)
            if (dados["projeto_temp_ambiente"] is not None and dados["sistema_delta_condensacao"] is not None) else None,
        "volume_m3": volume, "forcadores": forcadores_out, "alertas": alertas,
    }


def _valvulas_do_forcador_dados(valvulas: list, quantidade, coletores_por_forcador: int, cap_req_kcal_h,
                                 fab_atual, tipo_atual, modelos_cadastrados) -> list:
    """Igual a `_valvulas_do_forcador`, lendo de dict em vez de ORM ligado ao projeto."""
    qtd_valv = vl.qtd_valvulas(quantidade or 1, coletores_por_forcador)
    out = []
    for v in valvulas:
        abert = None
        if cap_req_kcal_h and v["capacidade_unit_kcal_h"] and qtd_valv:
            abert = round((cap_req_kcal_h / qtd_valv) / v["capacidade_unit_kcal_h"] * 100, 1)
        out.append({"id": v["id"], "fabricante": fab_atual or v["fabricante"],
                    "tipo_expansao": tipo_atual or v["tipo_expansao"],
                    "modelo_selecao": v["modelo_selecao"],
                    "modelo_nao_cadastrado": bool(v["modelo_selecao"]) and modelos_cadastrados is not None
                                              and v["modelo_selecao"] not in modelos_cadastrados,
                    "carga_abertura_pct": abert if abert is not None else v["carga_abertura_pct"],
                    "conexao_entrada": v["conexao_entrada"], "conexao_saida": v["conexao_saida"],
                    "folga_desejada": v["folga_desejada"], "considerado": v["considerado"], "quantidade": qtd_valv,
                    "capacidade_unit_kcal_h": v["capacidade_unit_kcal_h"], "orificio": v["orificio"],
                    "tensao": v["tensao"], "tipo_motor": v["tipo_motor"], "controlador": v["controlador"]})
    return out


def _calc_luminotecnico_camara_dados(db: Session, dados: dict):
    if not (dados["tipo_ambiente_lumino_id"] and dados["potencia_luminaria_texto"]):
        return None
    ambiente = db.get(m.LookupAmbienteLuminotecnico, dados["tipo_ambiente_lumino_id"])
    if not ambiente:
        return None
    lampada = _lampada_por_potencia_texto(db, dados["potencia_luminaria_texto"])
    if not lampada:
        return None
    return calcular_luminotecnico(dados["largura"], dados["comprimento"],
                                   dados["pedireito"], dados["qtd_luminarias"] or 0,
                                   ambiente.lux_recomendado, lampada.potencia_w, lampada.fluxo_lumens)


def calcular_camara_completo(db: Session, camara: m.CamaraCompleto) -> dict:
    sistema = camara.sistema
    modelos_valvula_cadastrados = {r[0] for r in db.query(m.TabelaValvulaExpansao.modelo).all()}
    projeto = sistema.projeto if sistema else None
    volume = volume_camara(camara.largura, camara.comprimento, camara.pedireito)

    # Fonte do ar que troca com a câmara (paredes/teto na penetração Q3 e ar de infiltração Q4).
    # "Adjacente" usa a temperatura/UR do ambiente vizinho informado na própria câmara; senão,
    # usa o ar externo do projeto. O piso (Q3) nunca usa essa fonte — troca com o solo (bulbo
    # úmido externo), tratado à parte.
    if camara.fonte_ar == "Adjacente":
        temp_fonte = camara.temp_adjacente if camara.temp_adjacente is not None else 25
        ur_fonte = camara.umidade_adjacente if camara.umidade_adjacente is not None else 60
    else:
        temp_fonte = (projeto.temp_ambiente if projeto else 0) or 0
        ur_fonte = (projeto.ur_externa if projeto else None) or 60
    altitude_m = (projeto.altitude_m if projeto else 0) or 0

    # ---- Q1 Produto ----
    q1 = 0.0
    if camara.produto:
        p = camara.produto
        q1 = cc.calor_produto(camara.mov_diaria or 0, camara.qtd_estocada or 0, p.calor_esp_antes,
                               p.calor_esp_depois, p.calor_latente, p.calor_respiracao,
                               camara.temp_entrada or 0, camara.temp_saida or 0, p.ponto_congelamento)

    # ---- Q2 Embalagem ----
    q2 = 0.0
    if camara.tipo_embalagem:
        q2 = cc.calor_embalagem(camara.massa_embalagem or 0, camara.tipo_embalagem.calor_especifico,
                                 camara.temp_entrada or 0, camara.temp_saida or 0)

    # ---- Q3 Penetração ----
    q3, areas = 0.0, {}
    bulbo_umido = None
    if projeto and projeto.estacao_climatologica:
        _, bulbo_umido, _ = resolver_clima_estacao(projeto.estacao_climatologica, projeto.criterio_climatico or "pico_sazonal")
    fatores_insolacao_cadastrados = [f.fator for f in db.query(m.FatorInsolacao).all()]
    fator_insolacao = (sum(fatores_insolacao_cadastrados) / len(fatores_insolacao_cadastrados)
                        if fatores_insolacao_cadastrados else 1.10)
    if camara.largura and camara.comprimento and camara.pedireito:
        u_parede = camara.isolamento_parede.u_valor if camara.isolamento_parede else 0
        u_teto = camara.isolamento_teto.u_valor if camara.isolamento_teto else 0
        u_piso = camara.isolamento_piso.u_valor if camara.isolamento_piso else 0
        q3, areas = cc.calor_penetracao(u_parede, u_teto, u_piso, camara.largura, camara.comprimento,
                                         camara.pedireito, temp_fonte,
                                         camara.temp_interna or 0, bulbo_umido, fator_insolacao)

    # ---- Q4 Infiltração — soma de TODAS as portas; cada porta tem sua própria fonte de ar
    # (uma pode dar para fora, outra para o galpão interno). ----
    ur_int = 95
    if camara.produto and camara.produto.classe:
        classe_produto = db.query(m.ClasseProduto).filter_by(classe=camara.produto.classe).first()
        if classe_produto and classe_produto.ur_min and classe_produto.ur_max:
            ur_int = (classe_produto.ur_min + classe_produto.ur_max) / 2
    q4 = 0.0
    for porta in camara.portas:
        if porta.fonte_ar == "Adjacente":
            t_porta = porta.temp_adjacente if porta.temp_adjacente is not None else 25
            ur_porta = porta.umidade_adjacente if porta.umidade_adjacente is not None else 60
        else:
            t_porta = (projeto.temp_ambiente if projeto else 0) or 0
            ur_porta = (projeto.ur_externa if projeto else None) or 60
        q4 += inf.calor_infiltracao(porta.quantidade or 1, porta.largura, porta.altura,
                                     porta.freq_abertura_min_h, porta.protecao,
                                     t_porta, camara.temp_interna or 0, ur_int, ur_porta, altitude_m)

    # ---- Q5 Pessoas ----
    q5 = cc.calor_pessoas(camara.num_pessoas or 0, camara.tempo_pessoas or 0, camara.temp_interna or 0)

    # ---- Q6 Iluminação ---- (horas/dia por câmara, default 24). Fórmula NUNCA muda (Qtd x
    # Potência x Horas) — só a ORIGEM da Potência muda: se a câmara tem Potência/Luminária escolhida
    # na árvore (Estudo Luminotécnico, aprovado 2026-08-08), usa a potência extraída do texto; senão
    # cai no potencia_luminaria antigo (legado, câmara cadastrada antes do Estudo — nunca sobrescrito
    # automaticamente, só muda se o usuário escolher uma Potência manualmente).
    horas_ilum = camara.horas_iluminacao_carga if camara.horas_iluminacao_carga is not None else 24
    potencia_unit_ilum = _extrair_potencia_w(camara.potencia_luminaria_texto)
    if potencia_unit_ilum is None:
        potencia_unit_ilum = camara.potencia_luminaria or 0
    q6, potencia_total_ilum = cc.calor_iluminacao(camara.qtd_luminarias or 0, potencia_unit_ilum, horas_ilum)

    # ---- Q7 Equipamentos ----
    itens_equip = [{"potencia_tipica_w": e.tipo_equipamento.potencia_tipica_w,
                    "fator_calor_rejeitado": e.tipo_equipamento.fator_calor_rejeitado,
                    "fator_simultaneidade": e.tipo_equipamento.fator_simultaneidade,
                    "qtd": e.qtd, "tempo": e.tempo}
                   for e in camara.equipamentos]
    q7 = cc.calor_equipamentos(itens_equip)

    # ---- Q8 Forçadores — calculado depois da seleção da linha considerada (ver abaixo) ----
    q8 = 0.0

    carga_total_24h = q1 + q2 + q3 + q4 + q5 + q6 + q7
    cap_req = capacidade_requerida(carga_total_24h, camara.fator_seguranca, camara.tempo_func_compressores)
    # Sem divisão por "quantidade de evaporadores" da câmara — cada linha de forçador tem sua
    # própria "Quantidade" (nº de unidades daquele modelo), e é só por ela que se divide.
    cap_req_unitaria = cap_req

    # Válvula Reguladora de Pressão (Temperatura de Saturação controlada) — só pra ESSA câmara:
    # troca a Temp. Evaporação e o Δt usados no dimensionamento do forçador pela versão virtual
    # (temp_interna - dt_evaporacao_desejado), sem tocar no Sistema nem em outras câmaras.
    # dt_camara_real: SEMPRE o Δt de verdade (temp_interna - sistema.temp_evaporacao), independente
    # da válvula estar ativa — é o que decide se os campos da Válvula Reguladora de Pressão aparecem
    # na tela (>10°C). dt_camara/temp_evap (usados no dimensionamento do forçador) viram a versão
    # virtual quando a válvula está ativa — se o gatilho da tela usasse dt_camara direto, ele
    # sumiria assim que a válvula ficasse ativa (o virtual normalmente é <10°C), prendendo o usuário
    # sem conseguir desligar a opção.
    dt_camara_real = (camara.temp_interna or 0) - (sistema.temp_evaporacao or 0) if sistema else None
    obs_valv_reg = None
    if camara.utilizar_valv_reg_pressao == "Sim" and camara.dt_evaporacao_desejado:
        dt_camara = camara.dt_evaporacao_desejado
        temp_evap = (camara.temp_interna or 0) - camara.dt_evaporacao_desejado
        obs_valv_reg = ("Temperatura de Saturação controlada. Considerada Temperatura de Evaporação "
                         f"{temp_evap:.1f}°C e Dt Evaporação {dt_camara:.1f}°C.")
    else:
        dt_camara = dt_camara_real
        temp_evap = sistema.temp_evaporacao if sistema else None

    alertas = []

    # ---- Seção 8 Forçadores ----
    # Cada candidato é avaliado contra a capacidade requerida que ELE MESMO gera (Q8 = calor do
    # motor daquele modelo específico, Cenário 1 ASHRAE, somado à carga base Q1-Q7 da câmara) —
    # nunca contra um valor emprestado de outro candidato. Isso elimina qualquer dependência de
    # "qual foi avaliado primeiro": o resultado é sempre o mesmo, função só da câmara e do
    # catálogo — aprovado 2026-08-10 (substitui a abordagem anterior de 2 passadas, que podia
    # descartar o menor modelo mesmo quando ele atendia à capacidade de forma autoconsistente).
    forcadores_out = []
    linha_considerada_modelo = None
    _valv_refs = []  # (item, row, coletores) — válvulas reatribuídas depois, com o cap_req FINAL
    carga_base_24h = carga_total_24h  # Q1-Q7, sem Q8 — base fixa pro cálculo autoconsistente de cada candidato

    for row in camara.forcadores:
        qtd = row.quantidade or 1
        if row.linha is None:
            # Catálogo do forçador foi excluído/alterado — nunca deixar isso derrubar o cálculo
            # da câmara inteira (dados dimensionais/demais forçadores continuam intactos).
            alertas.append("Catálogo do forçador (linha_id %s) não foi encontrado — provavelmente excluído. "
                            "Refaça a seleção do forçador nesta câmara." % row.linha_id)
            forcadores_out.append({
                "id": row.id, "fabricante": row.fabricante.nome if row.fabricante else None,
                "linha": None, "linha_id": row.linha_id, "erro_catalogo_ausente": True,
                "folga_desejada": row.folga_desejada, "considerado": row.considerado,
                "quantidade": qtd, "tipo_degelo_selecionado": row.tipo_degelo,
                "codigo_curto": row.codigo_curto, "valvulas": _valvulas_do_forcador(db, row, 1, cap_req, sistema, modelos_valvula_cadastrados),
            })
            _valv_refs.append((forcadores_out[-1], row, 1))
            continue
        modelos_calc = [_modelo_para_calculo(md) for md in row.linha.modelos]
        fator_gas_obj = None
        if sistema and sistema.gas_refrigerante:
            fator_gas_obj = (db.query(m.FatorCorrecaoGasForcador)
                              .filter_by(linha_id=row.linha_id, gas=sistema.gas_refrigerante).first())
        fatores = [fator_gas_obj.fator] if fator_gas_obj and fator_gas_obj.fator else None
        item = {"id": row.id, "fabricante": row.fabricante.nome, "linha": row.linha.nome,
                "linha_id": row.linha_id,
                "folga_desejada": row.folga_desejada, "considerado": row.considerado,
                "quantidade": qtd, "tipo_degelo_selecionado": row.tipo_degelo,
                "nomenclatura_selecionada": json.loads(row.nomenclatura_selecionada) if row.nomenclatura_selecionada else {},
                "fator_gas_aplicado": fator_gas_obj.fator if fator_gas_obj else None,
                "fator_gas_pendente": bool(sistema and sistema.gas_refrigerante and not (fator_gas_obj and fator_gas_obj.fator is not None)),
                # Tensão Comando/Equipamentos e Gás do sistema — fontes disponíveis pro Campo
                # Automático da nomenclatura do forçador (campo_catalogo.py).
                "tensao_comando": projeto.tensao_comando if projeto else None,
                "tensao_equipamentos": projeto.tensao_equipamentos if projeto else None,
                "gas": sistema.gas_refrigerante if sistema else None,
                "observacao_valv_reg_pressao": obs_valv_reg}
        escolhido = fc.selecionar_modelo_autoconsistente(
            modelos_calc, temp_evap, dt_camara, qtd, carga_base_24h,
            camara.fator_seguranca, camara.tempo_func_compressores,
            row.folga_desejada, fatores_correcao=fatores)
        if escolhido:
            trocas = fc.trocas_de_ar(escolhido["vazao_ar_m3h"], qtd, volume)
            item.update({
                "modelo_resultante": escolhido["modelo"],
                "modelo_comercial": _modelo_comercial_forcador(db, row.linha_id, escolhido["modelo"],
                    row.tipo_degelo, projeto.tensao_comando if projeto else None, item["nomenclatura_selecionada"],
                    dados_modelo={"fpi": escolhido.get("fpi"), "num_ventiladores": escolhido.get("num_ventiladores"),
                                  "diametro_ventilador_mm": escolhido.get("diametro_ventilador_mm")}),
                "capacidade_tabelada_kcal_h": round(fc.interpolar_capacidade(escolhido["capacidades"], temp_evap), 1) if temp_evap is not None else None,
                "capacidade_corrigida_unitaria": round(escolhido["capacidade_corrigida"], 1),
                "capacidade_instalada_total": round(escolhido["capacidade_corrigida"] * qtd, 1),
                "folga_real": round(escolhido["folga_real"], 1),
                "trocas_de_ar": round(trocas, 1) if trocas else None,
                "vazao_ar_m3h": escolhido["vazao_ar_m3h"], "tipo_degelo_catalogo": escolhido["tipo_degelo"],
                "tipo_degelo_opcoes_comerciais": cpc.opcoes_automatico(db, "Forcador", row.linha_id, "tipo_degelo"),
                "carga_gas_kg": escolhido["carga_gas_kg"], "pot_resistencia_degelo_w": escolhido["pot_resistencia_degelo_w"],
                "diametro_ventilador_mm": escolhido["diametro_ventilador_mm"], "flecha_ar_m": escolhido["flecha_ar_m"],
                "altura_max_instalacao_m": escolhido["altura_max_instalacao_m"],
                "pdl_referencia_m": escolhido["pdl_referencia_m"], "num_ventiladores": escolhido["num_ventiladores"],
                "fpi": escolhido["fpi"],
                "coletores_por_forcador": escolhido["coletores_por_forcador"],
            })
            # A flecha de ar é comparada com o COMPRIMENTO da câmara (direção do lançamento do ar
            # do forçador), não com a maior dimensão.
            if escolhido["flecha_ar_m"] and (camara.comprimento or 0) > escolhido["flecha_ar_m"]:
                alertas.append("Flecha de ar do forçador (%.1fm) insuficiente para o comprimento da câmara (%.1fm) — linha %s" % (
                    escolhido["flecha_ar_m"], camara.comprimento or 0, row.linha.nome))
            if escolhido["altura_max_instalacao_m"] and camara.pedireito and camara.pedireito > escolhido["altura_max_instalacao_m"]:
                alertas.append("Altura de instalação incompatível com o pé-direito (linha %s)" % row.linha.nome)
            if escolhido["pdl_referencia_m"] and camara.pedireito and camara.pedireito > escolhido["pdl_referencia_m"]:
                alertas.append("Pé-direito da câmara (%.2fm) acima do PDL Máximo do catálogo (%.2fm) — linha %s" % (
                    camara.pedireito, escolhido["pdl_referencia_m"], row.linha.nome))
            if trocas and (trocas < 30 or trocas > 60):
                alertas.append("Trocas de ar/hora fora da faixa recomendada (30-60/h) na linha %s" % row.linha.nome)
            if item["fator_gas_pendente"]:
                alertas.append("Fator de correção do gás %s ainda não preenchido para a linha %s — capacidade corrigida sem esse ajuste" % (sistema.gas_refrigerante, row.linha.nome))
            if escolhido["folga_real"] < row.folga_desejada:
                alertas.append("Folga insuficiente na linha %s: mesmo o maior modelo disponível (%dx %s) só atinge %.1f%% de folga (desejado %.0f%%) — aumente a quantidade" % (
                    row.linha.nome, qtd, escolhido["modelo"], escolhido["folga_real"], row.folga_desejada))
            if row.considerado:
                linha_considerada_modelo = escolhido
        item["codigo_curto"] = row.codigo_curto
        item["valvulas"] = _valvulas_do_forcador(db, row, escolhido["coletores_por_forcador"] if escolhido else 1, cap_req, sistema, modelos_valvula_cadastrados)
        _valv_refs.append((item, row, escolhido["coletores_por_forcador"] if escolhido else 1))
        forcadores_out.append(item)

    # ---- Q8 Forçadores (Cenário 1 ASHRAE) — totais da câmara refletem o modelo CONSIDERADO,
    # cuja folga/capacidade requerida já foram calculadas de forma autoconsistente acima.
    if linha_considerada_modelo is not None:
        q8 = linha_considerada_modelo["q8_candidato"]
        carga_total_24h = carga_base_24h + q8
        cap_req = linha_considerada_modelo["capacidade_requerida_candidato"]
        cap_req_unitaria = cap_req
        # O Abert. Válv. usa a MESMA Capacidade Requerida exibida (pós-Q8) — reatribuída aqui.
        for _item, _row, _colet in _valv_refs:
            _item["valvulas"] = _valvulas_do_forcador(db, _row, _colet, cap_req, sistema, modelos_valvula_cadastrados)

    # ---- Alertas adicionais ----
    if camara.produto and camara.produto.classe and dt_camara is not None:
        classe = db.query(m.ClasseProduto).filter_by(classe=camara.produto.classe).first()
        if classe and not (classe.dt_evap_min <= abs(dt_camara) <= classe.dt_evap_max):
            alertas.append("Umidade relativa pode ser incompatível com a Classe %s do produto (ΔT esperado %.0f-%.0f°C)"
                            % (classe.classe, classe.dt_evap_min, classe.dt_evap_max))
    if camara.temp_interna is not None and camara.temp_interna < 0 and camara.isolamento_piso \
            and "concreto" in (camara.isolamento_piso.material or "").lower():
        alertas.append("Piso em concreto não é recomendado para temperatura interna negativa")
    if volume and camara.pedireito and camara.pedireito > 10 and volume > 5000 and (camara.temp_interna or 0) < 0:
        alertas.append("Sugestão automática: considerar ventilação de piso (pé-direito>10m, volume>5.000m³, T<0°C)")

    return {
        "q1_produto": round(q1, 1), "q2_embalagem": round(q2, 1), "q3_penetracao": round(q3, 1),
        "q4_infiltracao": round(q4, 1), "q5_pessoas": round(q5, 1), "q6_iluminacao": round(q6, 1),
        "q7_equipamentos": round(q7, 1), "q8_forcadores": round(q8, 1), "carga_termica_total_24h": round(carga_total_24h, 1),
        "capacidade_requerida": round(cap_req, 1), "capacidade_requerida_unitaria": round(cap_req_unitaria, 1),
        "potencia_total_iluminacao_w": potencia_total_ilum, "luminotecnico": _calc_luminotecnico_camara(db, camara),
        "areas": areas, "dt_camara": dt_camara,
        "dt_camara_real": round(dt_camara_real, 1) if dt_camara_real is not None else None,
        "temp_evaporacao_sistema": sistema.temp_evaporacao if sistema else None,
        "temp_condensacao": round(projeto.temp_ambiente + sistema.delta_condensacao, 1)
            if (projeto and sistema and projeto.temp_ambiente is not None and sistema.delta_condensacao is not None) else None,
        "volume_m3": volume, "forcadores": forcadores_out, "alertas": alertas,
    }


def _serializar_camara_simples(camara: m.CamaraSimples) -> dict:
    sistema = camara.sistema
    projeto = sistema.projeto if sistema else None
    return {
        "tabela02_id": camara.tabela02_id, "area": camara.area, "pedireito": camara.pedireito,
        "temp_interna": camara.temp_interna, "fator_seguranca": camara.fator_seguranca,
        "potencia_luminaria_texto": camara.potencia_luminaria_texto, "qtd_luminarias": camara.qtd_luminarias,
        "tipo_ambiente_lumino_id": camara.tipo_ambiente_lumino_id, "largura": camara.largura,
        "comprimento": camara.comprimento,
        "utilizar_valv_reg_pressao": camara.utilizar_valv_reg_pressao,
        "dt_evaporacao_desejado": camara.dt_evaporacao_desejado,
        "forcadores": [{"id": row.id, "fabricante_id": row.fabricante_id, "linha_id": row.linha_id,
                          "folga_desejada": row.folga_desejada, "considerado": row.considerado,
                          "quantidade": row.quantidade, "tipo_degelo": row.tipo_degelo,
                          "codigo_curto": row.codigo_curto,
                          "nomenclatura_selecionada": row.nomenclatura_selecionada,
                          "valvulas": [{"id": v.id, "fabricante": v.fabricante, "tipo_expansao": v.tipo_expansao,
                                         "modelo_selecao": v.modelo_selecao, "carga_abertura_pct": v.carga_abertura_pct,
                                         "conexao_entrada": v.conexao_entrada, "conexao_saida": v.conexao_saida,
                                         "folga_desejada": v.folga_desejada, "considerado": v.considerado,
                                         "capacidade_unit_kcal_h": v.capacidade_unit_kcal_h, "orificio": v.orificio,
                                         "tensao": v.tensao, "tipo_motor": v.tipo_motor,
                                         "controlador": v.controlador} for v in row.valvulas]}
                         for row in camara.forcadores],
        "sistema_gas_refrigerante": sistema.gas_refrigerante if sistema else None,
        "sistema_temp_evaporacao": sistema.temp_evaporacao if sistema else None,
        "sistema_delta_condensacao": sistema.delta_condensacao if sistema else None,
        "sistema_fabricante_valvula": sistema.fabricante_valvula if sistema else None,
        "sistema_tipo_expansao": sistema.tipo_expansao if sistema else None,
        "projeto_temp_ambiente": projeto.temp_ambiente if projeto else None,
        "projeto_tensao_comando": projeto.tensao_comando if projeto else None,
    }


def calcular_camara_simples_de_dados(db: Session, dados: dict) -> dict:
    modelos_valvula_cadastrados = {r[0] for r in db.query(m.TabelaValvulaExpansao.modelo).all()}
    faixas = [{"pe_direito_ate_m": f.pe_direito_ate_m, "fator": f.fator} for f in db.query(m.FatorAltura).all()]
    carga_tabelada = None
    if dados["tabela02_id"] and dados["area"]:
        faixa_area = (db.query(m.FaixaAreaTabela02)
                      .filter(m.FaixaAreaTabela02.tabela02_id == dados["tabela02_id"],
                              m.FaixaAreaTabela02.area_de <= dados["area"],
                              m.FaixaAreaTabela02.area_ate >= dados["area"])
                      .first())
        carga_tabelada = faixa_area.carga_kcal_h if faixa_area else None
    fator_seguranca_mult = 1 + (dados["fator_seguranca"] or 0) / 100
    carga_base = cs.carga_simplificada(carga_tabelada or 0, dados["pedireito"] or 0, faixas)
    cap_req = carga_base * fator_seguranca_mult
    carga_total_24h = cap_req * 24
    cap_req_unitaria = cap_req

    potencia_ilum_w = None
    _pot_w_simples = _extrair_potencia_w(dados["potencia_luminaria_texto"])
    if _pot_w_simples is not None and dados["qtd_luminarias"]:
        potencia_ilum_w = round(dados["qtd_luminarias"] * _pot_w_simples, 1)

    dt_camara_real = (dados["temp_interna"] or 0) - (dados["sistema_temp_evaporacao"] or 0)
    obs_valv_reg = None
    if dados["utilizar_valv_reg_pressao"] == "Sim" and dados["dt_evaporacao_desejado"]:
        dt_camara = dados["dt_evaporacao_desejado"]
        temp_evap = (dados["temp_interna"] or 0) - dados["dt_evaporacao_desejado"]
        obs_valv_reg = ("Temperatura de Saturação controlada. Considerada Temperatura de Evaporação "
                         f"{temp_evap:.1f}°C e Dt Evaporação {dt_camara:.1f}°C.")
    else:
        dt_camara = dt_camara_real
        temp_evap = dados["sistema_temp_evaporacao"]

    alertas = []
    if dados["area"] and dados["area"] > 150:
        alertas.append("Área da câmara (%.0fm²) acima do máximo admissível para o cálculo simplificado (150m²) — use a Câmara Completo" % dados["area"])
    forcadores_out = []
    linha_considerada_modelo = None
    tipo_expansao_nome = idc.nome_por_codigo(db, dados["sistema_tipo_expansao"]) if dados["sistema_tipo_expansao"] else None
    for row in dados["forcadores"]:
        qtd = row["quantidade"] or 1
        linha = db.get(m.LinhaForcador, row["linha_id"]) if row["linha_id"] else None
        fabricante = db.get(m.Fabricante, row["fabricante_id"]) if row["fabricante_id"] else None
        if linha is None:
            alertas.append("Catálogo do forçador (linha_id %s) não foi encontrado — provavelmente excluído. "
                            "Refaça a seleção do forçador nesta câmara." % row["linha_id"])
            forcadores_out.append({
                "id": row["id"], "fabricante": fabricante.nome if fabricante else None,
                "linha": None, "linha_id": row["linha_id"], "erro_catalogo_ausente": True,
                "folga_desejada": row["folga_desejada"], "considerado": row["considerado"],
                "quantidade": qtd, "tipo_degelo_selecionado": row["tipo_degelo"],
                "codigo_curto": row["codigo_curto"],
                "valvulas": _valvulas_do_forcador_dados(row["valvulas"], row["quantidade"], 1, cap_req,
                    dados["sistema_fabricante_valvula"], tipo_expansao_nome, modelos_valvula_cadastrados)})
            continue
        modelos_calc = [_modelo_para_calculo(md) for md in linha.modelos]
        fator_gas_obj = None
        if dados["sistema_gas_refrigerante"]:
            fator_gas_obj = (db.query(m.FatorCorrecaoGasForcador)
                              .filter_by(linha_id=row["linha_id"], gas=dados["sistema_gas_refrigerante"]).first())
        fatores = [fator_gas_obj.fator] if fator_gas_obj and fator_gas_obj.fator else None
        escolhido = fc.selecionar_modelo(modelos_calc, temp_evap, dt_camara, cap_req_unitaria / qtd,
                                          row["folga_desejada"], fatores_correcao=fatores)
        item = {"id": row["id"], "fabricante": fabricante.nome if fabricante else None, "linha": linha.nome,
                "linha_id": row["linha_id"],
                "folga_desejada": row["folga_desejada"], "considerado": row["considerado"],
                "quantidade": qtd, "tipo_degelo_selecionado": row["tipo_degelo"],
                "nomenclatura_selecionada": json.loads(row["nomenclatura_selecionada"]) if row["nomenclatura_selecionada"] else {},
                "fator_gas_aplicado": fator_gas_obj.fator if fator_gas_obj else None,
                "fator_gas_pendente": bool(dados["sistema_gas_refrigerante"] and not (fator_gas_obj and fator_gas_obj.fator is not None)),
                "tensao_comando": dados["projeto_tensao_comando"],
                "observacao_valv_reg_pressao": obs_valv_reg}
        if escolhido:
            capacidade_instalada_total = escolhido["capacidade_corrigida"] * qtd
            folga_real = folga_percentual(capacidade_instalada_total, cap_req_unitaria)
            trocas = fc.trocas_de_ar(escolhido["vazao_ar_m3h"], qtd, dados["area"] * dados["pedireito"] if dados["area"] and dados["pedireito"] else None)
            item.update({
                "modelo_resultante": escolhido["modelo"],
                "modelo_comercial": _modelo_comercial_forcador(db, row["linha_id"], escolhido["modelo"],
                    row["tipo_degelo"], dados["projeto_tensao_comando"], item["nomenclatura_selecionada"],
                    dados_modelo={"fpi": escolhido.get("fpi"), "num_ventiladores": escolhido.get("num_ventiladores"),
                                  "diametro_ventilador_mm": escolhido.get("diametro_ventilador_mm")}),
                "capacidade_tabelada_kcal_h": round(fc.interpolar_capacidade(escolhido["capacidades"], temp_evap), 1) if temp_evap is not None else None,
                "capacidade_corrigida_unitaria": round(escolhido["capacidade_corrigida"], 1),
                "capacidade_instalada_total": round(capacidade_instalada_total, 1),
                "folga_real": round(folga_real, 1),
                "trocas_de_ar": round(trocas, 1) if trocas else None,
                "coletores_por_forcador": escolhido["coletores_por_forcador"],
                "tipo_degelo_catalogo": escolhido["tipo_degelo"], "carga_gas_kg": escolhido["carga_gas_kg"],
                "tipo_degelo_opcoes_comerciais": cpc.opcoes_automatico(db, "Forcador", row["linha_id"], "tipo_degelo"),
                "pot_resistencia_degelo_w": escolhido["pot_resistencia_degelo_w"],
                "diametro_ventilador_mm": escolhido["diametro_ventilador_mm"], "flecha_ar_m": escolhido["flecha_ar_m"],
                "altura_max_instalacao_m": escolhido["altura_max_instalacao_m"], "vazao_ar_m3h": escolhido["vazao_ar_m3h"],
                "pdl_referencia_m": escolhido["pdl_referencia_m"], "num_ventiladores": escolhido["num_ventiladores"],
                "fpi": escolhido["fpi"],
            })
            if trocas and (trocas < 30 or trocas > 60):
                alertas.append("Trocas de ar/hora fora da faixa recomendada (30-60/h) na linha %s" % linha.nome)
            if escolhido["pdl_referencia_m"] and dados["pedireito"] and dados["pedireito"] > escolhido["pdl_referencia_m"]:
                alertas.append("Pé-direito da câmara (%.2fm) acima do PDL Máximo do catálogo (%.2fm) — linha %s" % (
                    dados["pedireito"], escolhido["pdl_referencia_m"], linha.nome))
            if item["fator_gas_pendente"]:
                alertas.append("Fator de correção do gás %s ainda não preenchido para a linha %s — capacidade corrigida sem esse ajuste" % (dados["sistema_gas_refrigerante"], linha.nome))
            if folga_real < row["folga_desejada"]:
                alertas.append("Folga insuficiente na linha %s: mesmo o maior modelo disponível (%dx %s) só atinge %.1f%% de folga (desejado %.0f%%) — aumente a quantidade" % (
                    linha.nome, qtd, escolhido["modelo"], folga_real, row["folga_desejada"]))
            if row["considerado"]:
                linha_considerada_modelo = {**escolhido, "quantidade": qtd}
        item["codigo_curto"] = row["codigo_curto"]
        item["valvulas"] = _valvulas_do_forcador_dados(row["valvulas"], row["quantidade"],
            escolhido["coletores_por_forcador"] if escolhido else 1, cap_req,
            dados["sistema_fabricante_valvula"], tipo_expansao_nome, modelos_valvula_cadastrados)
        forcadores_out.append(item)

    return {
        "carga_termica_total_24h": round(carga_total_24h, 1), "capacidade_requerida": round(cap_req, 1),
        "capacidade_requerida_unitaria": round(cap_req_unitaria, 1), "dt_camara": dt_camara,
        "dt_camara_real": round(dt_camara_real, 1) if dt_camara_real is not None else None,
        "temp_evaporacao_sistema": dados["sistema_temp_evaporacao"],
        "temp_condensacao": round(dados["projeto_temp_ambiente"] + dados["sistema_delta_condensacao"], 1)
            if (dados["projeto_temp_ambiente"] is not None and dados["sistema_delta_condensacao"] is not None) else None,
        "potencia_ilum_w": potencia_ilum_w,
        "luminotecnico": _calc_luminotecnico_camara_dados(db, dados),
        "forcadores": forcadores_out, "alertas": alertas,
    }


def calcular_camara_simples(db: Session, camara: m.CamaraSimples) -> dict:
    modelos_valvula_cadastrados = {r[0] for r in db.query(m.TabelaValvulaExpansao.modelo).all()}
    # Carga = Carga tabelada (Tabela 02, por faixa de área x tipo de câmara) x Fator Altura
    # (pé-direito) x (1 + Fator Segurança). Sem tempo de funcionamento de compressores, sem
    # "% de Ajuste" global — não fazem parte da fórmula do cálculo simplificado.
    faixas = [{"pe_direito_ate_m": f.pe_direito_ate_m, "fator": f.fator} for f in db.query(m.FatorAltura).all()]
    carga_tabelada = None
    if camara.tabela02_id and camara.area:
        faixa_area = (db.query(m.FaixaAreaTabela02)
                      .filter(m.FaixaAreaTabela02.tabela02_id == camara.tabela02_id,
                              m.FaixaAreaTabela02.area_de <= camara.area,
                              m.FaixaAreaTabela02.area_ate >= camara.area)
                      .first())
        carga_tabelada = faixa_area.carga_kcal_h if faixa_area else None
    fator_seguranca_mult = 1 + (camara.fator_seguranca or 0) / 100
    carga_base = cs.carga_simplificada(carga_tabelada or 0, camara.pedireito or 0, faixas)
    cap_req = carga_base * fator_seguranca_mult
    carga_total_24h = cap_req * 24  # só para exibição consistente com a Câmara Completo
    cap_req_unitaria = cap_req

    # Potência Ilum. — desde o Estudo Luminotécnico (aprovado 2026-08-08), mesma fórmula da Câmara
    # Completo: Qtd. Luminárias x Potência (extraída da Potência/Luminária escolhida na árvore) — os
    # 3 configs globais antigos (W/m²/lm/m²/W-lâmpada) foram aposentados. Sem Potência escolhida, fica
    # None (nunca entrou na carga térmica mesmo antes — só usada em Compilação/Consumo).
    potencia_ilum_w = None
    _pot_w_simples = _extrair_potencia_w(camara.potencia_luminaria_texto)
    if _pot_w_simples is not None and camara.qtd_luminarias:
        potencia_ilum_w = round(camara.qtd_luminarias * _pot_w_simples, 1)

    sistema = camara.sistema
    projeto = sistema.projeto if sistema else None
    dt_camara_real = (camara.temp_interna or 0) - (sistema.temp_evaporacao or 0) if sistema else None
    obs_valv_reg = None
    if camara.utilizar_valv_reg_pressao == "Sim" and camara.dt_evaporacao_desejado:
        dt_camara = camara.dt_evaporacao_desejado
        temp_evap = (camara.temp_interna or 0) - camara.dt_evaporacao_desejado
        obs_valv_reg = ("Temperatura de Saturação controlada. Considerada Temperatura de Evaporação "
                         f"{temp_evap:.1f}°C e Dt Evaporação {dt_camara:.1f}°C.")
    else:
        dt_camara = dt_camara_real
        temp_evap = sistema.temp_evaporacao if sistema else None

    alertas = []
    if camara.area and camara.area > 150:
        alertas.append("Área da câmara (%.0fm²) acima do máximo admissível para o cálculo simplificado (150m²) — use a Câmara Completo" % camara.area)
    forcadores_out = []
    linha_considerada_modelo = None
    for row in camara.forcadores:
        qtd = row.quantidade or 1
        if row.linha is None:
            alertas.append("Catálogo do forçador (linha_id %s) não foi encontrado — provavelmente excluído. "
                            "Refaça a seleção do forçador nesta câmara." % row.linha_id)
            forcadores_out.append({
                "id": row.id, "fabricante": row.fabricante.nome if row.fabricante else None,
                "linha": None, "linha_id": row.linha_id, "erro_catalogo_ausente": True,
                "folga_desejada": row.folga_desejada, "considerado": row.considerado,
                "quantidade": qtd, "tipo_degelo_selecionado": row.tipo_degelo,
                "codigo_curto": row.codigo_curto, "valvulas": _valvulas_do_forcador(db, row, 1, cap_req, sistema, modelos_valvula_cadastrados),
            })
            continue
        modelos_calc = [_modelo_para_calculo(md) for md in row.linha.modelos]
        fator_gas_obj = None
        if sistema and sistema.gas_refrigerante:
            fator_gas_obj = (db.query(m.FatorCorrecaoGasForcador)
                              .filter_by(linha_id=row.linha_id, gas=sistema.gas_refrigerante).first())
        fatores = [fator_gas_obj.fator] if fator_gas_obj and fator_gas_obj.fator else None
        escolhido = fc.selecionar_modelo(modelos_calc, temp_evap, dt_camara, cap_req_unitaria / qtd,
                                          row.folga_desejada, fatores_correcao=fatores)
        item = {"id": row.id, "fabricante": row.fabricante.nome, "linha": row.linha.nome,
                "linha_id": row.linha_id,
                "folga_desejada": row.folga_desejada, "considerado": row.considerado,
                "quantidade": qtd, "tipo_degelo_selecionado": row.tipo_degelo,
                "nomenclatura_selecionada": json.loads(row.nomenclatura_selecionada) if row.nomenclatura_selecionada else {},
                "fator_gas_aplicado": fator_gas_obj.fator if fator_gas_obj else None,
                "fator_gas_pendente": bool(sistema and sistema.gas_refrigerante and not (fator_gas_obj and fator_gas_obj.fator is not None)),
                "tensao_comando": projeto.tensao_comando if projeto else None,
                "observacao_valv_reg_pressao": obs_valv_reg}
        if escolhido:
            capacidade_instalada_total = escolhido["capacidade_corrigida"] * qtd
            folga_real = folga_percentual(capacidade_instalada_total, cap_req_unitaria)
            trocas = fc.trocas_de_ar(escolhido["vazao_ar_m3h"], qtd, camara.area * camara.pedireito if camara.area and camara.pedireito else None)
            item.update({
                "modelo_resultante": escolhido["modelo"],
                "modelo_comercial": _modelo_comercial_forcador(db, row.linha_id, escolhido["modelo"],
                    row.tipo_degelo, projeto.tensao_comando if projeto else None, item["nomenclatura_selecionada"],
                    dados_modelo={"fpi": escolhido.get("fpi"), "num_ventiladores": escolhido.get("num_ventiladores"),
                                  "diametro_ventilador_mm": escolhido.get("diametro_ventilador_mm")}),
                "capacidade_tabelada_kcal_h": round(fc.interpolar_capacidade(escolhido["capacidades"], temp_evap), 1) if temp_evap is not None else None,
                "capacidade_corrigida_unitaria": round(escolhido["capacidade_corrigida"], 1),
                "capacidade_instalada_total": round(capacidade_instalada_total, 1),
                "folga_real": round(folga_real, 1),
                "trocas_de_ar": round(trocas, 1) if trocas else None,
                "coletores_por_forcador": escolhido["coletores_por_forcador"],
                "tipo_degelo_catalogo": escolhido["tipo_degelo"], "carga_gas_kg": escolhido["carga_gas_kg"],
                "tipo_degelo_opcoes_comerciais": cpc.opcoes_automatico(db, "Forcador", row.linha_id, "tipo_degelo"),
                "pot_resistencia_degelo_w": escolhido["pot_resistencia_degelo_w"],
                "diametro_ventilador_mm": escolhido["diametro_ventilador_mm"], "flecha_ar_m": escolhido["flecha_ar_m"],
                "altura_max_instalacao_m": escolhido["altura_max_instalacao_m"], "vazao_ar_m3h": escolhido["vazao_ar_m3h"],
                "pdl_referencia_m": escolhido["pdl_referencia_m"], "num_ventiladores": escolhido["num_ventiladores"],
                "fpi": escolhido["fpi"],
            })
            if trocas and (trocas < 30 or trocas > 60):
                alertas.append("Trocas de ar/hora fora da faixa recomendada (30-60/h) na linha %s" % row.linha.nome)
            if escolhido["pdl_referencia_m"] and camara.pedireito and camara.pedireito > escolhido["pdl_referencia_m"]:
                alertas.append("Pé-direito da câmara (%.2fm) acima do PDL Máximo do catálogo (%.2fm) — linha %s" % (
                    camara.pedireito, escolhido["pdl_referencia_m"], row.linha.nome))
            if item["fator_gas_pendente"]:
                alertas.append("Fator de correção do gás %s ainda não preenchido para a linha %s — capacidade corrigida sem esse ajuste" % (sistema.gas_refrigerante, row.linha.nome))
            if folga_real < row.folga_desejada:
                alertas.append("Folga insuficiente na linha %s: mesmo o maior modelo disponível (%dx %s) só atinge %.1f%% de folga (desejado %.0f%%) — aumente a quantidade" % (
                    row.linha.nome, qtd, escolhido["modelo"], folga_real, row.folga_desejada))
            if row.considerado:
                linha_considerada_modelo = {**escolhido, "quantidade": qtd}
        item["codigo_curto"] = row.codigo_curto
        item["valvulas"] = _valvulas_do_forcador(db, row, escolhido["coletores_por_forcador"] if escolhido else 1, cap_req, sistema, modelos_valvula_cadastrados)
        forcadores_out.append(item)

    return {
        "carga_termica_total_24h": round(carga_total_24h, 1), "capacidade_requerida": round(cap_req, 1),
        "capacidade_requerida_unitaria": round(cap_req_unitaria, 1), "dt_camara": dt_camara,
        "dt_camara_real": round(dt_camara_real, 1) if dt_camara_real is not None else None,
        "temp_evaporacao_sistema": sistema.temp_evaporacao if sistema else None,
        "temp_condensacao": round(projeto.temp_ambiente + sistema.delta_condensacao, 1)
            if (projeto and sistema and projeto.temp_ambiente is not None and sistema.delta_condensacao is not None) else None,
        "potencia_ilum_w": potencia_ilum_w,
        "luminotecnico": _calc_luminotecnico_camara(db, camara),
        "forcadores": forcadores_out, "alertas": alertas,
    }


# ---- Snapshot do cálculo (visualização offline / sem assinatura ativa) ----
# Cálculo é EXCLUSIVAMENTE remoto (Fly.io). Se o servidor retornar OK, grava snapshot. Se não
# conseguir (sem rede ou erro), devolve o último snapshot marcado como desatualizado. Se não
# houver licença (401/403), devolve snapshot marcado com _sem_licenca. Sem snapshot anterior, erro.
def calcular_camara_completo_seguro(db: Session, camara: m.CamaraCompleto) -> dict:
    try:
        dados = _serializar_camara_completo(camara)
        status, calc = _remoto.camara_completo(dados, _token_usuario.get())
        if status == _remoto.Status.OK and calc:
            camara.calculo_snapshot_json = json.dumps(calc)
            camara.calculo_desatualizado = False
            db.commit()
            return calc
        return _snapshot_ou_erro(camara, status)
    except ValueError:
        raise
    except Exception:
        return _snapshot_ou_erro(camara, _remoto.Status.ERRO_SERVIDOR)


def calcular_camara_simples_seguro(db: Session, camara: m.CamaraSimples) -> dict:
    try:
        dados = _serializar_camara_simples(camara)
        status, calc = _remoto.camara_simples(dados, _token_usuario.get())
        if status == _remoto.Status.OK and calc:
            camara.calculo_snapshot_json = json.dumps(calc)
            camara.calculo_desatualizado = False
            db.commit()
            return calc
        return _snapshot_ou_erro(camara, status)
    except ValueError:
        raise
    except Exception:
        return _snapshot_ou_erro(camara, _remoto.Status.ERRO_SERVIDOR)


def _snapshot_ou_erro(entidade, status: str) -> dict:
    if entidade.calculo_snapshot_json:
        calc = json.loads(entidade.calculo_snapshot_json)
        calc["_snapshot_desatualizado"] = True
        if status == _remoto.Status.SEM_LICENCA:
            calc["_sem_licenca"] = True
        return calc
    if status == _remoto.Status.SEM_LICENCA:
        raise ValueError("Assinatura inativa — cálculo não disponível.")
    raise ValueError("Sem conexão com o servidor de cálculo e sem snapshot anterior.")
