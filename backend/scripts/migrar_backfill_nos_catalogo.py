# -*- coding: utf-8 -*-
"""Materializa na árvore de Ids Comerciais (Configurações) os nós de LinhaForcador/CatalogoUC/
LinhaCondensadorRemoto já cadastrados ANTES de gerar_proximo_id_catalogo passar a inserir esse nó
(aprovado 2026-08-06) — o código de cada um já existe e continua exatamente o mesmo (não mexe em
nenhum id_comercial de catálogo), só passa a existir também como linha visível na árvore.

Só ADICIONA nó que falta (nunca apaga, nunca sobrescreve um nó já existente) — diferente de
migrar_arvore_ids_v2.py, que recria a árvore inteira do zero e destruiria os nós de Modelo do
Catálogo Comercial (Tela D) já cadastrados. Idempotente: pode rodar de novo sem duplicar."""
from backend.database import SessionLocal
from backend import models as m


def _garantir_no(db, codigo, nome):
    if not codigo:
        return False
    if db.query(m.IdComercial).filter_by(codigo=codigo).first():
        return False
    db.add(m.IdComercial(codigo=codigo, nome=nome, ordem=0, origem_automatica=True))
    return True


def main():
    db = SessionLocal()
    total = 0

    for linha in db.query(m.LinhaForcador).filter(m.LinhaForcador.id_comercial.isnot(None)).all():
        if _garantir_no(db, linha.id_comercial, linha.nome):
            total += 1
    db.flush()

    for cat in db.query(m.CatalogoUC).filter(m.CatalogoUC.id_comercial.isnot(None)).all():
        if _garantir_no(db, cat.id_comercial, cat.nome):
            total += 1
    db.flush()

    for linha in db.query(m.LinhaCondensadorRemoto).filter(m.LinhaCondensadorRemoto.id_comercial.isnot(None)).all():
        if _garantir_no(db, linha.id_comercial, linha.nome):
            total += 1
    db.flush()

    db.commit()
    db.close()
    print(f"{total} nó(s) de catálogo adicionado(s) à árvore de Ids Comerciais.")


if __name__ == "__main__":
    main()
