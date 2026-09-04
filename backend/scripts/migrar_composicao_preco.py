# -*- coding: utf-8 -*-
"""Cria as tabelas da Composição de Preço (fator_venda, item_composicao_mestre, vendedor,
composicao_preco_item, comissao_vendedor_projeto, margem_negociacao_projeto) e adiciona
centro_custo.bloco_composicao. Idempotente."""
import sqlite3
from backend.database import DB_PATH, engine
from backend import models as m


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(centro_custo)").fetchall()]
    if "bloco_composicao" not in cols:
        cur.execute("ALTER TABLE centro_custo ADD COLUMN bloco_composicao TEXT")
        print("Coluna centro_custo.bloco_composicao adicionada.")
    else:
        print("Coluna centro_custo.bloco_composicao já existe.")
    conn.commit()
    conn.close()

    m.Base.metadata.create_all(bind=engine, tables=[
        m.FatorVenda.__table__,
        m.ItemComposicaoMestre.__table__,
        m.Vendedor.__table__,
        m.ComposicaoPrecoItem.__table__,
        m.ComissaoVendedorProjeto.__table__,
        m.MargemNegociacaoProjeto.__table__,
    ])
    print("Tabelas de Composição de Preço criadas (ou já existentes).")


if __name__ == "__main__":
    main()
