# -*- coding: utf-8 -*-
"""Motor de cálculo da Composição de Preço (ver "Documentos de Criação/Tabela Composição
Preço.xlsx" — planilha-exemplo — e o escopo aprovado na conversa).

Fórmula de preço de venda = MARKUP DIVISOR (literatura de formação de preço de venda, não o
markup multiplicador ingênuo): Preço = Custo / (1 - %despesas_variaveis - %margem_desejada).
Aqui: %despesas_variaveis = Impostos% + Comissão%, %margem_desejada = Margem de Contribuição%.

Por item (linha da Composição de Preço):
    G (Custo Total)              = D (Quantidade) x F (Custo Unitário)
    TOTAL% do fator               = pct_impostos + pct_comissao + pct_margem
    H (Fator de Venda)            = 1 / (1 - TOTAL%)
    I (Margem Contribuição R$)    = G x pct_margem
    J (Impostos R$)               = G x pct_impostos
    K (Comissões R$)              = G x pct_comissao
    L (Valor unit. venda)         = F x H
    M (Valor total venda)         = G x H
    N (Valor c/ Margem Negociação)= M x (1 + margem_negociacao_projeto)

Resumo: agrupado por bloco (fixo, ver BLOCOS_COMPOSICAO) e, dentro de cada bloco, por Centro de
Custo — subtotal por bloco + Total Geral.

Comissão REAL do vendedor (distinta da "Comissões R$" por item, que é só previsão embutida no
preço): Comissao_vendedor = percentual_do_vendedor_no_projeto x N_total_geral.

DRE do projeto (estrutura padrão de DRE simplificada, nível de projeto):
    Receita Bruta de Vendas          = N_total_geral
    (-) Impostos sobre Vendas        = J_total_geral
    (=) Receita Líquida
    (-) Custo dos Materiais/Serviços = G_total_geral
    (=) Lucro Bruto
    (-) Comissões (reais, por vendedor)
    (=) Resultado do Projeto
"""
import datetime
import re
from sqlalchemy.orm import Session
from . import models as m

BLOCOS_COMPOSICAO = [
    "Equipamentos",
    "Materiais Mecânicos",
    "Materiais Elétricos",
    "Painéis Térmicos",
    "Mão de Obra",
    "Outros Serviços/ Materiais",
    "Fretes e Transporte Vertical",
    "Comissões por Indicação de Negócio",
]

# Bloco especial, gerado 100% automático (ver sincronizar_comissoes_indicacao) — nunca recebe
# item do mestre (ItemComposicaoMestre) nem entra na Lista de Materiais e Equipamentos (não é
# material/equipamento, é receita de comissão).
BLOCO_COMISSOES_INDICACAO = "Comissões por Indicação de Negócio"


def _eh_fator_comissao(fator: "m.FatorVenda | None") -> bool:
    """"Tipo" do Fator é texto livre digitado pelo usuário (Tela D) — comparação sem depender de
    maiúscula/minúscula, pra não quebrar silenciosamente se digitar "COMISSÃO"/"comissão"/etc.
    (bug real reportado 2026-08-05: usuário digitou "COMISSÃO", comparação exata nunca batia)."""
    return bool(fator) and (fator.tipo or "").strip().lower() == "comissão"


def _fator_percentuais(fator: "m.FatorVenda | None"):
    if not fator:
        return 0.0, 0.0, 0.0, 1.0
    impostos = fator.pct_impostos or 0
    comissao = fator.pct_comissao or 0
    margem = fator.pct_margem or 0
    total = impostos + comissao + margem
    fator_venda = 1 / (1 - total) if total < 1 else None
    return impostos, comissao, margem, fator_venda


def calcular_item(item: "m.ComposicaoPrecoItem", margem_negociacao_pct: float) -> dict:
    """Calcula as colunas F-N de UM item. Não persiste nada — cálculo em memória, sempre a
    partir dos valores atuais gravados (quantidade/custo_unitario/fator).

    Fator tipo "Comissão" (repasse a preço de fábrica — o revendedor emite NF ao cliente pelo
    custo e recebe comissão do fabricante por fora, com NF de serviço pro fabricante): o item em
    si não leva imposto/comissão/margem/negociação nenhuma (Valor de Venda = Custo). A receita
    real dessa venda é lançada à parte, agregada por fabricante, no bloco
    BLOCO_COMISSOES_INDICACAO (ver sincronizar_comissoes_indicacao).

    Item DAQUELE bloco (a linha agregada em si) não é "vendido" com markup nenhum — não faz
    sentido replicar a fórmula de Fator de Venda (H = 1/(1-total%)) em cima de uma receita que já
    é a comissão em si, e Comissões (R$) fica sempre 0 aqui (senão contaria a % de comissão do
    Fator duas vezes — uma pro valor da linha, outra pro campo Comissões). Só Margem de
    Contribuição e Impostos seguem o % do próprio Fator, exatamente como o usuário pediu
    (2026-08-05); Valor de Venda = Custo (sem fator_venda, sem margem de negociação)."""
    qtd = item.quantidade or 0
    custo_unit = item.custo_unitario or 0
    custo_total = qtd * custo_unit
    repasse = item.bloco != BLOCO_COMISSOES_INDICACAO and _eh_fator_comissao(item.fator)
    if repasse:
        fator_venda = 1.0
        margem_r = impostos_r = comissao_r = 0.0
        valor_unit_venda = custo_unit
        valor_total_venda = custo_total
        valor_c_negociacao = custo_total
    elif item.bloco == BLOCO_COMISSOES_INDICACAO:
        # Fator dessa linha é escolha LIVRE do usuário (ver sincronizar_comissoes_indicacao — só
        # sugere um Fator na criação, nunca sobrescreve depois) — Custo Total AQUI é a Receita
        # Bruta real (o que a empresa efetivamente recebeu de comissão do fabricante). Impostos/
        # Margem/Comissão são DEDUÇÕES de dentro dessa receita (Lei 6.404/76 art. 187 e CPC 26 —
        # Receita Líquida = Receita Bruta MENOS deduções, nunca receita bruta + tributo em cima).
        # Valor de Venda = Custo, sempre — não existe markup nem soma aqui, é dinheiro que já
        # entrou; somar imposto/comissão em cima dele inflava a receita além do que foi realmente
        # recebido (erro corrigido 2026-08-05, revertendo a "soma" que eu tinha feito antes)."""
        margem_pct = item.fator.pct_margem or 0 if item.fator else 0
        impostos_pct = item.fator.pct_impostos or 0 if item.fator else 0
        comissao_pct = item.fator.pct_comissao or 0 if item.fator else 0
        fator_venda = 1.0
        margem_r = custo_total * margem_pct
        impostos_r = custo_total * impostos_pct
        comissao_r = custo_total * comissao_pct
        valor_unit_venda = custo_unit
        valor_total_venda = custo_total
        valor_c_negociacao = custo_total
    else:
        impostos_pct, comissao_pct, margem_pct, fator_venda = _fator_percentuais(item.fator)
        if fator_venda is None:
            # soma de percentuais >= 100% — configuração inválida do Fator, não dá pra formar preço.
            margem_r = impostos_r = comissao_r = valor_unit_venda = valor_total_venda = valor_c_negociacao = None
        else:
            valor_unit_venda = custo_unit * fator_venda
            valor_total_venda = custo_total * fator_venda
            # Base do R$ de cada percentual é o Valor de Venda (M), não o Custo (G) — é assim que
            # o próprio Fator de Venda (H = 1/(1-total%)) é derivado no método Markup Divisor
            # (literatura de formação de preço de venda): só bate Custo + Margem + Impostos +
            # Comissões = Valor de Venda se cada parcela for M x pct (aprovado 2026-08-10, bug real
            # antes usava G x pct e a soma nunca fechava com o Valor de Venda mostrado).
            margem_r = valor_total_venda * margem_pct
            impostos_r = valor_total_venda * impostos_pct
            comissao_r = valor_total_venda * comissao_pct
            valor_c_negociacao = valor_total_venda * (1 + (margem_negociacao_pct or 0))
    return {
        "id": item.id, "bloco": item.bloco, "descricao": item.descricao,
        "fabricante": item.fabricante, "observacao": item.observacao,
        "centro_custo_id": item.centro_custo_id,
        "centro_custo_codigo": item.centro_custo.codigo if item.centro_custo else None,
        "centro_custo_descricao": item.centro_custo.descricao if item.centro_custo else None,
        "unidade": item.unidade,
        "fator_id": item.fator_id, "fator_codigo": item.fator.codigo if item.fator else None,
        "quantidade": qtd, "custo_unitario": custo_unit, "custo_total": custo_total,
        "fator_venda": fator_venda,
        "margem_contribuicao": margem_r, "impostos": impostos_r, "comissoes": comissao_r,
        "valor_unit_venda": valor_unit_venda, "valor_total_venda": valor_total_venda,
        "valor_venda_negociacao": valor_c_negociacao,
        "origem": item.origem, "ordem": item.ordem,
        # Checkbox "considerar no orçamento" (Tela 10, aprovado 2026-08-12): item continua
        # calculado e visível no bloco normalmente; só é excluído do Resumo por Bloco/Tabela de
        # Orçamento/DRE/Comissionamento quando False (ver resumo_por_bloco, dre_projeto,
        # comissionamento, valor_total_proposta — todos filtram por esse campo).
        "incluir_orcamento": item.incluir_orcamento,
        # CPC 47 (Res. CFC NBC TG 47) B34-B38 — empresa age como AGENTE nesse item (repasse a
        # preço de fábrica): não reconhece receita nem custo pelo valor bruto do negócio, só pela
        # comissão líquida (linha agregada em BLOCO_COMISSOES_INDICACAO). Usado pra excluir este
        # item do Receita de Vendas / Custo do DRE e da base do comissionamento do vendedor —
        # ver _totais_liquidos/dre_projeto/comissionamento (corrigido 2026-08-05).
        "repasse": repasse,
        "fechada": item.fechada,
    }


def _margem_negociacao(db: Session, projeto_id: int) -> float:
    reg = db.get(m.MargemNegociacaoProjeto, projeto_id)
    return reg.percentual if reg else 0.05


def sincronizar_equipamentos(db: Session, projeto_id: int):
    """Sincroniza o bloco "Equipamentos" com a lista gerada pela Tela 10 (mesma fonte —
    _gerar_equipamentos, que já reusa a Compilação Geral) — cria os itens que faltam (custo
    zerado, usuário preenche), atualiza quantidade/descrição dos que já existem (chave =
    identidade estável do item, ver `chave` em tela10.py — não mais a descrição completa, que pro
    Rack Paralelo muda a cada recálculo). Item cujo equipamento sumiu do projeto é apagado
    automaticamente — SÓ se ainda estiver com custo_unitario zerado (nunca precificado, lixo
    puro); um órfão com preço já digitado pelo usuário nunca é apagado sozinho, pra não destruir
    precificação real (mesmo padrão de sincronizar_paineis_portas/sincronizar_luminarias —
    aprovado 2026-08-10, antes esse bloco nunca apagava órfão nenhum)."""
    from .routers.tela10 import _gerar_equipamentos
    _, equipamentos = _gerar_equipamentos(db, projeto_id)
    existentes = {i.chave_sistema: i for i in
                  db.query(m.ComposicaoPrecoItem)
                  .filter_by(projeto_id=projeto_id, bloco="Equipamentos", origem="sistema").all()}
    ordem_max = db.query(m.ComposicaoPrecoItem).filter_by(projeto_id=projeto_id, bloco="Equipamentos").count()
    chaves_atuais = set()
    for eq in equipamentos:
        # `chave` (aprovado 2026-08-08): identidade estável (ex.: "Rack Paralelo — Sistema LTB"),
        # separada da descrição exibida — antes usava a descrição inteira como chave, e como a
        # descrição do Rack embute capacidade/modelo recalculados, cada ajuste de Folga Técnica/
        # Motor criava um item NOVO em vez de atualizar o existente (bug real, projeto 2026.027).
        chave = eq.get("chave") or eq["descricao"]
        chaves_atuais.add(chave)
        if chave in existentes:
            existentes[chave].quantidade = eq["quantidade"]
            existentes[chave].fabricante = eq.get("fabricante")
            existentes[chave].descricao = eq["descricao"]
            if not existentes[chave].unidade:
                existentes[chave].unidade = "un"
        else:
            db.add(m.ComposicaoPrecoItem(
                projeto_id=projeto_id, bloco="Equipamentos", descricao=eq["descricao"],
                fabricante=eq.get("fabricante"), unidade="un",
                quantidade=eq["quantidade"], custo_unitario=0, origem="sistema",
                chave_sistema=chave, ordem=ordem_max))
            ordem_max += 1
    for chave, item in existentes.items():
        if chave not in chaves_atuais and not item.custo_unitario:
            db.delete(item)
    db.commit()


def sincronizar_paineis_portas(db: Session, projeto_id: int):
    """Sincroniza o bloco "Painéis Térmicos" com o resumo calculado na Tela 7 (Painéis/Portas —
    ver calc_paineis_portas.montar_resumo, modo "total"): painéis/isolamento agrupados por
    ESPESSURA (produto real que se compra — produtos iguais somam numa linha só, produtos
    diferentes ficam em linhas separadas), portas agrupadas por padrão (modelo+dimensão, ver
    _portas_por_padrao — igual em qualquer modo). Antes usava modo "painel_portas_geral", que
    agrupava painéis por Id.Painel (código de instância tipo P01/T01) — gerava uma linha quase-
    duplicada por posição de placa em vez de uma por produto, deixando a Composição de Preço e a
    Tabela de Orçamento enormes (bug real reportado 2026-08-06, corrigido pra bater com o mesmo
    resumo agrupado que a Tela 7 já mostra).

    Mesmo padrão de sincronizar_equipamentos: cria os itens que faltam (custo zerado), atualiza
    quantidade dos que já existem (chave = descrição/item do resumo). A troca de modo muda a
    chave das linhas de painel/isolamento (de código de instância pra espessura) — as linhas
    antigas viram órfãs; são apagadas automaticamente SÓ se ainda estiverem com custo_unitario
    zerado (nunca precificadas, lixo puro); uma órfã com preço já digitado pelo usuário nunca é
    apagada sozinha (evita destruir preço real — mesma cautela de sempre)."""
    from .routers.paineis_portas import montar_resumo
    projeto = db.get(m.Projeto, projeto_id)
    resumo = montar_resumo(db, projeto, "total")
    # "item" (painéis/piso, ver calc_paineis_portas._linha) ou "descricao" (portas, ver
    # _portas_por_padrao) — formatos de linha diferentes conforme a origem.
    # Ordem sempre igual à da Tela 7 (painéis parede/teto → isolamento de piso → portas) —
    # reatribuída em TODA sincronização (não só nos itens novos), senão um item novo entra no fim
    # da lista com ordem sequencial enquanto os já existentes mantêm a ordem antiga, embaralhando
    # a exibição (bug real reportado 2026-08-06).
    linhas = resumo["paineis_parede_teto"] + resumo["isolamento_piso"] + resumo["portas"]
    existentes = {i.chave_sistema: i for i in
                  db.query(m.ComposicaoPrecoItem)
                  .filter_by(projeto_id=projeto_id, bloco="Painéis Térmicos", origem="sistema").all()}
    chaves_atuais = set()
    for idx, linha in enumerate(linhas):
        if "item" in linha:
            chave = linha["item"]
        else:
            # Porta: id_porta+descricao sozinhos podem repetir entre grupos com tensão/observação
            # diferentes (não fazem parte da descrição composta) — a chave/rótulo precisa incluir
            # os dois pra não colidir duas linhas reais numa só.
            partes = [linha["id_porta"], linha["descricao"]]
            if linha.get("tensao"):
                partes.append(linha["tensao"])
            if linha.get("observacoes"):
                partes.append(f"({linha['observacoes']})")
            chave = " - ".join(partes)
        chaves_atuais.add(chave)
        if chave in existentes:
            existentes[chave].quantidade = linha["quantidade"]
            existentes[chave].unidade = linha["unidade"]
            existentes[chave].ordem = idx
        else:
            db.add(m.ComposicaoPrecoItem(
                projeto_id=projeto_id, bloco="Painéis Térmicos", descricao=chave,
                unidade=linha["unidade"], quantidade=linha["quantidade"],
                custo_unitario=0, origem="sistema", chave_sistema=chave, ordem=idx))
    for chave, item in existentes.items():
        if chave not in chaves_atuais and not item.custo_unitario:
            db.delete(item)
    db.commit()


def sincronizar_luminarias(db: Session, projeto_id: int):
    """Sincroniza o bloco "Outros Serviços/ Materiais" com o resumo somatório de luminárias da
    Tela 11 (ver luminotecnico.montar_estudo, "resumo_por_modelo") -- agrupado por MODELO (o que
    se compra de fato, não por potência -- aprovado 2026-08-10). Fabricante vem de
    LookupLampada.fabricante (Configurações — Tela 11 Cadastro Lâmpadas); se não preenchido lá,
    fica em branco aqui pro usuário completar manual. Mesmo padrão de cria/atualiza/apaga órfã sem
    preço de sincronizar_paineis_portas."""
    from .routers.luminotecnico import montar_estudo
    estudo = montar_estudo(db, projeto_id)
    linhas = estudo["resumo_por_modelo"]
    existentes = {i.chave_sistema: i for i in
                  db.query(m.ComposicaoPrecoItem)
                  .filter_by(projeto_id=projeto_id, bloco="Outros Serviços/ Materiais", origem="sistema").all()}
    chaves_atuais = set()
    for idx, linha in enumerate(linhas):
        chave = linha["modelo_luminaria"]
        chaves_atuais.add(chave)
        if chave in existentes:
            existentes[chave].quantidade = linha["qtd_total"]
            existentes[chave].fabricante = linha["fabricante"]
            existentes[chave].ordem = idx
        else:
            db.add(m.ComposicaoPrecoItem(
                projeto_id=projeto_id, bloco="Outros Serviços/ Materiais", descricao=chave,
                fabricante=linha["fabricante"], unidade="un", quantidade=linha["qtd_total"],
                custo_unitario=0, origem="sistema", chave_sistema=chave, ordem=idx))
    for chave, item in existentes.items():
        if chave not in chaves_atuais and not item.custo_unitario:
            db.delete(item)
    db.commit()


def sincronizar_comissoes_indicacao(db: Session, projeto_id: int):
    """Agrega, por Fabricante, a comissão de indicação de negócio de todo item com Fator tipo
    "Comissão" (repasse a preço de fábrica — ver calcular_item) num item só no bloco
    BLOCO_COMISSOES_INDICACAO: quantidade sempre 1, custo = soma de (%Comissão do Fator × Custo
    Total) de cada item do fabricante. O Fator da linha agregada é escolha LIVRE do usuário (só
    sugerido — herdado dos itens de origem — na primeira criação da linha; depois disso nunca
    mais sobrescrito, representa os custos que incidem sobre a comissão recebida: imposto,
    comissão ao vendedor — ver calcular_item, ajustado 2026-08-05).
    Recalcula do zero a cada chamada (custo é 100% derivado, nunca editado à mão — só o Fator é).
    Diferente dos outros sincronizadores (que nunca tocam num item que sumiu, pra não perder
    preço digitado à mão): aqui não tem preço digitado nenhum pra perder — se um fabricante
    deixa de ter item de comissão, a linha é APAGADA (nunca fica lançamento fantasma parado,
    2026-08-05)."""
    itens = (db.query(m.ComposicaoPrecoItem)
             .filter_by(projeto_id=projeto_id)
             .filter(m.ComposicaoPrecoItem.bloco != BLOCO_COMISSOES_INDICACAO)
             .filter(m.ComposicaoPrecoItem.fator_id.isnot(None)).all())
    grupos = {}  # fabricante -> {"soma": float, "fator_id": int}
    for it in itens:
        if not _eh_fator_comissao(it.fator):
            continue
        fab = it.fabricante or "—"
        custo_total = (it.quantidade or 0) * (it.custo_unitario or 0)
        comissao = custo_total * (it.fator.pct_comissao or 0)
        g = grupos.setdefault(fab, {"soma": 0.0, "fator_id": it.fator_id})
        g["soma"] += comissao
        g["fator_id"] = it.fator_id

    existentes = {i.chave_sistema: i for i in
                  db.query(m.ComposicaoPrecoItem)
                  .filter_by(projeto_id=projeto_id, bloco=BLOCO_COMISSOES_INDICACAO, origem="sistema").all()}
    ordem_max = db.query(m.ComposicaoPrecoItem).filter_by(projeto_id=projeto_id, bloco=BLOCO_COMISSOES_INDICACAO).count()
    for fab, g in grupos.items():
        chave = f"comissao-indicacao::{fab}"
        if chave in existentes:
            item = existentes[chave]
            item.custo_unitario = g["soma"]
            item.fabricante = fab
            item.quantidade = 1
            # fator_id NÃO é mais sobrescrito aqui (só sugerido na criação, abaixo) — nessa
            # linha o usuário escolhe livremente o Fator que representa os custos que incidem
            # sobre a comissão recebida (imposto, comissão ao vendedor — ver calcular_item),
            # independente do Fator dos itens de origem (2026-08-05).
        else:
            db.add(m.ComposicaoPrecoItem(
                projeto_id=projeto_id, bloco=BLOCO_COMISSOES_INDICACAO,
                descricao=f"Comissão indicação de negócio - {fab}", fabricante=fab,
                quantidade=1, custo_unitario=g["soma"], fator_id=g["fator_id"],
                origem="sistema", chave_sistema=chave, ordem=ordem_max))
            ordem_max += 1

    # Fabricante que ficou sem item de comissão nenhum (mudou o Fator, apagou o item etc.) —
    # apaga a linha, nunca deixa lançamento fantasma parado ali (2026-08-05).
    chaves_atuais = {f"comissao-indicacao::{fab}" for fab in grupos}
    for chave, item in existentes.items():
        if chave not in chaves_atuais:
            db.delete(item)
    db.commit()


def restaurar_padroes(db: Session, projeto_id: int, bloco: str | None = None):
    """Recopia do mestre (ItemComposicaoMestre) os itens "default" que estiverem faltando no
    projeto — nunca duplica os que já existem (chave = descrição), nunca mexe no mestre."""
    q = db.query(m.ItemComposicaoMestre)
    if bloco:
        q = q.filter_by(bloco=bloco)
    mestre = q.order_by(m.ItemComposicaoMestre.ordem).all()
    existentes_desc = {i.descricao for i in
                        db.query(m.ComposicaoPrecoItem).filter_by(projeto_id=projeto_id).all()}
    ordem_por_bloco = {}
    criados = 0
    for it in mestre:
        if it.descricao in existentes_desc:
            continue
        cc_id = it.centro_custo_id
        if not cc_id and it.centro_custo_codigo:
            centro = (db.query(m.CentroCusto)
                      .filter_by(codigo=it.centro_custo_codigo).first())
            cc_id = centro.id if centro else None
        ordem = ordem_por_bloco.get(it.bloco)
        if ordem is None:
            ordem = db.query(m.ComposicaoPrecoItem).filter_by(projeto_id=projeto_id, bloco=it.bloco).count()
        db.add(m.ComposicaoPrecoItem(
            projeto_id=projeto_id, bloco=it.bloco, descricao=it.descricao,
            quantidade=1, custo_unitario=it.custo_unitario_padrao or 0,
            fator_id=it.fator_id, centro_custo_id=cc_id,
            origem="default", chave_sistema=None, ordem=ordem))
        ordem_por_bloco[it.bloco] = ordem + 1
        criados += 1
    db.commit()
    return criados


def montar_composicao(db: Session, projeto_id: int) -> dict:
    sincronizar_equipamentos(db, projeto_id)
    sincronizar_paineis_portas(db, projeto_id)
    sincronizar_luminarias(db, projeto_id)
    sincronizar_comissoes_indicacao(db, projeto_id)
    margem_neg = _margem_negociacao(db, projeto_id)
    itens = (db.query(m.ComposicaoPrecoItem).filter_by(projeto_id=projeto_id)
             .order_by(m.ComposicaoPrecoItem.bloco, m.ComposicaoPrecoItem.ordem, m.ComposicaoPrecoItem.id).all())
    calculados = [calcular_item(i, margem_neg) for i in itens]
    blocos = {b: [] for b in BLOCOS_COMPOSICAO}
    for c in calculados:
        blocos.setdefault(c["bloco"], []).append(c)
    return {"blocos": blocos, "margem_negociacao_pct": margem_neg}


def _totais_liquidos(dados: dict) -> dict:
    """Totais REAIS da empresa — exclui todo item marcado "repasse" (ver calcular_item, CPC 47
    B34-B38: empresa age como agente nesses itens, não reconhece receita/custo pelo valor bruto
    do negócio) e exclui o próprio bloco de Comissões (que tem tratamento à parte — é receita
    líquida em si, ver sincronizar_comissoes_indicacao). Usado pelo DRE e pela base real do
    comissionamento do vendedor — nenhum dos dois pode contar o valor bruto de um repasse
    (2026-08-06)."""
    receita_vendas = custo = impostos_vendas = 0.0
    for bloco, itens in dados["blocos"].items():
        if bloco == BLOCO_COMISSOES_INDICACAO:
            continue
        for it in itens:
            if it.get("repasse") or not it.get("incluir_orcamento", True):
                continue
            receita_vendas += it["valor_venda_negociacao"] or 0
            custo += it["custo_total"] or 0
            impostos_vendas += it["impostos"] or 0
    return {"receita_vendas": receita_vendas, "custo": custo, "impostos_vendas": impostos_vendas}


def lista_materiais(db: Session, projeto_id: int, bloco: str | None = None,
                     centro_custo_id: int | None = None, fabricante: str | None = None) -> list[dict]:
    """"Lista de Materiais e Equipamentos" — versão simples (sem valores financeiros) da
    Composição de Preço, pra pedido de orçamento a fornecedores (Imprimir/Exportar Excel da
    Tela 10): Nº, Descrição, Fabricante, Centro de Custo, Unid., Quantidade. Filtra pelos mesmos
    3 filtros já usados na tela (Bloco/Centro de Custo/Fabricante)."""
    montar_composicao(db, projeto_id)  # garante Equipamentos/Painéis Térmicos sincronizados
    q = (db.query(m.ComposicaoPrecoItem).filter_by(projeto_id=projeto_id)
         .filter(m.ComposicaoPrecoItem.bloco != BLOCO_COMISSOES_INDICACAO)
         .order_by(m.ComposicaoPrecoItem.bloco, m.ComposicaoPrecoItem.ordem, m.ComposicaoPrecoItem.id))
    if bloco:
        q = q.filter_by(bloco=bloco)
    if centro_custo_id:
        q = q.filter_by(centro_custo_id=centro_custo_id)
    if fabricante:
        q = q.filter_by(fabricante=fabricante)
    itens = q.all()
    return [{"numero": i, "descricao": it.descricao, "fabricante": it.fabricante,
             "centro_custo": it.centro_custo.codigo if it.centro_custo else None,
             "unidade": it.unidade, "quantidade": it.quantidade}
            for i, it in enumerate(itens, start=1)]


_CAMPOS_SOMA = ("custo_total", "impostos", "comissoes", "margem_contribuicao",
                "valor_total_venda", "valor_venda_negociacao")


def resumo_por_bloco(db: Session, projeto_id: int, dados: dict | None = None) -> dict:
    """Uma linha por Centro de Custo CADASTRADO no bloco (código + descrição do próprio Centro de
    Custo — não do item), sempre presente mesmo com R$ 0,00 se ainda não tem item lançado. Itens
    sem Centro de Custo atribuído entram numa linha agrupada "Sem Centro de Custo" (só aparece se
    houver pelo menos 1 item nessa situação).

    `dados` opcional = resultado já pronto de montar_composicao — evita rodar as sincronizações
    (Equipamentos/Painéis/Comissões, todas pesadas) de novo quando quem chama já tem os dados na
    mão (ver obter_tudo — consolidado, senão cada tela virava 3-4 recomputações completas por
    edição de campo, bug real de lentidão reportado 2026-08-05)."""
    if dados is None:
        dados = montar_composicao(db, projeto_id)
    centros = (db.query(m.CentroCusto)
               .order_by(m.CentroCusto.ordem, m.CentroCusto.id).all())
    resultado = []
    total_geral = {c: 0 for c in _CAMPOS_SOMA}
    for bloco in BLOCOS_COMPOSICAO:
        # Checkbox "considerar no orçamento" (aprovado 2026-08-12): item desmarcado nunca entra
        # no Resumo por Bloco (nem no Total Geral, nem no subtotal usado por DRE/Comissionamento
        # — ver _totais_liquidos e comissionamento, que leem esse mesmo total_geral). Continua no
        # bloco em si (dados["blocos"]), só sai daqui.
        itens = [it for it in dados["blocos"].get(bloco, []) if it.get("incluir_orcamento", True)]
        por_cc_id = {}
        sem_cc = {"centro_custo": None, "descricao": "Sem Centro de Custo",
                   **{c: 0 for c in _CAMPOS_SOMA}}
        tem_item_sem_cc = False
        for it in itens:
            if it["centro_custo_id"] is None:
                tem_item_sem_cc = True
                for campo in _CAMPOS_SOMA:
                    sem_cc[campo] += (it[campo] or 0)
            else:
                acc = por_cc_id.setdefault(it["centro_custo_id"], {c: 0 for c in _CAMPOS_SOMA})
                for campo in _CAMPOS_SOMA:
                    acc[campo] += (it[campo] or 0)
        linhas = []
        for cc in centros:
            # O Resumo por Bloco sempre mostra todo item lançado, sem esconder nada — inclusive
            # comissão com Centro de Custo escolhido em "Agrupar valor em" continua aparecendo
            # normalmente aqui, dentro do bloco Comissões (aprovado 2026-08-10). Esconder a
            # comissão como linha própria e somar por dentro de outro Centro de Custo só acontece
            # na Tabela de Orçamento (ver t17_calcularTabelaOrcamento) e no Total da Proposta (ver
            # valor_total_proposta) — nunca aqui.
            acc = por_cc_id.get(cc.id, {c: 0 for c in _CAMPOS_SOMA})
            if not any(acc.values()):
                continue  # sem uso nesse bloco — não cria linha zerada repetida em todo bloco
            linhas.append({"centro_custo": cc.codigo, "descricao": cc.descricao, **acc})
        if tem_item_sem_cc:
            linhas.append(sem_cc)
        subtotal = {c: 0 for c in _CAMPOS_SOMA}
        for linha in linhas:
            for campo in _CAMPOS_SOMA:
                subtotal[campo] += linha[campo]
        for campo in total_geral:
            total_geral[campo] += subtotal[campo]
        resultado.append({"bloco": bloco, "centros_custo": linhas, "subtotal": subtotal})
    return {"blocos": resultado, "total_geral": total_geral}


def comissionamento(db: Session, projeto_id: int, dados: dict | None = None,
                     resumo: dict | None = None) -> dict:
    """`dados`/`resumo` opcionais — evita recalcular tudo de novo quando quem chama já tem (ver
    obter_tudo).

    O comissionamento NÃO calcula um valor próprio — ele DISTRIBUI o total já orçado na
    composição (soma da coluna "Comissões (R$)" de todo item, calculada item a item pelo Fator de
    cada um) entre os vendedores vinculados, proporcional ao percentual de cada um. Antes disso,
    "Comissionamento" calculava seu PRÓPRIO valor (% sobre Receita Líquida) — número
    desconectado do que a composição já previa, podendo pagar mais do que o orçado (bug real
    reportado 2026-08-06: orçamento previa R$89,40 de comissão e o sistema calculava R$406,77 pra
    pagar)."""
    if dados is None:
        dados = montar_composicao(db, projeto_id)
    if resumo is None:
        resumo = resumo_por_bloco(db, projeto_id, dados=dados)
    total_orcado = resumo["total_geral"]["comissoes"]
    vinculos = (db.query(m.ComissaoVendedorProjeto).filter_by(projeto_id=projeto_id).all())
    soma_percentuais = sum((v.percentual or 0) for v in vinculos)
    itens = []
    for v in vinculos:
        pct = v.percentual or 0
        fatia = (pct / soma_percentuais) if soma_percentuais else 0.0
        itens.append({"id": v.id, "vendedor_id": v.vendedor_id,
                      "vendedor_nome": v.vendedor.nome if v.vendedor else None,
                      "percentual": pct, "comissao_r": total_orcado * fatia,
                      "fechada": v.fechada})
    return {"itens": itens, "total_venda": total_orcado,
            "total_comissoes": sum(i["comissao_r"] for i in itens)}


def dre_projeto(db: Session, projeto_id: int, dados: dict | None = None,
                 resumo: dict | None = None, com: dict | None = None) -> dict:
    """DRE do projeto — Receita Bruta Total é a soma de 2 receitas de natureza (e regime
    tributário) diferentes, por isso vêm decompostas: Receita de Vendas (produtos, ICMS) e
    Receita de Comissões de Indicação de Negócio (serviço/intermediação, ISS — ver
    BLOCO_COMISSOES_INDICACAO), cada uma com seu próprio Imposto. Daí em diante o DRE segue único
    (Receita Líquida/Lucro Bruto/Resultado), conforme confirmado com o usuário 2026-08-05.

    Item de repasse (empresa age como agente — ver calcular_item/_totais_liquidos, CPC 47 B34-B38)
    NÃO entra em Receita de Vendas nem em Custo — só a comissão líquida recebida é receita real da
    empresa. Sem isso, um repasse de R$149.000 (venda direta fábrica, sem markup) inflava Receita
    Bruta E Custo com dinheiro que nunca foi da empresa (corrigido 2026-08-06).

    `dados`/`resumo`/`com` opcionais — evita recalcular tudo de novo (ver obter_tudo)."""
    if dados is None:
        dados = montar_composicao(db, projeto_id)
    if resumo is None:
        resumo = resumo_por_bloco(db, projeto_id, dados=dados)
    if com is None:
        com = comissionamento(db, projeto_id, dados=dados, resumo=resumo)
    totais = _totais_liquidos(dados)
    bloco_comissao = next((b for b in resumo["blocos"] if b["bloco"] == BLOCO_COMISSOES_INDICACAO), None)
    sub_comissao = bloco_comissao["subtotal"] if bloco_comissao else {c: 0 for c in _CAMPOS_SOMA}

    receita_vendas = totais["receita_vendas"]
    receita_comissoes = sub_comissao["valor_venda_negociacao"]
    receita_bruta = receita_vendas + receita_comissoes
    impostos_vendas = totais["impostos_vendas"]
    impostos_comissoes = sub_comissao["impostos"]
    impostos = impostos_vendas + impostos_comissoes
    receita_liquida = receita_bruta - impostos
    custo = totais["custo"]
    lucro_bruto = receita_liquida - custo
    comissoes_reais = com["total_comissoes"]
    resultado = lucro_bruto - comissoes_reais
    margem_liquida_pct = (resultado / receita_bruta) if receita_bruta else None
    return {
        "receita_vendas": receita_vendas, "receita_comissoes": receita_comissoes,
        "receita_bruta": receita_bruta,
        "impostos_vendas": impostos_vendas, "impostos_comissoes": impostos_comissoes,
        "impostos": impostos, "receita_liquida": receita_liquida,
        "custo": custo, "lucro_bruto": lucro_bruto, "comissoes": comissoes_reais,
        "resultado": resultado, "margem_liquida_pct": margem_liquida_pct,
    }


def obter_tudo(db: Session, projeto_id: int) -> dict:
    """Composição + Resumo + Comissionamento + DRE numa passada só — a Tela 10 batia 4 endpoints
    separados a cada campo editado (composição, resumo, comissionamento, dre), cada um rodando
    as 3 sincronizações (Equipamentos/Painéis/Comissões, todas pesadas) e o resumo por bloco de
    novo do zero — travava a tela por segundos a cada campo (bug real reportado 2026-08-05).
    Agora tudo reaproveita o mesmo cálculo já feito."""
    dados = montar_composicao(db, projeto_id)
    resumo = resumo_por_bloco(db, projeto_id, dados=dados)
    com = comissionamento(db, projeto_id, dados=dados, resumo=resumo)
    dre = dre_projeto(db, projeto_id, dados=dados, resumo=resumo, com=com)
    return {"composicao": dados, "resumo": resumo, "comissionamento": com, "dre": dre}


# ---------------- Condições de Pagamento ----------------

def _chave_natural_cc(codigo: str):
    # ordenação natural ("2" antes de "10"); tipos consistentes p/ comparação (dígito -> (0,int), texto -> (1,str))
    return [(0, int(p)) if p.isdigit() else (1, p.lower()) for p in re.split(r'(\d+)', codigo or "")]


def _ordenar_itens_orcamento(itens: list, bloco: str) -> list:
    """Mesma ordenação da Tela 10 (t17_ordenarItens / t17_ordenarPorOrdemDoBackend): por código de
    Centro de Custo (menor acima; itens sem CC ao fim; depois descrição). "Painéis Térmicos" mantém
    a ordem própria do backend (aprovado 2026-08-13)."""
    if bloco == "Painéis Térmicos":
        return sorted(itens, key=lambda it: (it.get("ordem") or 0))
    return sorted(itens, key=lambda it: (
        it.get("centro_custo_codigo") in (None, ""),
        _chave_natural_cc(it.get("centro_custo_codigo") or ""),
        (it.get("descricao") or "").lower()))


def tabela_orcamento(dados: dict) -> dict:
    """Versão Python (Excel — "Exportar Tudo", Tela 1, aprovado 2026-08-12) da mesma "Tabela de
    Orçamento" que a Tela 17 monta em JS (ver tela17.js t17_calcularTabelaOrcamento) — MESMO
    algoritmo, pra nunca divergir do que a tela mostra: bloco Comissões nunca aparece como seção
    própria; item de Comissão com Centro de Custo escolhido em "Agrupar valor em" soma seu valor,
    por dentro, no bloco onde esse Centro de Custo já tem uso real (primeiro bloco encontrado, na
    ordem de BLOCOS_COMPOSICAO); item com o checkbox "considerar no orçamento" desmarcado nunca
    entra aqui."""
    resultado = {}
    ordem = []
    for bloco in BLOCOS_COMPOSICAO:
        if bloco == BLOCO_COMISSOES_INDICACAO:
            continue
        itens = _ordenar_itens_orcamento(
            [it for it in dados["blocos"].get(bloco, []) if it.get("incluir_orcamento", True)], bloco)
        linhas = [{"descricao": it["descricao"], "unidade": it.get("unidade") or "-",
                    "quantidade": it["quantidade"], "cc": it.get("centro_custo_descricao"),
                    "valor": it["valor_venda_negociacao"] or 0} for it in itens]
        resultado[bloco] = {"itens": linhas, "total": sum(i["valor"] for i in linhas), "extra_por_cc": {}}
        ordem.append(bloco)

    bloco_por_cc = {}
    for bloco in ordem:
        for it in dados["blocos"].get(bloco, []):
            cc_id = it.get("centro_custo_id")
            if cc_id and cc_id not in bloco_por_cc:
                bloco_por_cc[cc_id] = bloco

    for it in dados["blocos"].get(BLOCO_COMISSOES_INDICACAO, []):
        cc_id = it.get("centro_custo_id")
        if not cc_id or not it.get("incluir_orcamento", True):
            continue
        bloco_alvo_nome = bloco_por_cc.get(cc_id)
        if not bloco_alvo_nome:
            continue
        bloco_alvo = resultado[bloco_alvo_nome]
        valor = it["valor_venda_negociacao"] or 0
        bloco_alvo["total"] += valor
        chave = it.get("centro_custo_descricao") or "Sem Centro de Custo"
        bloco_alvo["extra_por_cc"][chave] = bloco_alvo["extra_por_cc"].get(chave, 0) + valor

    total_geral = sum(b["total"] for b in resultado.values())
    return {"ordem": ordem, "blocos": resultado, "total_geral": total_geral}


def valor_total_proposta(db: Session, dados: dict) -> float:
    """Mesmo total da "Tabela de Orçamento" (ver tabela_orcamento acima / tela17.js
    t17_calcularTabelaOrcamento)."""
    return tabela_orcamento(dados)["total_geral"]


def _ajustar_dia_util(data: datetime.date) -> datetime.date:
    """Sábado antecipa pra sexta, domingo posterga pra segunda (regra explícita do usuário,
    2026-08-06)."""
    if data.weekday() == 5:
        return data - datetime.timedelta(days=1)
    if data.weekday() == 6:
        return data + datetime.timedelta(days=1)
    return data


def listar_agenda_pagamento(db: Session, projeto_id: int) -> dict:
    config = db.query(m.CondicaoPagamentoProjeto).filter_by(projeto_id=projeto_id).first()
    parcelas = (db.query(m.CondicaoPagamentoParcela).filter_by(projeto_id=projeto_id)
                .order_by(m.CondicaoPagamentoParcela.ordem).all())
    return {
        "config": {
            "percentual_sinal": config.percentual_sinal,
            "data_sinal": config.data_sinal,
            "quantidade_parcelas": config.quantidade_parcelas,
            "periodicidade_dias": config.periodicidade_dias,
        } if config else None,
        "fechada": config.fechada if config else False,
        "parcelas": [{"id": p.id, "ordem": p.ordem, "descricao": p.descricao,
                       "data": p.data, "valor": p.valor} for p in parcelas],
        "total": sum(p.valor for p in parcelas),
    }


def gerar_agenda_pagamento(db: Session, projeto_id: int, percentual_sinal: float,
                            data_sinal_str: str, quantidade_parcelas: int,
                            periodicidade_dias: int) -> dict:
    """Gera (substituindo a agenda anterior) o Sinal de Negócio + N parcelas iguais sobre o Valor
    Total da Proposta, com vencimentos a cada periodicidade_dias a partir da Data do Sinal, cada
    data individualmente ajustada pra dia útil. Última parcela absorve a sobra de arredondamento.
    As linhas geradas ficam editáveis depois (ver PUT /condicao-pagamento/parcela/{id}) — regerar
    substitui qualquer edição manual feita na agenda anterior."""
    dados = montar_composicao(db, projeto_id)
    total = valor_total_proposta(db, dados)
    data_sinal = datetime.date.fromisoformat(data_sinal_str)

    valor_sinal = round(total * (percentual_sinal or 0), 2)
    saldo = total - valor_sinal
    qtd = quantidade_parcelas or 0
    valor_parcela = round(saldo / qtd, 2) if qtd else 0.0

    db.query(m.CondicaoPagamentoParcela).filter_by(projeto_id=projeto_id).delete()

    db.add(m.CondicaoPagamentoParcela(
        projeto_id=projeto_id, ordem=0, descricao="Sinal de Negócio",
        data=_ajustar_dia_util(data_sinal).isoformat(), valor=valor_sinal))

    soma_parcelas = 0.0
    for i in range(1, qtd + 1):
        data_i = _ajustar_dia_util(data_sinal + datetime.timedelta(days=periodicidade_dias * i))
        valor_i = valor_parcela if i < qtd else round(saldo - soma_parcelas, 2)
        soma_parcelas += valor_i
        db.add(m.CondicaoPagamentoParcela(
            projeto_id=projeto_id, ordem=i, descricao=f"Parc. {i:02d}",
            data=data_i.isoformat(), valor=valor_i))

    config = db.query(m.CondicaoPagamentoProjeto).filter_by(projeto_id=projeto_id).first()
    if not config:
        config = m.CondicaoPagamentoProjeto(projeto_id=projeto_id)
        db.add(config)
    config.percentual_sinal = percentual_sinal
    config.data_sinal = data_sinal_str
    config.quantidade_parcelas = quantidade_parcelas
    config.periodicidade_dias = periodicidade_dias

    db.commit()
    return listar_agenda_pagamento(db, projeto_id)
