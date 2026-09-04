# -*- coding: utf-8 -*-
"""Backfill idempotente: garante 1 válvula por linha de forçador já existente (criada antes da
válvula passar a ser provisionada automaticamente junto com o forçador). Fabricante/Tipo de
Expansão herdados do Sistema da câmara (mesma regra do provisionamento novo).

Rodar direto: python -m backend.scripts.backfill_valvula_por_forcador <caminho_db>
"""
import sys
import sqlite3


def backfill(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    total = 0

    for tabela_forc, tabela_valv, tabela_camara, coluna_sistema in (
        ("camara_completo_forcadores", "camara_completo_valvulas", "camaras_completo", "sistema_id"),
        ("camara_simples_forcadores", "camara_simples_valvulas", "camaras_simples", "sistema_id"),
    ):
        cur.execute(f"""SELECT f.id, s.tipo_expansao, s.automacao_linhas_fabricante
                        FROM {tabela_forc} f
                        JOIN {tabela_camara} c ON c.id = f.camara_id
                        JOIN sistemas_refrigeracao s ON s.id = c.{coluna_sistema}
                        WHERE f.id NOT IN (SELECT forcador_selecao_id FROM {tabela_valv})""")
        pendentes = cur.fetchall()
        for forcador_id, tipo_expansao, fabricante in pendentes:
            cur.execute(f"""INSERT INTO {tabela_valv}
                            (forcador_selecao_id, fabricante, tipo_expansao, considerado)
                            VALUES (?, ?, ?, 1)""",
                        (forcador_id, fabricante or "—", tipo_expansao or "Eletrônica"))
            total += 1
        print(f"{tabela_forc}: {len(pendentes)} válvula(s) provisionada(s).")

    con.commit()
    con.close()
    print(f"Backfill concluído — {total} válvula(s) criada(s) no total.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    backfill(caminho)
