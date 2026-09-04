"""Migração pontual (2026-07): adiciona quantidade/tipo_degelo na seleção de forçador (Câmara
Completo/Simples), cria FatorCorrecaoGasForcador e insere linhas em branco (fator=NULL) para os
8 gases nas linhas de forçador já cadastradas — usuário preenche manualmente."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")
GASES = ["R-404A", "R-134a", "R-452A", "R-448A", "R-449A", "R-407C", "R-22", "R-410A"]


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for tabela in ["camara_completo_forcadores", "camara_simples_forcadores"]:
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({tabela})")]
        if "quantidade" not in cols:
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN quantidade INTEGER DEFAULT 1")
            print(tabela, "+ quantidade")
        if "tipo_degelo" not in cols:
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN tipo_degelo VARCHAR")
            print(tabela, "+ tipo_degelo")
    cur.execute("UPDATE camara_completo_forcadores SET quantidade=1 WHERE quantidade IS NULL")
    cur.execute("UPDATE camara_simples_forcadores SET quantidade=1 WHERE quantidade IS NULL")

    cur.execute("""CREATE TABLE IF NOT EXISTS forcador_fatores_gas (
        id INTEGER PRIMARY KEY,
        linha_id INTEGER NOT NULL REFERENCES forcador_linhas(id),
        gas VARCHAR NOT NULL,
        fator FLOAT,
        UNIQUE(linha_id, gas)
    )""")
    print("forcador_fatores_gas criada")

    linhas = cur.execute("SELECT id, nome FROM forcador_linhas").fetchall()
    for linha_id, nome in linhas:
        for gas in GASES:
            cur.execute("INSERT OR IGNORE INTO forcador_fatores_gas (linha_id, gas, fator) VALUES (?,?,NULL)",
                        (linha_id, gas))
        print(f"linha {nome} (id={linha_id}): 8 gases em branco inseridos")

    conn.commit()
    conn.close()
    print("Migração concluída.")


if __name__ == "__main__":
    run()
