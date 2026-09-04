# -*- coding: utf-8 -*-
"""Exclui as Portas Frigoríficas duplicadas no projeto 210/2026 R01 (projeto_id=3) — mesmo bug de
duplicação na criação da revisão que afetou os Painéis Térmicos (ver
excluir_paineis_duplicados_210_2026_r01.py). 35 portas originais viraram 70 (35 pares idênticos,
offset de id +70). Mantém a de menor id de cada par, exclui a de maior id."""
from collections import defaultdict
from backend.database import SessionLocal
from backend import models as m


def main():
    db = SessionLocal()
    try:
        portas = db.query(m.PortaFrigorifica).filter_by(projeto_id=3).order_by(m.PortaFrigorifica.id).all()
        grupos = defaultdict(list)
        for pf in portas:
            chave = (pf.camara_completo_id, pf.camara_simples_id, pf.funcao, pf.modelo, pf.sentido,
                      pf.vao_largura_mm, pf.vao_altura_mm, pf.fixacao, pf.espessura_fixacao_mm,
                      pf.tensao, pf.observacoes, pf.ordem, pf.ambiente_nao_climatizado_nome)
            grupos[chave].append(pf)

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
        restantes = db.query(m.PortaFrigorifica).filter_by(projeto_id=3).count()
        print(f"Excluídas: {excluidos} portas duplicadas.")
        print(f"Restantes no projeto 3 (210/2026 R01): {restantes}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
