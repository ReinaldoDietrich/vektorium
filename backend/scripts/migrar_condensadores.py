# -*- coding: utf-8 -*-
"""Cria as tabelas da Tela C (Condensadores Remotos): condensador_linhas, condensador_modelos,
condensador_fatores, condensador_importacoes. Idempotente — Base.metadata.create_all só cria as
tabelas que ainda não existem, não toca em nenhuma existente nem em dados.

Rodar: python -m backend.scripts.migrar_condensadores <caminho_db>
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import create_engine
from backend.database import Base
from backend import models  # noqa: F401 — registra os modelos no metadata


def run(db_path):
    engine = create_engine(f"sqlite:///{db_path}")
    antes = set(engine.dialect.get_table_names(engine.connect()))
    Base.metadata.create_all(bind=engine)
    depois = set(engine.dialect.get_table_names(engine.connect()))
    criadas = sorted(depois - antes)
    if criadas:
        print(f"Tabelas criadas em {db_path}: {', '.join(criadas)}")
    else:
        print(f"Nenhuma tabela nova (já existiam) em {db_path}.")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    run(db_path)
