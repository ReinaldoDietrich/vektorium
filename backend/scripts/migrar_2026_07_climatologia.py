"""Migração pontual (2026-07): expande Projeto/CondicaoClimatica para o novo modelo de
climatologia (estações INMET + critério de projeto), cria FatorInsolacao, corrige os valores de
FatorAltura e ClasseProduto, e remove os configs globais substituídos por dados por-câmara/projeto.
Roda uma vez, direto no arquivo sqlite."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(projetos)")]
    for col, tipo in [("estacao_climatologica_id", "INTEGER"), ("criterio_climatico", "TEXT"), ("ur_externa", "FLOAT")]:
        if col not in cols:
            cur.execute(f"ALTER TABLE projetos ADD COLUMN {col} {tipo}")
            print("projetos +", col)

    cur.execute("DROP TABLE IF EXISTS cat_condicoes_climaticas")
    cur.execute("""CREATE TABLE cat_condicoes_climaticas (
        id INTEGER PRIMARY KEY,
        cidade VARCHAR NOT NULL UNIQUE,
        uf VARCHAR,
        codigo_estacao INTEGER,
        tbs_pico_sazonal FLOAT,
        tbu_pico_sazonal FLOAT,
        ur_pico_sazonal FLOAT,
        tbs_media_anual FLOAT,
        tbu_media_anual FLOAT,
        ur_media_anual FLOAT,
        tbs_maxima_absoluta FLOAT
    )""")
    print("cat_condicoes_climaticas recriada")

    cur.execute("""CREATE TABLE IF NOT EXISTS cat_fator_insolacao (
        id INTEGER PRIMARY KEY,
        orientacao VARCHAR NOT NULL UNIQUE,
        fator FLOAT NOT NULL
    )""")
    print("cat_fator_insolacao criada")

    cur.execute("DELETE FROM cat_fator_altura")
    for ate, fator in [(2.49, 0.70), (2.74, 0.80), (2.99, 0.90), (3.24, 1.00), (3.49, 1.05), (4.00, 1.12)]:
        cur.execute("INSERT INTO cat_fator_altura (pe_direito_ate_m, fator) VALUES (?,?)", (ate, fator))
    print("cat_fator_altura atualizada")

    cur.execute("DELETE FROM cat_classes_produto")
    classes = [
        (1, 4, 5, 90, 90, "Vegetais, flores, gelo sem embalagem"),
        (2, 6, 7, 80, 85, "Armazenamentos de frigorificados em geral refrigeração, alimentos e vegetais embalados, frutas e similares"),
        (3, 7, 9, 65, 80, "Cerveja, vinho, produtos farmacêuticos, batatas, cebolas, frutas de casca dura e produtos embalados"),
        (4, 9, 10, 50, 65, "Sala de preparo, processo e cortes"),
        (5, 11, 14, 50, 65, "Armazém de cerveja, doces e armazenagem de filmes"),
    ]
    for c in classes:
        cur.execute("INSERT INTO cat_classes_produto (classe,dt_evap_min,dt_evap_max,ur_min,ur_max,aplicacao) VALUES (?,?,?,?,?,?)", c)
    print("cat_classes_produto atualizada")

    cur.execute("DELETE FROM configuracao_global WHERE chave IN ('ur_interna_infiltracao','ur_externa_infiltracao')")
    cur.execute("UPDATE configuracao_global SET valor=1.10, pendente_confirmacao=0 WHERE chave='fator_majoracao_insolacao'")
    print("cat_configuracao_global limpo/atualizado")

    conn.commit()
    conn.close()
    print("Migração concluída.")


if __name__ == "__main__":
    run()
