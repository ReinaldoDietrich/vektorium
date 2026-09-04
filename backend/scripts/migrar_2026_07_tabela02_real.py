"""Migração pontual (2026-07): substitui os 8 tipos exemplo/teste da Tabela 02 pelos 7 tipos reais
("Tabela Câmaras Simples.xlsx"), cria cat_faixa_area_tabela02 (a carga não é linear por m² — é
consultada por faixa de área x tipo) e importa as 150 faixas x 7 tipos da planilha real."""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tabela02_faixas.json")

TIPOS = [
    ("C. Carnes, peixes ou frangos", -5),
    ("C. Laticínios, salgados, padaria, frios ou pizzas", 2),
    ("C. FLV/horti, lixo, ossos, prep. carnes aberto", 8),
    ("Prep. carnes fechado ou prep. diversos aberto", 10),
    ("Prep. div. fech., ante-câmara ou corredor refrig.", 12),
    ("C. Congelados com ante-câmara", -22),
    ("C. Congelados sem ante-câmara", -25),
]


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA encoding = 'UTF-8'")
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS cat_faixa_area_tabela02 (
        id INTEGER PRIMARY KEY,
        tabela02_id INTEGER NOT NULL REFERENCES cat_tabela_tipo02(id),
        area_de FLOAT NOT NULL,
        area_ate FLOAT NOT NULL,
        carga_kcal_h FLOAT NOT NULL
    )""")
    print("cat_faixa_area_tabela02 criada (ou já existia)")

    # Nenhuma câmara simples real referencia os 8 ids exemplo/teste ainda (verificado antes de
    # rodar) — seguro apagar e recriar do zero.
    cur.execute("SELECT COUNT(*) FROM camaras_simples WHERE tabela02_id IS NOT NULL")
    (qtd_camaras_com_tipo,) = cur.fetchone()
    if qtd_camaras_com_tipo > 0:
        raise RuntimeError(
            f"{qtd_camaras_com_tipo} câmara(s) simples já referenciam um tabela02_id — "
            "migração abortada para não quebrar dado real. Remapear manualmente antes de rodar."
        )

    cur.execute("DELETE FROM cat_faixa_area_tabela02")
    cur.execute("DELETE FROM cat_tabela_tipo02")

    tabela02_ids = []
    for tipo, temp_default in TIPOS:
        cur.execute("INSERT INTO cat_tabela_tipo02 (tipo, temp_interna_default) VALUES (?,?)",
                    (tipo, temp_default))
        tabela02_ids.append(cur.lastrowid)
    print(f"{len(tabela02_ids)} tipos reais inseridos: {[t[0] for t in TIPOS]}")

    with open(DATA_PATH, encoding="utf-8") as f:
        faixas = json.load(f)

    total = 0
    for faixa in faixas:
        for tabela02_id, valor in zip(tabela02_ids, faixa["valores"]):
            cur.execute(
                "INSERT INTO cat_faixa_area_tabela02 (tabela02_id, area_de, area_ate, carga_kcal_h) VALUES (?,?,?,?)",
                (tabela02_id, faixa["area_de"], faixa["area_ate"], valor),
            )
            total += 1
    print(f"{total} faixas inseridas ({len(faixas)} faixas de área x {len(tabela02_ids)} tipos)")

    conn.commit()
    conn.close()
    print("Migração concluída.")


if __name__ == "__main__":
    run()
