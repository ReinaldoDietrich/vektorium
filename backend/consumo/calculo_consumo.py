# -*- coding: utf-8 -*-
"""Tela D — Cálculo de Consumo Elétrico e Payback.

Metodologia (validada na literatura de refrigeração — fração de tempo de operação / duty cycle):
compressor liga em potência nominal e a fração do tempo ligado é proporcional à razão entre a
carga necessária e a capacidade fornecida. Consumo [kWh] = Potência[kW] × Fator_Carga × Horas × 30.

Roda o cálculo em 2 cenários por sistema, usando o MESMO equipamento (mesma UC, mesmos forçadores)
e só alternando as otimizações, pra isolar o efeito delas no payback:
  - "projeto": conforme configurado (aplica redução de EEV se Expansão=Eletrônica; não conta carga
    de degelo elétrico se o degelo selecionado for Gás Quente ou Natural).
  - "simples": baseline sem nenhuma otimização (sem redução de EEV; linhas com degelo Gás Quente são
    simuladas como Elétrico, usando a potência de resistência publicada no catálogo do forçador).
    Linhas com degelo Natural NUNCA são simuladas como Elétrico em nenhum dos dois cenários — não é
    uma otimização escolhida, é ausência de necessidade de degelo ativo (câmara opera acima de 0°C
    ou não acumula geada o suficiente); forçar essa carga distorceria a comparação.

Escopo (deliberado, ver conversa com o usuário):
  - Só sistemas com tipo_compressao = "Unidade Condensadora Comercial" — Rack Paralelo não tem
    catálogo de equipamento com dados elétricos no app ainda, não dá pra calcular consumo real.
  - Só Câmara Completo e Câmara Simples (têm forçador vinculado + tempo_func_compressores).
    Expositores têm equipamento próprio autocontido, fora do escopo deste motor.
  - Iluminação não é modelada (a app não cadastra potência de luminária por câmara ainda).

Partida (Sistema.partida = "Direta" | "Dividida" | "SoftStarter"): NÃO entra neste cálculo.
  Confirmado por pesquisa (2026-07-17): partida estrela-triângulo (Dividida) e SoftStarter reduzem
  só a corrente de PICO no instante de partida (a estrela-triângulo cai pra ~33% da corrente em
  triângulo só durante a aceleração; o SoftStarter é eletricamente removido do circuito assim que
  atinge velocidade nominal). Em regime, o motor puxa a mesma corrente nominal independente de como
  partiu — não há redução de consumo mensal a modelar. Ver fontes: WattBuild ("soft start does not
  meaningfully reduce steady state power"), EEPower ("Motor Starters — Star-Delta"). `partida` é
  puramente descritivo (compõe a descrição técnica de compra do equipamento / memorial).

Modo Operação (Sistema.modo_operacao) — aqui sim há redução real de consumo, cada modo com seu
  próprio fator em Configurações Globais, calibrado por pesquisa de literatura/fabricante (não
  chute — ver fontes ao final):

  "Controle de Capacidade" = descarregamento mecânico de cilindros (ex.: sistema Bitzer CR — injeta
  pressão de óleo/gás no cabeçote pra levantar a palheta de sucção e desativar cilindro(s)). O
  compressor descarrega em degraus, mas o motor continua girando: em descarregamento máximo, a
  literatura reporta o consumo elétrico caindo só a ~80-85% do consumo em plena carga (ou seja,
  redução real de até ~15-20%, não mais que isso — a eficiência/COP piora ao descarregar, porque a
  potência não cai na mesma proporção que a capacidade).
  Modelo aplicado (linear, piso em 35% de carga — ponto em que o compressor não consegue mais
  modular e volta a ciclar):
    reducao_pct = reducao_controle_capacidade_pct (config. global, default 18%) × clamp((1 −
    fator_carga) / (1 − 0.35), 0, 1)

  "Inversor de Frequência" (VFD) = modulação real de rotação do motor. Ganho de categoria diferente
  do descarregamento mecânico, por seguir as Leis de Afinidade (potência cai aproximadamente com o
  cubo da rotação). Estudos de mercado/fabricante (Danfoss, York) reportam de 30% a 50% de melhoria
  em IEER (eficiência sazonal em carga parcial) frente a liga/desliga tradicional. Piso de modulação
  mais baixo que o mecânico (compressores com VFD tipicamente modulam até ~20% de capacidade).
  Modelo aplicado (mesma forma linear, piso em 20% de carga):
    reducao_pct = reducao_inversor_pct (config. global, default 40%) × clamp((1 − fator_carga) /
    (1 − 0.20), 0, 1)

  Os dois modos são mutuamente exclusivos (campo único `modo_operacao`) e só aplicados no cenário
  "projeto" (mesmo tratamento dado à redução por EEV) — o padrão (None = Liga/Desliga) mantém
  reducao = 0%, comportamento anterior a essa funcionalidade existir.

  Fontes consultadas (busca 2026-07-17): Rawal/York "Capacity Modulation Comparison for Hot Gas
  Bypass" (white paper — dado de ~15-20% de potência em descarregamento máximo de compressor a
  pistão); Delta T Systems "How Do Variable Speed Compressors Improve Energy Efficiency"; BITZER
  "Efficient capacity control saves energy and costs"; Compressed Air Towards Zero — Compressor
  Capacity Control (aircyclopedia).
"""
from .. import models as m
from .. import id_comercial as idc

FATOR_POTENCIA = 0.85  # mesma convenção usada nas planilhas de referência do usuário


def _tensao_num(tensao_str):
    if not tensao_str:
        return None
    try:
        return float(str(tensao_str).upper().split("V")[0].strip())
    except (ValueError, IndexError):
        return None


def _potencia_compressor_kw(uc: m.UnidadeCondensadora, eletrica: m.EletricaUC):
    """Deriva a potência do(s) compressor(es) + ventiladores do condensador onboard a partir de
    tensão/corrente da linha Elétrica resolvida pela Tensão do projeto (RLA — corrente de regime;
    MCC como alternativa se RLA não estiver preenchida). MCC/RLA no catálogo já são a corrente de
    TODOS os compressores da unidade somada (não por compressor individual) — não multiplicar por
    numero_compressores."""
    if not eletrica:
        return None
    v = _tensao_num(eletrica.tensao)
    i = eletrica.rla_a or eletrica.mcc_a
    p_comp_kw = None
    if v and i:
        fases = eletrica.fases or 1
        mult = 3 ** 0.5 if fases == 3 else 1
        p_comp_kw = (mult * v * i * FATOR_POTENCIA) / 1000
    p_vent_kw = None
    if eletrica.vent_corrente_a:
        v_vent = _tensao_num(eletrica.vent_tensao) or v
        fases_vent = eletrica.vent_fases or 1
        if v_vent:
            mult_vent = 3 ** 0.5 if fases_vent == 3 else 1
            p_vent_kw = (mult_vent * v_vent * eletrica.vent_corrente_a * FATOR_POTENCIA) / 1000
    if p_comp_kw is None and p_vent_kw is None:
        return None
    return (p_comp_kw or 0) + (p_vent_kw or 0)


def _dados_ventiladores_condensador(db, rack, v_equip):
    """Potência dos ventiladores do Condensador Remoto selecionado na Tela 6 (mesma corrente nominal
    do resumo do rack × qtd. de ventiladores do modelo) + tipo de motor (AC/EC) e fator de carga do
    PRÓPRIO condensador (calor rejeitado / capacidade corrigida) — usado pra escalar a redução do
    ventilador EC pela folga real do condensador (ver _reducao_ec_condensador)."""
    from ..routers.rack_paralelo import selecao_condensador
    dados = selecao_condensador(rack.id, db)
    sel = dados.get("selecao")
    e = sel.get("escolhido") if sel else None
    if not e:
        return None, None, None
    qtd_condensadores = (sel.get("quantidade_condensadores") or 1)
    p_vent_kw = None
    if e.get("corrente_ventiladores_a") and v_equip:
        qtd = (e.get("qtd_ventiladores") or 1) * qtd_condensadores
        p_vent_kw = (v_equip * e["corrente_ventiladores_a"] * qtd * FATOR_POTENCIA) / 1000
    fator_carga_condensador = None
    capacidade_total = e.get("capacidade_corrigida_total_kcal_h") or e.get("capacidade_corrigida_kcal_h")
    if dados.get("calor_rejeitado_kcal_h") and capacidade_total:
        fator_carga_condensador = min(dados["calor_rejeitado_kcal_h"] / capacidade_total, 1)
    return p_vent_kw, (e.get("tipo_motor") or "").upper(), fator_carga_condensador


def _reducao_ec_condensador(db, fator_carga_condensador):
    """Ventilador EC do Condensador Remoto modula a rotação conforme a folga do condensador — quanto
    mais folga (fator de carga baixo), mais o EC reduz rotação/consumo frente a um AC de rotação
    fixa. Mesma forma linear já usada pro Modo Operação do compressor (piso 20%, mesmo da tecnologia
    equivalente — Inversor de Frequência), mas com fator PRÓPRIO (reducao_ec_condensador_pct),
    independente do reducao_inversor_pct do compressor — são equipamentos e decisões diferentes."""
    if fator_carga_condensador is None:
        return 0.0
    PISO_EC = 0.20
    cfg = db.query(m.ConfiguracaoGlobal).filter_by(chave="reducao_ec_condensador_pct").first()
    reducao_maxima = (cfg.valor if cfg else 40) / 100
    proporcao = min(max((1 - fator_carga_condensador) / (1 - PISO_EC), 0), 1)
    return reducao_maxima * proporcao


def _selecao_rack_do_sistema(db, sistema, v_equip):
    """Potência do Rack (compressores, Tela 6) e capacidade fornecida — mesmo dado já exibido no
    Resumo do Rack, sem recalcular nada, só reaproveitando o endpoint existente. Ventiladores do
    condensador ficam de fora daqui (tratados à parte em calcular_consumo_sistema, pra poder aplicar
    a redução do EC só nessa parcela, não no compressor)."""
    from ..routers.rack_paralelo import resumo_compressores
    rack = sistema.rack_paralelo
    if not rack or not rack.quantidade_compressores:
        return None, 0
    dados = resumo_compressores(rack.id, db)
    resumo = dados["resumo"]
    n_paralelo = dados.get("quantidade_paralelo", 1)
    # carga do sistema INTEIRO (exibição/fator); capacidade/potência do resumo já são POR RACK
    # (dimensionadas sobre carga ÷ N). O fator de carga e o kWh multiplicam por N no chamador.
    carga_sistema = dados.get("carga_sistema_total_kcal_h", dados["carga_requerida_kcal_h"])
    completo = bool(dados["posicoes"]) and all(p["resultado"] is not None for p in dados["posicoes"])
    if not completo or not resumo["capacidade_total_kcal_h"]:
        return None, carga_sistema
    p_comp_kw = (resumo["potencia_total_w"] or 0) / 1000
    return ({"rack": rack, "p_comp_kw": p_comp_kw,
             "capacidade_kcal_h": resumo["capacidade_total_kcal_h"],
             "quantidade_paralelo": n_paralelo},
            carga_sistema)


def _selecao_uc_do_sistema(db, sistema):
    """Reaproveita a mesma resolução de UC usada na Tela 1 (seleção 'considerada' por sistema)."""
    from ..routers.unidades_condensadoras import obter_selecao, _eletrica_da_tensao
    resp = obter_selecao(sistema.id, db)
    escolhida = next((s for s in resp["selecoes"] if s.get("considerado") and s.get("unidade_id")), None)
    if not escolhida:
        return None, resp["carga_total_kcal_h"]
    uc = db.get(m.UnidadeCondensadora, escolhida["unidade_id"])
    projeto = sistema.projeto
    eletrica = _eletrica_da_tensao(uc, projeto.tensao_equipamentos if projeto else None)
    return {"uc": uc, "eletrica": eletrica, "capacidade_kcal_h": escolhida["capacidade_kcal_h"],
            "quantidade_paralelo": escolhida.get("quantidade_paralelo", 1)}, resp["carga_total_kcal_h"]


def _forcadores_do_sistema(db, sistema, tensao_comando, v_equip, considerar_ilum):
    """Para cada câmara (completo/simples) do sistema, resolve o forçador 'considerado' e devolve
    ventilação/degelo/portas/drenos elétricos + horas de funcionamento — mesmo motor de cálculo da
    Tela 2/3/5. Portas/Drenos são calculados 2x: com o tipo de degelo REAL da linha (cenário
    "projeto") e forçando Elétrico (cenário "simples", que já força degelo elétrico do mesmo jeito
    pra representar o baseline sem otimização — sem isso, um sistema real a Gás Quente/Natural
    ficaria sem essa carga também no baseline, subestimando o "sem otimização")."""
    from ..calc_service import calcular_camara_completo_seguro as calcular_camara_completo, calcular_camara_simples_seguro as calcular_camara_simples
    from ..routers.compilacao import _eletrica_forcador, _eletrica_dreno_portas

    def _item(camara, calc):
        eletrica = _eletrica_forcador(camara, calc, tensao_comando)
        row_considerada = next((r for r in camara.forcadores if r.considerado), None)
        tipo_degelo = row_considerada.tipo_degelo if row_considerada else None
        dp_real = _eletrica_dreno_portas(db, camara, v_equip, True, eletrica["quantidade"], eletrica["tipo_degelo"])
        # No cenário "simples" só linhas que JÁ usam degelo ATIVO na vida real (Elétrico ou Gás
        # Quente) viram Elétrico simulado — uma linha Natural nunca teria resistência de degelo/
        # portas/drenos em nenhum design realista (não é uma "otimização", é ausência de
        # necessidade), então fica de fora do baseline "sem otimização" também.
        tipo_simulado = "Elétrico" if tipo_degelo in ("Elétrico", "Gás quente") else tipo_degelo
        dp_forcado = _eletrica_dreno_portas(db, camara, v_equip, True, eletrica["quantidade"], tipo_simulado)
        # Iluminação AMBIENTE — Completo usa potencia_total_iluminacao_w (Q6), Simples usa
        # potencia_ilum_w (fórmula W/m² x lm/m² x potência da lâmpada); nunca afeta Expositor.
        ilum_w = calc.get("potencia_total_iluminacao_w") or calc.get("potencia_ilum_w")
        return {"vent_w": eletrica["vent_w"], "degelo_w": eletrica["degelo_w"], "tipo_degelo": tipo_degelo,
                "horas": camara.tempo_func_compressores or 18,
                "ilum_w": ilum_w if considerar_ilum else None,
                "portas_drenos_w_real": (dp_real["portas_w"] or 0) + (dp_real["drenos_w"] or 0),
                "portas_drenos_w_forcado": (dp_forcado["portas_w"] or 0) + (dp_forcado["drenos_w"] or 0)}

    itens = [_item(c, calcular_camara_completo(db, c)) for c in sistema.camaras_completo]
    itens += [_item(c, calcular_camara_simples(db, c)) for c in sistema.camaras_simples]
    return itens


def calcular_consumo_sistema(db, sistema: m.SistemaRefrigeracao) -> dict:
    # tipo_compressao/tipo_expansao/modo_operacao gravam o CÓDIGO da árvore de Ids Comerciais desde
    # 2026-08-08 ("4.1.1" Unidade Condensadora Comercial, "4.1.2" Rack Paralelo, "3.2" Eletrônica,
    # "4.1.4.1"/"4.1.4.2" Controle de Capacidade/Inversor de Frequência) — nunca mais nome, códigos
    # estáveis e não duplicáveis.
    if sistema.tipo_compressao not in ("4.1.1", "4.1.2"):
        return {"disponivel": False, "motivo": "Cálculo de consumo hoje só está disponível para "
                "Unidade Condensadora Comercial e Rack Paralelo."}

    from ..routers.compilacao import _voltagem_num

    projeto = sistema.projeto
    custo_kwh = (projeto.custo_energia if projeto else None) or 0
    tensao_comando = projeto.tensao_comando if projeto else None
    v_equip = _voltagem_num(projeto.tensao_equipamentos if projeto else None)
    considerar_ilum = projeto.considerar_iluminacao_ambiente if (projeto and projeto.considerar_iluminacao_ambiente is not None) else True

    p_vent_condensador_kw = None
    tipo_motor_condensador = None
    fator_carga_condensador = None
    if sistema.tipo_compressao == "4.1.2":  # Rack Paralelo
        rotulo_equipamento = "Rack considerado"
        sel, carga_total_kcal_h = _selecao_rack_do_sistema(db, sistema, v_equip)
        if not sel:
            return {"disponivel": False, "motivo": "Seleção de Compressores do Rack incompleta "
                    "ainda (Tela 6).", "carga_total_kcal_h": carga_total_kcal_h}
        modelo_equipamento = sel["rack"].modelo_comercial or "Rack Paralelo"
        hp_equipamento = sel["rack"].hp_total
        capacidade_kcal_h = sel["capacidade_kcal_h"]
        p_compressor_kw = sel["p_comp_kw"]
        p_vent_condensador_kw, tipo_motor_condensador, fator_carga_condensador = \
            _dados_ventiladores_condensador(db, sel["rack"], v_equip)
    else:
        rotulo_equipamento = "UC considerada"
        sel, carga_total_kcal_h = _selecao_uc_do_sistema(db, sistema)
        if not sel or not sel["uc"] or not sel["capacidade_kcal_h"]:
            return {"disponivel": False, "motivo": "Nenhuma Unidade Condensadora selecionada/"
                    "considerada para este sistema ainda (Tela 1 → Seleção de UC).",
                    "carga_total_kcal_h": carga_total_kcal_h}
        modelo_equipamento = sel["uc"].modelo
        hp_equipamento = sel["uc"].hp
        capacidade_kcal_h = sel["capacidade_kcal_h"]
        p_compressor_kw = _potencia_compressor_kw(sel["uc"], sel["eletrica"])

    n_paralelo = sel.get("quantidade_paralelo", 1) if sel else 1
    # Fator de carga é POR UNIDADE: cada equipamento idêntico em paralelo atende carga_total ÷ N.
    fator_carga = min((carga_total_kcal_h / n_paralelo) / capacidade_kcal_h, 1) if capacidade_kcal_h else None
    if p_compressor_kw is None or fator_carga is None:
        return {"disponivel": False, "motivo": "Dados elétricos do compressor incompletos para a "
                "Tensão configurada no projeto (Tela 1 → Tensão dos Equipamentos) — não dá pra "
                "calcular a potência.", "modelo_uc": modelo_equipamento}

    forcadores = _forcadores_do_sistema(db, sistema, tensao_comando, v_equip, considerar_ilum)
    horas = forcadores[0]["horas"] if forcadores else 18  # compressor é único/compartilhado no sistema
    horas_degelo = (sistema.quantidade_degelo_dia or 4) * (sistema.tempo_degelo_min or 60) / 60
    horas_iluminacao = sistema.horas_iluminacao_dia if sistema.horas_iluminacao_dia is not None else 10

    eev_ativo = sistema.tipo_expansao == "3.2"  # Eletrônica
    # Redução por Válvula Eletrônica é valor GLOBAL (Configurações), não por sistema — uma válvula
    # de expansão eletrônica não rende de forma diferente de um sistema pro outro.
    cfg_reducao_eev = db.query(m.ConfiguracaoGlobal).filter_by(chave="reducao_eev_pct").first()
    reducao_eev = ((cfg_reducao_eev.valor if cfg_reducao_eev else 15) / 100) if eev_ativo else 0

    # Modo Operação (ver docstring do módulo p/ fundamentação e fontes) — interpola linearmente
    # entre 0% de redução em 100% de carga e a redução máxima configurada (global) no piso de
    # modulação de cada modo; abaixo do piso, o benefício é tratado como constante (teto), já que o
    # modelo não simula ciclagem residual abaixo do ponto de modulação mínima do compressor.
    PISO_CONTROLE_CAPACIDADE = 0.35
    PISO_INVERSOR = 0.20
    modo_operacao = sistema.modo_operacao
    reducao_operacao = 0.0
    if modo_operacao == "4.1.4.1":  # Controle de Capacidade
        cfg_reducao_cap = db.query(m.ConfiguracaoGlobal).filter_by(chave="reducao_controle_capacidade_pct").first()
        reducao_maxima = (cfg_reducao_cap.valor if cfg_reducao_cap else 18) / 100
        proporcao = min(max((1 - fator_carga) / (1 - PISO_CONTROLE_CAPACIDADE), 0), 1)
        reducao_operacao = reducao_maxima * proporcao
    elif modo_operacao == "4.1.4.2":  # Inversor de Frequência
        cfg_reducao_inv = db.query(m.ConfiguracaoGlobal).filter_by(chave="reducao_inversor_pct").first()
        reducao_maxima = (cfg_reducao_inv.valor if cfg_reducao_inv else 40) / 100
        proporcao = min(max((1 - fator_carga) / (1 - PISO_INVERSOR), 0), 1)
        reducao_operacao = reducao_maxima * proporcao

    # Ventilador EC do Condensador Remoto (Rack Paralelo, Tela 6) — fator PRÓPRIO e independente do
    # Inversor de Frequência do compressor (ver _reducao_ec_condensador): equipamento diferente,
    # decisão de compra diferente, não faz sentido compartilhar o mesmo percentual configurado.
    reducao_ec = _reducao_ec_condensador(db, fator_carga_condensador) if tipo_motor_condensador == "EC" else 0.0

    def _cenario(aplicar_eev: bool, forcar_degelo_eletrico: bool, aplicar_modo_operacao: bool = False,
                 aplicar_reducao_ec: bool = False):
        p_comp = p_compressor_kw
        if aplicar_eev:
            p_comp *= (1 - reducao_eev)
        if aplicar_modo_operacao:
            p_comp *= (1 - reducao_operacao)
        kwh_compressor = p_comp * fator_carga * horas * 30 * n_paralelo  # N equipamentos idênticos em paralelo

        kwh_vent_condensador = 0.0
        if p_vent_condensador_kw:
            p_vent_cond = p_vent_condensador_kw * (1 - reducao_ec) if aplicar_reducao_ec else p_vent_condensador_kw
            kwh_vent_condensador = p_vent_cond * fator_carga * horas * 30 * n_paralelo

        kwh_vent = 0.0
        kwh_degelo = 0.0
        kwh_portas_drenos = 0.0
        kwh_iluminacao = 0.0
        degelo_sem_dado = False
        for f in forcadores:
            # Cada linha usa a hora de funcionamento da SUA câmara (Tempo de Funcionamento dos
            # Compressores) — não a de uma câmara qualquer do sistema, já que cada forçador só
            # atende a própria câmara (diferente do compressor, que é único/compartilhado).
            # Natural nunca vira Elétrico simulado (não é otimização, é ausência de necessidade de
            # degelo ativo) — só Gás Quente é "promovido" a Elétrico no cenário Simples.
            usa_eletrico = f["tipo_degelo"] == "Elétrico" or (forcar_degelo_eletrico and f["tipo_degelo"] == "Gás quente")
            if f["vent_w"]:
                # Fan delay thermostat (prática padrão de refrigeração comercial): o ventilador do
                # evaporador desliga durante o degelo elétrico (e no atraso pós-degelo) pra não
                # jogar ar quente/úmido no ambiente — desconta as horas de degelo elétrico da linha
                # das horas de funcionamento do ventilador dela.
                horas_vent = max(f["horas"] - horas_degelo, 0) if usa_eletrico else f["horas"]
                kwh_vent += (f["vent_w"] / 1000) * fator_carga * horas_vent * 30
            if usa_eletrico:
                if f["degelo_w"]:
                    kwh_degelo += (f["degelo_w"] / 1000) * horas_degelo * 30
                else:
                    degelo_sem_dado = True
            # Gás quente / Natural: sem linha extra — o compressor já roda pra prover o degelo.
            # Res. Portas/Drenos ficam ligadas ~100% do tempo (24h/dia) — sem fator de carga, que
            # só se aplica ao ciclo de refrigeração propriamente dito.
            portas_drenos_w = f["portas_drenos_w_forcado"] if forcar_degelo_eletrico else f["portas_drenos_w_real"]
            if portas_drenos_w:
                kwh_portas_drenos += (portas_drenos_w / 1000) * 24 * 30
            # Iluminação — só Câmara Completo tem potência cadastrada (Simples/Expositor não têm
            # esse dado hoje); horas vêm de "Horas de Iluminação/Dia" do sistema (Tela D), não da
            # premissa de 24h usada no cálculo de carga térmica.
            if f["ilum_w"]:
                kwh_iluminacao += (f["ilum_w"] / 1000) * horas_iluminacao * 30

        kwh_vent += kwh_vent_condensador
        kwh_total = kwh_compressor + kwh_vent + kwh_degelo + kwh_portas_drenos + kwh_iluminacao
        return {"kwh_compressor": round(kwh_compressor, 1), "kwh_ventiladores": round(kwh_vent, 1),
                "kwh_degelo": round(kwh_degelo, 1), "kwh_portas_drenos": round(kwh_portas_drenos, 1),
                "kwh_iluminacao": round(kwh_iluminacao, 1),
                "kwh_total_mes": round(kwh_total, 1),
                "custo_mes": round(kwh_total * custo_kwh, 2), "degelo_sem_dado": degelo_sem_dado}

    projeto_calc = _cenario(aplicar_eev=eev_ativo, forcar_degelo_eletrico=False, aplicar_modo_operacao=bool(modo_operacao),
                             aplicar_reducao_ec=True)
    simples_calc = _cenario(aplicar_eev=False, forcar_degelo_eletrico=True, aplicar_modo_operacao=False,
                             aplicar_reducao_ec=False)

    payback_meses = None
    if sistema.custo_sistema_simples is not None and sistema.custo_sistema_projeto is not None:
        delta_investimento = sistema.custo_sistema_projeto - sistema.custo_sistema_simples
        economia_mes = simples_calc["custo_mes"] - projeto_calc["custo_mes"]
        if economia_mes > 0:
            payback_meses = round(delta_investimento / economia_mes, 1)
        elif delta_investimento <= 0:
            payback_meses = 0  # projeto não custa mais e ainda economiza — retorno imediato

    return {
        "disponivel": True, "modelo_uc": modelo_equipamento, "hp_uc": hp_equipamento,
        "rotulo_equipamento": rotulo_equipamento, "quantidade_paralelo": n_paralelo,
        "carga_total_kcal_h": round(carga_total_kcal_h, 1), "capacidade_uc_kcal_h": round(capacidade_kcal_h, 1),
        "fator_carga_pct": round(fator_carga * 100, 1), "horas_funcionamento": horas,
        "horas_iluminacao_dia": horas_iluminacao,
        "eev_ativo": eev_ativo, "reducao_eev_pct": round(reducao_eev * 100, 1) if eev_ativo else None,
        "modo_operacao": idc.nome_por_codigo(db, modo_operacao) if modo_operacao else None,
        "reducao_operacao_pct": round(reducao_operacao * 100, 1) if modo_operacao else None,
        "ec_condensador_ativo": tipo_motor_condensador == "EC",
        "reducao_ec_condensador_pct": round(reducao_ec * 100, 1) if tipo_motor_condensador == "EC" else None,
        "projeto": projeto_calc, "simples": simples_calc,
        "economia_mes": round(simples_calc["custo_mes"] - projeto_calc["custo_mes"], 2),
        "payback_meses": payback_meses,
        "custo_sistema_simples": sistema.custo_sistema_simples, "custo_sistema_projeto": sistema.custo_sistema_projeto,
    }
