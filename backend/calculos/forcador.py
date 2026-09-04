"""Seleção de forçador de ar — interpolação por temperatura de evaporação, correção de ΔT e
folga, exatamente conforme validado nas Anotações da Etapa 3 e no Escopo Etapa 1."""
from .comum import folga_percentual, capacidade_requerida, W_PARA_KCAL_H


def interpolar_capacidade(pontos, temp_requerida):
    """pontos: [(temp_evaporacao, capacidade_kcal_h), ...]. Interpolação linear entre o ponto
    tabelado imediatamente acima e abaixo da temperatura requerida; fora da faixa, usa o
    extremo mais próximo (mais conservador que extrapolar)."""
    if not pontos:
        return 0.0
    pts = sorted(pontos, key=lambda p: p[0])
    for t, c in pts:
        if abs(t - temp_requerida) < 1e-9:
            return c
    abaixo = max((p for p in pts if p[0] < temp_requerida), key=lambda p: p[0], default=None)
    acima = min((p for p in pts if p[0] > temp_requerida), key=lambda p: p[0], default=None)
    if abaixo is None:
        return acima[1]
    if acima is None:
        return abaixo[1]
    t_acima, c_acima = acima
    t_abaixo, c_abaixo = abaixo
    return ((c_acima - c_abaixo) / abs(t_acima - t_abaixo)) * abs(temp_requerida - t_abaixo) + c_abaixo


def corrigir_delta_t(capacidade_no_dt_catalogo, dt_camara, dt_catalogo):
    if not dt_catalogo or dt_camara == dt_catalogo:
        return capacidade_no_dt_catalogo
    return (dt_camara / dt_catalogo) * capacidade_no_dt_catalogo


def aplicar_fatores_correcao(capacidade, fatores):
    resultado = capacidade
    for f in fatores or []:
        resultado *= f
    return resultado


def capacidade_corrigida_modelo(modelo, temp_evaporacao, dt_camara, fatores_correcao=None):
    """modelo: dict com 'capacidades': [(t,c)...] e 'dt_referencia'."""
    cap_no_evap = interpolar_capacidade(modelo["capacidades"], temp_evaporacao)
    cap_dt = corrigir_delta_t(cap_no_evap, dt_camara, modelo.get("dt_referencia"))
    return aplicar_fatores_correcao(cap_dt, fatores_correcao)


def selecionar_modelo(modelos, temp_evaporacao, dt_camara, capacidade_requerida_unitaria,
                       folga_desejada_pct, fatores_correcao=None):
    """Escolhe o menor modelo cuja folga real >= folga desejada; se nenhum atender, devolve o
    maior disponível (sistema sinaliza folga insuficiente, mas nunca bloqueia)."""
    candidatos = []
    for m in modelos:
        cap = capacidade_corrigida_modelo(m, temp_evaporacao, dt_camara, fatores_correcao)
        candidatos.append({**m, "capacidade_corrigida": cap,
                            "folga_real": folga_percentual(cap, capacidade_requerida_unitaria)})
    if not candidatos:
        return None
    candidatos.sort(key=lambda c: c["capacidade_corrigida"])
    atendem = [c for c in candidatos if c["folga_real"] >= folga_desejada_pct]
    return atendem[0] if atendem else candidatos[-1]


def selecionar_modelo_autoconsistente(modelos, temp_evaporacao, dt_camara, qtd, carga_base_24h,
                                       fator_seguranca_pct, tempo_func_compressores_h,
                                       folga_desejada_pct, fatores_correcao=None):
    """Mesma regra do selecionar_modelo (menor modelo cuja folga real >= folga desejada; se nenhum
    atender, devolve o maior disponível) — mas avalia CADA candidato contra a capacidade requerida
    que ELE MESMO gera: o motor do forçador fica dentro da câmara (Q8, Cenário 1 ASHRAE) e soma à
    carga total, então um motor mais potente aumenta a própria capacidade requerida. `carga_base_24h`
    é a carga da câmara SEM Q8 (Q1-Q7); aqui somamos o Q8 específico de cada candidato antes de
    calcular a folga dele. Isso elimina a dependência de qual candidato foi avaliado primeiro —
    aprovado 2026-08-10, substitui a abordagem anterior de 2 passadas (que comparava candidatos
    contra um cap_req "emprestado" de outro candidato, podendo descartar o menor modelo mesmo
    quando ele atendia à capacidade de forma autoconsistente)."""
    candidatos = []
    for mod in modelos:
        cap = capacidade_corrigida_modelo(mod, temp_evaporacao, dt_camara, fatores_correcao)
        motores_w_total = (mod.get("motores_w") or 0) * qtd
        q8_candidato = motores_w_total * W_PARA_KCAL_H * 24
        cap_req_candidato = capacidade_requerida(carga_base_24h + q8_candidato, fator_seguranca_pct,
                                                   tempo_func_compressores_h)
        cap_total_candidato = cap * qtd
        candidatos.append({**mod, "capacidade_corrigida": cap,
                            "q8_candidato": round(q8_candidato, 1),
                            "capacidade_requerida_candidato": round(cap_req_candidato, 1),
                            "folga_real": folga_percentual(cap_total_candidato, cap_req_candidato)})
    if not candidatos:
        return None
    candidatos.sort(key=lambda c: c["capacidade_corrigida"])
    atendem = [c for c in candidatos if c["folga_real"] >= folga_desejada_pct]
    return atendem[0] if atendem else candidatos[-1]


def trocas_de_ar(vazao_unitaria_m3h, quantidade, volume_m3):
    if not volume_m3:
        return None
    return (vazao_unitaria_m3h or 0) * quantidade / volume_m3
