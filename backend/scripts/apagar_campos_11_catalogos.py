# -*- coding: utf-8 -*-
"""Apaga TODOS os cards de Nomenclatura (CampoCatalogo + opções) dos 11 catálogos que tinham
transcrição não confiável (baseada em memória do assistente, sem conferência contra a imagem
original) — deixa cada um com ZERO cards. Sem reconstrução, sem adição de nada.
Usa salvar_campos(..., []) — mesmo caminho seguro já usado no resto do sistema, evita o bug de
reaproveitamento de id do SQLite (ver comentário em campo_catalogo.salvar_campos)."""
from backend.database import SessionLocal
from backend import models as m
from backend import campo_catalogo as cc


def main():
    db = SessionLocal()
    try:
        forcadores = ['EDH - 4 Aletas', 'EDH - 6 Aletas', 'FM*4', 'FM*6', 'FBX+', 'FL+', 'MI GS2']
        for nome in forcadores:
            linha = db.query(m.LinhaForcador).filter_by(nome=nome).first()
            if not linha:
                print(f"{nome}: NÃO ENCONTRADA, pulando.")
                continue
            cc.salvar_campos(db, "Forcador", linha.id, [])
            print(f"{nome} (linha_id={linha.id}): cards apagados.")

        linha_acc = db.query(m.LinhaCondensadorRemoto).filter_by(nome="ACC").first()
        if linha_acc:
            cc.salvar_campos(db, "CondensadorRemoto", linha_acc.id, [])
            print(f"ACC (linha_id={linha_acc.id}): cards apagados.")
        else:
            print("ACC: NÃO ENCONTRADA, pulando.")

        for cat_id in (1, 2, 3):
            cat = db.get(m.CatalogoUC, cat_id)
            if not cat:
                print(f"catalogo_id={cat_id}: NÃO ENCONTRADO, pulando.")
                continue
            cc.salvar_campos(db, "UC", cat_id, [])
            print(f"{cat.nome} (catalogo_id={cat_id}): cards apagados.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
