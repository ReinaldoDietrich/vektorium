"""Carga de degelo a gás quente — informativo para dimensionamento de tubulação.
NÃO faz parte do cálculo de carga térmica (Q1-Q9).
"""

# Constantes de material (kcal/kg·°C)
_CP_MATERIAL = {1: 0.22, 2: 0.09}  # 1=Alumínio, 2=Cobre
_LABEL_MATERIAL = {1: "Alumínio", 2: "Cobre"}

# Calor latente de fusão do gelo (kcal/kg)
_L_FUSAO_GELO = 80.0

# Fração do peso do evaporador que acumula como gelo por ciclo (regra prática)
_FATOR_GELO = 0.02


def calor_degelo_gas_quente(peso_liquido_kg, material_evaporador, temp_interna,
                             temp_final_degelo, quantidade_degelo_dia):
    """Calcula carga de degelo a gás quente (kcal/ciclo e kcal/dia).

    Retorna dict {kcal_ciclo, kcal_dia} ou None se dados insuficientes.
    """
    if not peso_liquido_kg or peso_liquido_kg <= 0:
        return None
    if temp_interna is None or temp_final_degelo is None:
        return None

    cp = _CP_MATERIAL.get(int(material_evaporador or 1), 0.22)
    qtd_degelo = quantidade_degelo_dia if quantidade_degelo_dia and quantidade_degelo_dia > 0 else 4
    dt = temp_final_degelo - temp_interna

    if dt <= 0:
        return None

    q_metal = peso_liquido_kg * cp * dt

    q_gelo = 0.0
    if temp_interna < 0:
        m_gelo = peso_liquido_kg * _FATOR_GELO
        q_gelo = m_gelo * _L_FUSAO_GELO

    kcal_ciclo = q_gelo + q_metal
    kcal_dia = kcal_ciclo * qtd_degelo

    return {"kcal_ciclo": round(kcal_ciclo, 1), "kcal_dia": round(kcal_dia, 1),
            "kcal_h": round(kcal_dia / 24, 1)}
