# -*- coding: utf-8 -*-
"""Mapa de propagação de invalidação pai→filho para o padrão fechada=TRUE/FALSE.

Quando uma entidade PAI é salva (fechada→TRUE), todas as entidades FILHAS listadas aqui que
já estejam fechadas são marcadas como `calculo_desatualizado=True` — na próxima abertura para
edição, o cálculo será refeito com os dados atualizados do pai.

Chaves: nome do model SQLAlchemy do pai.
Valores: lista de nomes dos models filhos que dependem dele.

A propagação é de UM nível apenas (não recursiva) — se A→B→C, salvar A invalida B; salvar B
invalida C. Isso é intencional: cada nível decide quando recalcular.
"""

MAPA_INVALIDACAO = {
    "Projeto.dados_gerais": ["SistemaRefrigeracao"],
    "Projeto.clima": ["CamaraCompleto", "CamaraSimples"],
    "Projeto.estrutural": [],
    "SistemaRefrigeracao": [
        "CamaraCompleto", "CamaraSimples", "Expositor",
        "UnidadeSelecaoSistema", "RackParalelo",
    ],
    "CamaraCompleto": ["UnidadeSelecaoSistema", "RackParalelo"],
    "CamaraSimples": ["UnidadeSelecaoSistema", "RackParalelo"],
    "Expositor": ["UnidadeSelecaoSistema", "RackParalelo"],
    "RackParalelo": [],
    "UnidadeSelecaoSistema": [],
    "PainelTermico": [],
    "PortaFrigorifica": [],
    "ComposicaoPrecoItem": [],
    "CondicaoPagamentoProjeto": [],
    "ComissaoVendedorProjeto": [],
    "MargemNegociacaoProjeto": [],
}


def dependentes_de(nome_model: str) -> list[str]:
    return MAPA_INVALIDACAO.get(nome_model, [])
