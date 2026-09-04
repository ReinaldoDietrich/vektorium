"""Banco de Dados 100% acessível, visível e editável — exigência firme do usuário. SQLAdmin
gera o CRUD completo de cada tabela automaticamente, sem precisar de tela própria por catálogo."""
from sqladmin import Admin, ModelView
from sqladmin.models import ModelViewMeta
from sqlalchemy.orm import object_session
from . import models as m


def _projeto_de(obj):
    """Acha o Projeto dono de um registro editado pelo SQLAdmin, pra bloquear edição/exclusão
    quando esse Projeto estiver com "Edição Bloqueada" (Tela 1, aprovado 2026-08-12) — mesma
    trava da API normal (ver backend/routers/_bloqueio_projeto.py), só que aqui é preciso navegar
    a cadeia manualmente (SQLAdmin edita o registro isolado, sem os relationships já carregados
    do fluxo normal da tela). Retorna None se o registro não pertence a projeto nenhum (tabela de
    catálogo global)."""
    db = object_session(obj)
    if db is None:
        return None
    if isinstance(obj, m.Projeto):
        return obj
    if isinstance(obj, m.SistemaRefrigeracao):
        return obj.projeto
    if isinstance(obj, (m.CamaraCompleto, m.CamaraSimples, m.Expositor)):
        return obj.sistema.projeto if obj.sistema else None
    if isinstance(obj, m.EquipamentoCamaraCompleto):
        c = db.get(m.CamaraCompleto, obj.camara_id)
        return _projeto_de(c) if c else None
    if isinstance(obj, m.ModuloExpositor):
        e = db.get(m.Expositor, obj.expositor_id)
        return _projeto_de(e) if e else None
    if isinstance(obj, m.ForcadorSelecaoCompleto):
        c = db.get(m.CamaraCompleto, obj.camara_id)
        return _projeto_de(c) if c else None
    if isinstance(obj, m.ForcadorSelecaoSimples):
        c = db.get(m.CamaraSimples, obj.camara_id)
        return _projeto_de(c) if c else None
    if isinstance(obj, m.ValvulaSelecaoCompleto):
        f = db.get(m.ForcadorSelecaoCompleto, obj.forcador_selecao_id)
        return _projeto_de(f) if f else None
    if isinstance(obj, m.ValvulaSelecaoSimples):
        f = db.get(m.ForcadorSelecaoSimples, obj.forcador_selecao_id)
        return _projeto_de(f) if f else None
    if isinstance(obj, (m.ComposicaoPrecoItem, m.ComissaoVendedorProjeto)):
        return db.get(m.Projeto, obj.projeto_id)
    if isinstance(obj, m.MargemNegociacaoProjeto):
        return db.get(m.Projeto, obj.projeto_id)
    return None


def _verificar_nao_bloqueado(obj):
    projeto = _projeto_de(obj)
    if projeto and projeto.fechado:
        raise Exception("Projeto com Edição Bloqueada (Tela 1) — desbloqueie antes de editar por aqui.")


async def _on_model_change(self, data, model, is_created, request):
    _verificar_nao_bloqueado(model)


async def _on_model_delete(self, model, request):
    _verificar_nao_bloqueado(model)


# Modelos que pertencem a um Projeto específico (ver _projeto_de acima) — recebem os hooks de
# bloqueio. Catálogos globais (Fabricante, LinhaForcador, tabelas de apoio etc.) nunca têm dono
# de projeto, então não fazem sentido travar por aqui (mesmo critério já usado nos endpoints da
# API — ver backend/routers/_bloqueio_projeto.py).
_MODELOS_COM_BLOQUEIO = {
    m.Projeto, m.SistemaRefrigeracao, m.CamaraCompleto, m.EquipamentoCamaraCompleto,
    m.ForcadorSelecaoCompleto, m.ValvulaSelecaoCompleto, m.CamaraSimples,
    m.ForcadorSelecaoSimples, m.ValvulaSelecaoSimples, m.Expositor, m.ModuloExpositor,
    m.ComposicaoPrecoItem, m.ComissaoVendedorProjeto, m.MargemNegociacaoProjeto,
}


def _view(model, nome, plural, categoria, colunas=None):
    attrs = {
        "name": nome, "name_plural": plural, "category": categoria,
        "column_list": colunas or [c.key for c in model.__table__.columns],
        "can_export": True,
    }
    if model in _MODELOS_COM_BLOQUEIO:
        attrs["on_model_change"] = _on_model_change
        attrs["on_model_delete"] = _on_model_delete
    # SQLAdmin só monta pk_columns/identity quando 'model' chega via kwarg de classe
    # (metaclasse ModelViewMeta), por isso a criação dinâmica usa ModelViewMeta direto.
    return ModelViewMeta(f"{model.__name__}Admin", (ModelView,), attrs, model=model)


def registrar(app, engine):
    admin = Admin(app, engine, title="Carga Térmica — Banco de Dados")

    views = [
        _view(m.Projeto, "Projeto", "Projetos", "Projeto"),
        _view(m.SistemaRefrigeracao, "Sistema de Refrigeração", "Sistemas de Refrigeração", "Projeto"),

        _view(m.Produto, "Produto", "Catálogo · Produtos", "Catálogos"),
        _view(m.TipoEmbalagem, "Tipo de Embalagem", "Catálogo · Tipos de Embalagem", "Catálogos"),
        _view(m.IsolamentoParedeTeto, "Isolamento Parede/Teto", "Catálogo · Isolamento Parede/Teto", "Catálogos"),
        _view(m.IsolamentoPiso, "Isolamento Piso", "Catálogo · Isolamento Piso", "Catálogos"),
        _view(m.TipoEquipamento, "Tipo de Equipamento", "Catálogo · Tipos de Equipamento", "Catálogos"),
        _view(m.CondicaoClimatica, "Condição Climática", "Catálogo · Clima por Cidade", "Catálogos"),
        _view(m.TabelaTipo02, "Tabela 02 (Tipo Câmara Simples)", "Catálogo · Tabela 02", "Catálogos"),
        _view(m.FatorAltura, "Fator de Altura", "Catálogo · Fator de Altura", "Catálogos"),
        _view(m.FaixaTrocasAr, "Faixa de Trocas de Ar", "Catálogo · Faixas de Trocas de Ar", "Catálogos"),
        _view(m.ClasseProduto, "Classe de Produto", "Catálogo · Classes de Produto", "Catálogos"),
        _view(m.SetorExpositor, "Setor de Expositor", "Catálogo · Setores de Expositor", "Catálogos"),
        _view(m.BancoExpositor, "Banco de Expositores", "Catálogo · Bancos de Expositores", "Catálogos"),
        _view(m.ModeloExpositor, "Modelo de Expositor", "Catálogo · Modelos de Expositor", "Catálogos"),
        _view(m.ConfiguracaoGlobal, "Configuração Global", "Configurações Globais", "Catálogos"),

        _view(m.Fabricante, "Fabricante", "Fabricantes", "Forçadores e Válvulas"),
        _view(m.LinhaForcador, "Linha de Forçador", "Linhas de Forçador", "Forçadores e Válvulas"),
        _view(m.ModeloForcador, "Modelo de Forçador", "Modelos de Forçador", "Forçadores e Válvulas"),
        _view(m.CapacidadeForcador, "Capacidade x Temp. Evaporação", "Capacidades de Forçador", "Forçadores e Válvulas"),
        _view(m.DadosEletricosForcador, "Dados Elétricos", "Dados Elétricos de Forçador", "Forçadores e Válvulas"),
        _view(m.DadosFisicosForcador, "Dados Físicos", "Dados Físicos de Forçador", "Forçadores e Válvulas"),
        _view(m.DadosDimensionaisForcador, "Dados Dimensionais", "Dados Dimensionais de Forçador", "Forçadores e Válvulas"),
        _view(m.ImportacaoCatalogo, "Importação de Catálogo", "Histórico de Importações", "Forçadores e Válvulas"),
        _view(m.ModeloValvula, "Modelo de Válvula", "Modelos de Válvula", "Forçadores e Válvulas"),

        _view(m.CamaraCompleto, "Câmara (Cálculo Completo)", "Câmaras — Cálculo Completo", "Câmaras e Expositores"),
        _view(m.EquipamentoCamaraCompleto, "Equipamento da Câmara", "Equipamentos (Câmara Completo)", "Câmaras e Expositores"),
        _view(m.ForcadorSelecaoCompleto, "Forçador Selecionado", "Forçadores Selecionados (Completo)", "Câmaras e Expositores"),
        _view(m.ValvulaSelecaoCompleto, "Válvula Selecionada", "Válvulas Selecionadas (Completo)", "Câmaras e Expositores"),
        _view(m.CamaraSimples, "Câmara (Cálculo Simples)", "Câmaras — Cálculo Simples", "Câmaras e Expositores"),
        _view(m.ForcadorSelecaoSimples, "Forçador Selecionado (Simples)", "Forçadores Selecionados (Simples)", "Câmaras e Expositores"),
        _view(m.ValvulaSelecaoSimples, "Válvula Selecionada (Simples)", "Válvulas Selecionadas (Simples)", "Câmaras e Expositores"),
        _view(m.Expositor, "Expositor", "Expositores", "Câmaras e Expositores"),
        _view(m.ModuloExpositor, "Módulo de Expositor", "Módulos de Expositor", "Câmaras e Expositores"),

        _view(m.FatorVenda, "Fator de Venda", "Fatores de Venda", "Composição de Preço"),
        _view(m.ItemComposicaoMestre, "Item Default (mestre)", "Itens Default (mestre)", "Composição de Preço"),
        _view(m.Vendedor, "Vendedor", "Vendedores", "Composição de Preço"),
        _view(m.ComposicaoPrecoItem, "Item de Composição (por projeto)", "Itens de Composição (por projeto)", "Composição de Preço"),
        _view(m.ComissaoVendedorProjeto, "Comissão Vendedor x Projeto", "Comissões Vendedor x Projeto", "Composição de Preço"),
        _view(m.MargemNegociacaoProjeto, "Margem de Negociação (por projeto)", "Margens de Negociação", "Composição de Preço"),
    ]
    for v in views:
        admin.add_view(v)
    return admin
