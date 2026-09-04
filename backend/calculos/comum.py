W_PARA_KCAL_H = 0.860  # 1 W = 0,860 kcal/h


def volume_camara(largura, comprimento, pedireito):
    if not (largura and comprimento and pedireito):
        return None
    return largura * comprimento * pedireito


def capacidade_requerida(carga_total_24h, fator_seguranca_pct, tempo_func_compressores_h):
    """Carga térmica total (kcal/24h) -> capacidade que o compressor precisa entregar (kcal/h)."""
    if not tempo_func_compressores_h:
        return 0.0
    return carga_total_24h * (1 + (fator_seguranca_pct or 0) / 100) / tempo_func_compressores_h


def folga_percentual(capacidade_instalada, capacidade_requerida_un):
    if not capacidade_requerida_un:
        return 0.0
    return (capacidade_instalada - capacidade_requerida_un) / capacidade_requerida_un * 100


def carga_gas_estimada(soma_forcadores_kg, tanque_liquido_l=None):
    """Estimativa de carga de gás refrigerante do sistema: soma da carga de cada forçador
    (catálogo, por unidade x quantidade) + tanque de líquido, quando dimensionado; sem tanque
    dimensionado, a mesma soma x1,5 -- aprovado 2026-08-11 (usado no Resumo do Rack, Tela 6, e na
    Compilação Geral, Tela 8 — mesma fórmula nos dois lugares)."""
    if not soma_forcadores_kg:
        return None
    if tanque_liquido_l:
        return round(soma_forcadores_kg + tanque_liquido_l, 1)
    return round(soma_forcadores_kg * 1.5, 1)
