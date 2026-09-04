"""Q1 a Q7 da Câmara / Cálculo Completo (ASHRAE Handbook — Refrigeration, cap. 24).
Convenção adotada: cada Qx é a carga térmica TOTAL do dia (kcal/24h); a soma de Q1..Q7
só é convertida em capacidade (kcal/h) ao final, dividindo pelo Tempo Func. Compressores
(mesma convenção do Script_Implementacao: Capacidade Requerida = Carga Total / Tempo Func.).
"""
from .comum import W_PARA_KCAL_H


def calor_produto(mov_diaria_kg, qtd_estocada_kg, c1, c2, calor_latente, calor_respiracao,
                   temp_entrada, temp_saida, ponto_congelamento):
    """Q1 = calor sensível/latente do produto (3 estágios, conforme cruzamento com o ponto de
    congelamento) + calor de respiração (hortifrutigranjeiros)."""
    tf = ponto_congelamento if ponto_congelamento is not None else -1e9
    if temp_entrada <= tf:
        q1a, q1b = 0.0, 0.0
        q1c = mov_diaria_kg * (c2 or 0) * (temp_entrada - temp_saida)
    elif temp_saida >= tf:
        q1a = mov_diaria_kg * (c1 or 0) * (temp_entrada - temp_saida)
        q1b, q1c = 0.0, 0.0
    else:
        q1a = mov_diaria_kg * (c1 or 0) * (temp_entrada - tf)
        q1b = mov_diaria_kg * (calor_latente or 0)
        q1c = mov_diaria_kg * (c2 or 0) * (tf - temp_saida)
    q_resp = qtd_estocada_kg * (calor_respiracao or 0)  # catálogo já informa kcal/kg em base 24h
    return q1a + q1b + q1c + q_resp


def calor_embalagem(massa_kg_24h, calor_especifico, temp_entrada, temp_saida):
    """Q2 = massa de embalagem x calor específico do material x ΔT (independente do produto)."""
    if not massa_kg_24h or not calor_especifico:
        return 0.0
    return massa_kg_24h * calor_especifico * (temp_entrada - temp_saida)


def calor_penetracao(u_parede, u_teto, u_piso, largura, comprimento, pedireito,
                      temp_ambiente, temp_interna, temp_bulbo_umido, fator_insolacao=1.0):
    """Q3 = U x Área x ΔT x Majoração de Insolação, por superfície (parede/teto em bulbo seco,
    piso em bulbo úmido sem majoração). Áreas calculadas internamente, nunca expostas como campo."""
    perimetro = 2 * (largura + comprimento)
    area_parede = perimetro * pedireito
    area_teto = largura * comprimento
    area_piso = largura * comprimento
    dt_seco = temp_ambiente - temp_interna
    dt_umido = (temp_bulbo_umido if temp_bulbo_umido is not None else temp_ambiente) - temp_interna

    q_parede = (u_parede or 0) * area_parede * dt_seco * fator_insolacao * 24
    q_teto = (u_teto or 0) * area_teto * dt_seco * fator_insolacao * 24
    q_piso = (u_piso or 0) * area_piso * dt_umido * 24
    areas = {"area_parede": area_parede, "area_teto": area_teto, "area_piso": area_piso}
    return q_parede + q_teto + q_piso, areas


def calor_pessoas(num_pessoas, tempo_h, temp_camara):
    """Q5: qp(W/pessoa) = 272 - 6*t, convertido para kcal/h e multiplicado pelo tempo de presença."""
    if not num_pessoas:
        return 0.0
    qp_w = max(272 - 6 * temp_camara, 0)
    return num_pessoas * qp_w * W_PARA_KCAL_H * (tempo_h or 0)


def calor_iluminacao(qtd_luminarias, potencia_unit_w, tempo_h):
    """Q6 = Potência Total (calculada) x Tempo. Retorna também a potência total para o painel."""
    potencia_total_w = (qtd_luminarias or 0) * (potencia_unit_w or 0)
    q6 = potencia_total_w * W_PARA_KCAL_H * (tempo_h or 0)
    return q6, potencia_total_w


def calor_equipamentos(itens):
    """Q7 — Cenário 1 ASHRAE (motor e carga no mesmo ambiente): calor = potência x fator de
    calor rejeitado x fator de simultaneidade, x quantidade x tempo de funcionamento."""
    total = 0.0
    for it in itens:
        potencia_w = it["potencia_tipica_w"] or 0
        fu = it["fator_calor_rejeitado"] if it["fator_calor_rejeitado"] is not None else 1.0
        fs = it["fator_simultaneidade"] if it["fator_simultaneidade"] is not None else 1.0
        calor_w = potencia_w * fu * fs
        total += calor_w * W_PARA_KCAL_H * it["qtd"] * it["tempo"]
    return total


def calor_forcadores(potencia_motores_w_total):
    """Q8 — Cenário 1 ASHRAE, motor do forçador dentro da câmara junto com a carga (ar):
    calor = potência total dos motores, funcionamento contínuo (24h/24h)."""
    return (potencia_motores_w_total or 0) * W_PARA_KCAL_H * 24
