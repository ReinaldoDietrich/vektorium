def qtd_valvulas(qtd_forcadores, coletores_por_forcador):
    return (qtd_forcadores or 0) * (coletores_por_forcador or 1)
