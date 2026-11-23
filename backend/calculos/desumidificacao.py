"""Q9 — Desumidificação por reheat (gás quente).
Calcula a carga extra sobre o compressor quando a UR requerida pelo usuário é menor
que a UR que o ΔT do evaporador naturalmente produz (interpolada pela tabela de classes).
"""
from .infiltracao import _psicrometria, pressao_barometrica, KW_PARA_KCAL_H


def calcular_ur_projeto(dt_camara, classes):
    """Interpola linearmente a UR de projeto a partir do ΔT do evaporador e da tabela de classes.
    classes: lista de dicts com dt_evap_min, dt_evap_max, ur_min, ur_max (ou objetos com esses attrs).
    Retorna UR (%) ou None se não houver dados."""
    if dt_camara is None or not classes:
        return None
    pontos = []
    for c in classes:
        dt_min = getattr(c, 'dt_evap_min', None) if hasattr(c, 'dt_evap_min') else c.get('dt_evap_min')
        dt_max = getattr(c, 'dt_evap_max', None) if hasattr(c, 'dt_evap_max') else c.get('dt_evap_max')
        ur_min = getattr(c, 'ur_min', None) if hasattr(c, 'ur_min') else c.get('ur_min')
        ur_max = getattr(c, 'ur_max', None) if hasattr(c, 'ur_max') else c.get('ur_max')
        if None in (dt_min, dt_max, ur_min, ur_max):
            continue
        pontos.append((dt_min, ur_max))
        pontos.append((dt_max, ur_min))
    if not pontos:
        return None
    pontos.sort(key=lambda p: p[0])
    unicos = []
    for p in pontos:
        if not unicos or abs(p[0] - unicos[-1][0]) > 0.001:
            unicos.append(p)
        else:
            unicos[-1] = (unicos[-1][0], min(unicos[-1][1], p[1]))
    pontos = unicos
    dt = abs(dt_camara)
    if dt <= pontos[0][0]:
        return pontos[0][1]
    if dt >= pontos[-1][0]:
        return pontos[-1][1]
    for i in range(len(pontos) - 1):
        x0, y0 = pontos[i]
        x1, y1 = pontos[i + 1]
        if x0 <= dt <= x1:
            if abs(x1 - x0) < 0.001:
                return y0
            return y0 + (dt - x0) / (x1 - x0) * (y1 - y0)
    return pontos[-1][1]


def calor_desumidificacao(vazao_m3h, temp_ext, ur_ext, temp_int, ur_projeto, ur_requerida,
                           altitude_m=0):
    """Q9 (kcal/24h). Carga extra de desumidificação quando ur_requerida < ur_projeto.
    vazao_m3h = vazão total dos forçadores considerados (m³/h).
    Retorna a carga latente extra que o compressor precisa absorver."""
    if not vazao_m3h or ur_projeto is None or ur_requerida is None:
        return 0.0
    if ur_requerida >= ur_projeto:
        return 0.0
    pressao = pressao_barometrica(altitude_m)
    h_proj, rho_proj = _psicrometria(temp_int, ur_projeto, pressao)
    h_req, rho_req = _psicrometria(temp_int, ur_requerida, pressao)
    if h_proj <= h_req:
        return 0.0
    m_da_kg_h = vazao_m3h * rho_proj
    q_kw = m_da_kg_h * (h_proj - h_req) / 3600
    return q_kw * KW_PARA_KCAL_H * 24
