"""Q4 — Infiltração de Ar pelas portas (Gosney & Olama 1975 / Hendrix et al. 1989, citado no
Escopo Etapa 1). As propriedades do ar (entalpia, densidade) são estimadas por psicrometria
padrão a partir das temperaturas capturadas (fonte do ar — externo ou ambiente adjacente — e
câmara) e da UR de cada um. Fm segue a regra usual ASHRAE/IIR: 1,1 para ΔT<=11°C, 0,8 para
ΔT>11°C.

qt = q · Dt · Df · (1 − E), onde:
- Dt = fração de hora com a porta aberta (minutos/60).
- Df = fator de fluxo da porta (doorway flow factor) — constante ~0,8 do método ASHRAE/Gosney.
  NÃO é a fração de tempo aberta (erro antigo Df=Dt, que subestimava a infiltração em várias
  vezes). Ver validação contra projeto de referência.
- E = efetividade da proteção de porta.

A pressão barométrica é corrigida pela altitude do local (ISA) — afeta densidade e, portanto,
a infiltração (~−1% a cada ~120 m). Sem altitude informada, usa nível do mar.
"""
import math
from .comum import W_PARA_KCAL_H

KW_PARA_KCAL_H = 860.0
PRESSAO_ATM_PA = 101325.0
R_AR_SECO = 287.055
R_VAPOR = 461.5
DF_FLUXO_PORTA = 0.8  # fator de fluxo da porta (ASHRAE/Gosney) — constante, não é a fração de tempo


def pressao_barometrica(altitude_m):
    """Pressão atmosférica (Pa) na altitude, modelo ISA: P = P0·(1 − 2,25577e−5·h)^5,2559."""
    if not altitude_m:
        return PRESSAO_ATM_PA
    return PRESSAO_ATM_PA * (1 - 2.25577e-5 * altitude_m) ** 5.2559

EFETIVIDADE_PROTECAO = {
    "Nenhuma": 0.0,
    "Cortina de tiras": 0.875,
    "Cortina de ar": 0.6,
    "Antecâmara": 0.9,
}


def _psicrometria(temp_c, ur_pct, pressao_pa=PRESSAO_ATM_PA):
    psat = 610.94 * math.exp(17.625 * temp_c / (temp_c + 243.04))
    pv = (ur_pct / 100) * psat
    w = 0.622 * pv / max(pressao_pa - pv, 1.0)
    h = 1.006 * temp_c + w * (2501 + 1.86 * temp_c)  # kJ/kg ar seco
    rho = (pressao_pa - pv) / (R_AR_SECO * (temp_c + 273.15)) + pv / (R_VAPOR * (temp_c + 273.15))
    return h, rho


def calor_infiltracao(num_portas, porta_largura, porta_altura, freq_abertura_min_h, protecao,
                       temp_ambiente, temp_interna, ur_interna=95, ur_externa=60, altitude_m=0):
    """Q4 (kcal/24h). freq_abertura_min_h = minutos de porta aberta por hora (0-60).
    temp_ambiente/ur_externa = ar da FONTE (externo do projeto ou ambiente adjacente).
    altitude_m corrige a pressão barométrica (densidade do ar)."""
    if not (num_portas and porta_largura and porta_altura):
        return 0.0
    area_total = num_portas * porta_largura * porta_altura
    pressao = pressao_barometrica(altitude_m)
    h_amb, rho_amb = _psicrometria(temp_ambiente, ur_externa, pressao)
    h_cam, rho_cam = _psicrometria(temp_interna, ur_interna, pressao)

    delta_t = abs(temp_ambiente - temp_interna)
    fm = 0.8 if delta_t > 11 else 1.1
    g = 9.81
    razao = max(1 - rho_amb / rho_cam, 0)
    q_kw = 0.221 * area_total * (h_amb - h_cam) * rho_cam * (razao ** 0.5) * ((g * porta_altura) ** 0.5) * fm

    dt_fracao = min((freq_abertura_min_h or 0) / 60, 1.0)
    e = EFETIVIDADE_PROTECAO.get(protecao, 0.0)
    qt_kw = max(q_kw, 0) * dt_fracao * DF_FLUXO_PORTA * (1 - e)

    qt_kcal_h = qt_kw * KW_PARA_KCAL_H
    return qt_kcal_h * 24
