# -*- coding: utf-8 -*-
"""Cria as tabelas de Condições de Pagamento (condicao_pagamento_projeto,
condicao_pagamento_parcela). Idempotente."""
from backend.database import engine
from backend import models as m


def main():
    m.Base.metadata.create_all(bind=engine, tables=[
        m.CondicaoPagamentoProjeto.__table__,
        m.CondicaoPagamentoParcela.__table__,
    ])
    print("Tabelas de Condições de Pagamento criadas (ou já existentes).")


if __name__ == "__main__":
    main()
