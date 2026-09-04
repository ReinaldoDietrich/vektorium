# -*- coding: utf-8 -*-
"""Cria as tabelas da Tela B (Unidades Condensadoras) no banco de TESTE e popula a nomenclatura
padrão (tabelas de código da Planilha2 do usuário). Idempotente."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.database import engine, SessionLocal, Base
from backend import models as m

# Nomenclatura padrão — (categoria, valor, codigo, ordem)
NOMENCLATURA = [
    ("Sistema", "Alta", "1", 0),
    ("Sistema", "Média", "2", 1),
    ("Sistema", "Baixa", "3", 2),
    ("Sistema", "Média e Baixa", "4", 3),
    ("Fabricante UC", "Elgin", "1", 0),
    ("Fabricante UC", "Danfoss", "2", 1),
    ("Fabricante UC", "Tecumseh", "3", 2),
    ("Fabricante UC", "Bitzer", "4", 3),
    ("Tipo", "Hermético", "1", 0),
    ("Tipo", "Semi-Hermético", "2", 1),
    ("Tipo", "Scroll", "3", 2),
    ("Tipo", "Duplo-Estágio", "4", 3),
    ("Tipo", "Parafuso", "5", 4),
    ("Fabricante Compressor", "Bitzer", "1", 0),
    ("Fabricante Compressor", "Dorin", "2", 1),
    ("Fabricante Compressor", "Copeland", "3", 2),
    ("Fabricante Compressor", "Danfoss", "4", 3),
    ("Fabricante Compressor", "Elgin", "5", 4),
    ("Fabricante Compressor", "Lunite", "6", 5),
    ("Gás", "R-134a", "1", 0),
    ("Gás", "R-22", "2", 1),
    ("Gás", "R-404a", "3", 2),
    ("Gás", "R-507c", "4", 3),
    ("Ambiente", "32", "1", 0),
    ("Ambiente", "35", "2", 1),
    ("Ambiente", "38", "3", 2),
    ("Ambiente", "43", "4", 3),
]


def run():
    Base.metadata.create_all(bind=engine)
    print("Tabelas UC criadas (as que faltavam).")
    db = SessionLocal()
    try:
        if db.query(m.NomenclaturaUC).count() == 0:
            for categoria, valor, codigo, ordem in NOMENCLATURA:
                db.add(m.NomenclaturaUC(categoria=categoria, valor=valor, codigo=codigo, ordem=ordem))
            db.commit()
            print(f"{len(NOMENCLATURA)} linhas de nomenclatura inseridas.")
        else:
            print("Nomenclatura já populada, nada a fazer.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
