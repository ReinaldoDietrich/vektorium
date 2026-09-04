# -*- coding: utf-8 -*-
"""Corrige duplicidade de fabricante Mipal/MIPAL (cat_fabricantes id=2 'MIPAL' vs id=3 'Mipal',
criada ao importar EVIB/HdhB com grafia diferente da já usada pelo MI_GS2). Move as linhas de
fabricante_id=3 para fabricante_id=2, apaga o duplicado e padroniza o nome como 'Mipal' (mesmo
padrão de 'Elgin' -- só a inicial maiúscula). Idempotente: se id=3 já não existir, não faz nada."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent.parent / "database" / "carga_termica.db"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    existe_dup = cur.execute("SELECT COUNT(*) FROM cat_fabricantes WHERE id=3").fetchone()[0]
    if not existe_dup:
        print("Nada a fazer -- fabricante id=3 não existe (já corrigido antes).")
        con.close()
        return

    n = cur.execute("UPDATE forcador_linhas SET fabricante_id=2 WHERE fabricante_id=3").rowcount
    cur.execute("DELETE FROM cat_fabricantes WHERE id=3")
    cur.execute("UPDATE cat_fabricantes SET nome='Mipal' WHERE id=2")
    con.commit()

    print(f"{n} linha(s) reapontada(s) de fabricante_id=3 para 2.")
    print("Fabricante duplicado (id=3) removido.")
    print("Fabricante id=2 renomeado para 'Mipal'.")
    for r in cur.execute("SELECT id, nome FROM cat_fabricantes ORDER BY id"):
        print(" ", r)
    con.close()


if __name__ == "__main__":
    main()
