# -*- coding: utf-8 -*-
"""Exclui os Painéis Térmicos duplicados no projeto 210/2026 R01 (projeto_id=3) — bug na criação
da revisão duplicou os 49 painéis inteiros (98 registros, todos em pares idênticos com offset de
id +98). Mantém o de menor id de cada par (o "original" da revisão), exclui o de maior id (a
duplicata). Recalcula os pares na hora (mesma lógica da investigação) em vez de usar uma lista
fixa de ids, pra ser seguro mesmo se algo mudar entre a análise e a execução."""
from collections import defaultdict
from backend.database import SessionLocal
from backend import models as m


def main():
    db = SessionLocal()
    try:
        paineis = db.query(m.PainelTermico).filter_by(projeto_id=3).order_by(m.PainelTermico.id).all()
        grupos = defaultdict(list)
        for pt in paineis:
            chave = (pt.camara_completo_id, pt.camara_simples_id, pt.tipo, pt.espessura,
                      pt.dimensao_1, pt.dimensao_2, pt.ordem, pt.ambiente_nao_climatizado_nome)
            grupos[chave].append(pt)

        excluidos = 0
        for chave, itens in grupos.items():
            if len(itens) != 2:
                print(f"AVISO: grupo com {len(itens)} itens (esperado 2) -- pulando por segurança: {chave}")
                continue
            itens.sort(key=lambda p: p.id)
            duplicata = itens[1]
            db.delete(duplicata)
            excluidos += 1

        db.commit()
        restantes = db.query(m.PainelTermico).filter_by(projeto_id=3).count()
        print(f"Excluídos: {excluidos} painéis duplicados.")
        print(f"Restantes no projeto 3 (210/2026 R01): {restantes}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
