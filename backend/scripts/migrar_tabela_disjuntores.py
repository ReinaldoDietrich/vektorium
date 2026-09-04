# -*- coding: utf-8 -*-
"""Migração aditiva: cria as tabelas "Tela 5 - Tabela de Disjuntores" (Termomagnético e DDR),
com a mesma disposição de colunas/linhas da planilha original "Documentos de Criação/Tabela de
Disjuntores.xlsx". Também cria os 2 parâmetros globais que estavam no cabeçalho da planilha
(Limite Curva C e Folga Adotada Corrente) em configuracao_global.

CREATE TABLE (se não existir) + INSERT só se a tabela estiver vazia -- idempotente, nunca duplica
nem apaga dado existente.

Rodar: python -m backend.scripts.migrar_tabela_disjuntores <caminho_db>
"""
import sys
import sqlite3

# Termomagnético: (utilizacao, corrente_nominal_a, desc_proj_127v_1p, desc_comercial_127v_1p,
#                  desc_proj_220v_1p, desc_comercial_220v_1p, desc_proj_220v_3p, desc_comercial_220v_3p,
#                  desc_proj_380v_3p, desc_comercial_380v_3p)
DADOS_TERMOMAGNETICO = [
    ('Ventilação', 5, 'Disj. 5A 1 P', 'Disj. Termomagnético 5A 1 P 127V Curva C', 'Disj. 5A 1 P', 'Disj. Termomagnético 5A 1 P 220V Curva C', 'Disj. 5A 3 P', 'Disj. Termomagnético 5A 3 P 220V Curva C', 'Disj. 5A 3 P', 'Disj. Termomagnético 5A 3 P 380V Curva C'),
    ('Degelo', 10, 'Disj. 10A 1 P', 'Disj. Termomagnético 10A 1 P 127V Curva C', 'Disj. 10A 1 P', 'Disj. Termomagnético 10A 1 P 220V Curva C', 'Disj. 10A 3 P', 'Disj. Termomagnético 10A 3 P 220V Curva C', 'Disj. 10A 3 P', 'Disj. Termomagnético 10A 3 P 380V Curva C'),
    (None, 16, 'Disj. 16A 1 P', 'Disj. Termomagnético 16A 1 P 127V Curva C', 'Disj. 16A 1 P', 'Disj. Termomagnético 16A 1 P 220V Curva C', 'Disj. 16A 3 P', 'Disj. Termomagnético 16A 3 P 220V Curva C', 'Disj. 16A 3 P', 'Disj. Termomagnético 16A 3 P 380V Curva C'),
    (None, 20, 'Disj. 20A 1 P', 'Disj. Termomagnético 20A 1 P 127V Curva C', 'Disj. 20A 1 P', 'Disj. Termomagnético 20A 1 P 220V Curva C', 'Disj. 20A 3 P', 'Disj. Termomagnético 20A 3 P 220V Curva C', 'Disj. 20A 3 P', 'Disj. Termomagnético 20A 3 P 380V Curva C'),
    (None, 25, 'Disj. 25A 1 P', 'Disj. Termomagnético 25A 1 P 127V Curva C', 'Disj. 25A 1 P', 'Disj. Termomagnético 25A 1 P 220V Curva C', 'Disj. 25A 3 P', 'Disj. Termomagnético 25A 3 P 220V Curva C', 'Disj. 25A 3 P', 'Disj. Termomagnético 25A 3 P 380V Curva C'),
    (None, 32, 'Disj. 32A 1 P', 'Disj. Termomagnético 32A 1 P 127V Curva C', 'Disj. 32A 1 P', 'Disj. Termomagnético 32A 1 P 220V Curva C', 'Disj. 32A 3 P', 'Disj. Termomagnético 32A 3 P 220V Curva C', 'Disj. 32A 3 P', 'Disj. Termomagnético 32A 3 P 380V Curva C'),
    (None, 40, 'Disj. 40A 1 P', 'Disj. Termomagnético 40A 1 P 127V Curva C', 'Disj. 40A 1 P', 'Disj. Termomagnético 40A 1 P 220V Curva C', 'Disj. 40A 3 P', 'Disj. Termomagnético 40A 3 P 220V Curva C', 'Disj. 40A 3 P', 'Disj. Termomagnético 40A 3 P 380V Curva C'),
    (None, 50, 'Disj. 50A 1 P', 'Disj. Termomagnético 50A 1 P 127V Curva C', 'Disj. 50A 1 P', 'Disj. Termomagnético 50A 1 P 220V Curva C', 'Disj. 50A 3 P', 'Disj. Termomagnético 50A 3 P 220V Curva C', 'Disj. 50A 3 P', 'Disj. Termomagnético 50A 3 P 380V Curva C'),
    (None, 63, 'Disj. 63A 1 P', 'Disj. Termomagnético 63A 1 P 127V Curva C', 'Disj. 63A 1 P', 'Disj. Termomagnético 63A 1 P 220V Curva C', 'Disj. 63A 3 P', 'Disj. Termomagnético 63A 3 P 220V Curva C', 'Disj. 63A 3 P', 'Disj. Termomagnético 63A 3 P 380V Curva C'),
    (None, 80, 'Disj. 80A 1 P', 'Disj. Termomagnético 80A 1 P 127V Curva D', 'Disj. 80A 1 P', 'Disj. Termomagnético 80A 1 P 220V Curva D', 'Disj. 80A 3 P', 'Disj. Termomagnético 80A 3 P 220V Curva D', 'Disj. 80A 3 P', 'Disj. Termomagnético 80A 3 P 380V Curva D'),
    (None, 100, 'Disj. 100A 1 P', 'Disj. Termomagnético 100A 1 P 127V Curva D', 'Disj. 100A 1 P', 'Disj. Termomagnético 100A 1 P 220V Curva D', 'Disj. 100A 3 P', 'Disj. Termomagnético 100A 3 P 220V Curva D', 'Disj. 100A 3 P', 'Disj. Termomagnético 100A 3 P 380V Curva D'),
    (None, 125, 'Disj. 125A 1 P', 'Disj. Termomagnético 125A 1 P 127V Curva D', 'Disj. 125A 1 P', 'Disj. Termomagnético 125A 1 P 220V Curva D', 'Disj. 125A 3 P', 'Disj. Termomagnético 125A 3 P 220V Curva D', 'Disj. 125A 3 P', 'Disj. Termomagnético 125A 3 P 380V Curva D'),
    (None, 160, 'Disj. 160A 1 P', 'Disj. Termomagnético 160A 1 P 127V Curva D', 'Disj. 160A 1 P', 'Disj. Termomagnético 160A 1 P 220V Curva D', 'Disj. 160A 3 P', 'Disj. Termomagnético 160A 3 P 220V Curva D', 'Disj. 160A 3 P', 'Disj. Termomagnético 160A 3 P 380V Curva D'),
    (None, 200, 'Disj. 200A 1 P', 'Disj. Termomagnético 200A 1 P 127V Curva D', 'Disj. 200A 1 P', 'Disj. Termomagnético 200A 1 P 220V Curva D', 'Disj. 200A 3 P', 'Disj. Termomagnético 200A 3 P 220V Curva D', 'Disj. 200A 3 P', 'Disj. Termomagnético 200A 3 P 380V Curva D'),
    (None, 250, 'Disj. 250A 1 P', 'Disj. Termomagnético 250A 1 P 127V Curva D', 'Disj. 250A 1 P', 'Disj. Termomagnético 250A 1 P 220V Curva D', 'Disj. 250A 3 P', 'Disj. Termomagnético 250A 3 P 220V Curva D', 'Disj. 250A 3 P', 'Disj. Termomagnético 250A 3 P 380V Curva D'),
    (None, 315, 'Disj. 315A 1 P', 'Disj. Termomagnético 315A 1 P 127V Curva D', 'Disj. 315A 1 P', 'Disj. Termomagnético 315A 1 P 220V Curva D', 'Disj. 315A 3 P', 'Disj. Termomagnético 315A 3 P 220V Curva D', 'Disj. 315A 3 P', 'Disj. Termomagnético 315A 3 P 380V Curva D'),
    (None, 400, 'Disj. 400A 1 P', 'Disj. Termomagnético 400A 1 P 127V Curva D', 'Disj. 400A 1 P', 'Disj. Termomagnético 400A 1 P 220V Curva D', 'Disj. 400A 3 P', 'Disj. Termomagnético 400A 3 P 220V Curva D', 'Disj. 400A 3 P', 'Disj. Termomagnético 400A 3 P 380V Curva D'),
    (None, 500, 'Disj. 500A 1 P', 'Disj. Termomagnético 500A 1 P 127V Curva D', 'Disj. 500A 1 P', 'Disj. Termomagnético 500A 1 P 220V Curva D', 'Disj. 500A 3 P', 'Disj. Termomagnético 500A 3 P 220V Curva D', 'Disj. 500A 3 P', 'Disj. Termomagnético 500A 3 P 380V Curva D'),
]

DADOS_DDR = [
    ('Res. Porta', 5, 'Disj. DDR 5A 1 P', 'Disj. Dif. Resid. (DDR) 5A 1 P 127V Curva C  30mA', 'Disj. DDR 5A 1 P', 'Disj. Dif. Resid. (DDR) 5A 1 P 220V Curva C  30mA', 'Disj. DDR 5A 3 P', 'Disj. Dif. Resid. (DDR) 5A 3 P 220V Curva C  30mA', 'Disj. DDR 5A 3 P', 'Disj. Dif. Resid. (DDR) 5A 3 P 380V Curva C  30mA'),
    ('Res. Dreno', 10, 'Disj. DDR 10A 1 P', 'Disj. Dif. Resid. (DDR) 10A 1 P 127V Curva C  30mA', 'Disj. DDR 10A 1 P', 'Disj. Dif. Resid. (DDR) 10A 1 P 220V Curva C  30mA', 'Disj. DDR 10A 3 P', 'Disj. Dif. Resid. (DDR) 10A 3 P 220V Curva C  30mA', 'Disj. DDR 10A 3 P', 'Disj. Dif. Resid. (DDR) 10A 3 P 380V Curva C  30mA'),
    ('Iluminação', 16, 'Disj. DDR 16A 1 P', 'Disj. Dif. Resid. (DDR) 16A 1 P 127V Curva C  30mA', 'Disj. DDR 16A 1 P', 'Disj. Dif. Resid. (DDR) 16A 1 P 220V Curva C  30mA', 'Disj. DDR 16A 3 P', 'Disj. Dif. Resid. (DDR) 16A 3 P 220V Curva C  30mA', 'Disj. DDR 16A 3 P', 'Disj. Dif. Resid. (DDR) 16A 3 P 380V Curva C  30mA'),
    (None, 20, 'Disj. DDR 20A 1 P', 'Disj. Dif. Resid. (DDR) 20A 1 P 127V Curva C  30mA', 'Disj. DDR 20A 1 P', 'Disj. Dif. Resid. (DDR) 20A 1 P 220V Curva C  30mA', 'Disj. DDR 20A 3 P', 'Disj. Dif. Resid. (DDR) 20A 3 P 220V Curva C  30mA', 'Disj. DDR 20A 3 P', 'Disj. Dif. Resid. (DDR) 20A 3 P 380V Curva C  30mA'),
    (None, 25, 'Disj. DDR 25A 1 P', 'Disj. Dif. Resid. (DDR) 25A 1 P 127V Curva C  30mA', 'Disj. DDR 25A 1 P', 'Disj. Dif. Resid. (DDR) 25A 1 P 220V Curva C  30mA', 'Disj. DDR 25A 3 P', 'Disj. Dif. Resid. (DDR) 25A 3 P 220V Curva C  30mA', 'Disj. DDR 25A 3 P', 'Disj. Dif. Resid. (DDR) 25A 3 P 380V Curva C  30mA'),
    (None, 32, 'Disj. DDR 32A 1 P', 'Disj. Dif. Resid. (DDR) 32A 1 P 127V Curva C  30mA', 'Disj. DDR 32A 1 P', 'Disj. Dif. Resid. (DDR) 32A 1 P 220V Curva C  30mA', 'Disj. DDR 32A 3 P', 'Disj. Dif. Resid. (DDR) 32A 3 P 220V Curva C  30mA', 'Disj. DDR 32A 3 P', 'Disj. Dif. Resid. (DDR) 32A 3 P 380V Curva C  30mA'),
    (None, 40, 'Disj. DDR 40A 1 P', 'Disj. Dif. Resid. (DDR) 40A 1 P 127V Curva C  30mA', 'Disj. DDR 40A 1 P', 'Disj. Dif. Resid. (DDR) 40A 1 P 220V Curva C  30mA', 'Disj. DDR 40A 3 P', 'Disj. Dif. Resid. (DDR) 40A 3 P 220V Curva C  30mA', 'Disj. DDR 40A 3 P', 'Disj. Dif. Resid. (DDR) 40A 3 P 380V Curva C  30mA'),
    (None, 50, 'Disj. DDR 50A 1 P', 'Disj. Dif. Resid. (DDR) 50A 1 P 127V Curva C  30mA', 'Disj. DDR 50A 1 P', 'Disj. Dif. Resid. (DDR) 50A 1 P 220V Curva C  30mA', 'Disj. DDR 50A 3 P', 'Disj. Dif. Resid. (DDR) 50A 3 P 220V Curva C  30mA', 'Disj. DDR 50A 3 P', 'Disj. Dif. Resid. (DDR) 50A 3 P 380V Curva C  30mA'),
    (None, 63, 'Disj. DDR 63A 1 P', 'Disj. Dif. Resid. (DDR) 63A 1 P 127V Curva C  30mA', 'Disj. DDR 63A 1 P', 'Disj. Dif. Resid. (DDR) 63A 1 P 220V Curva C  30mA', 'Disj. DDR 63A 3 P', 'Disj. Dif. Resid. (DDR) 63A 3 P 220V Curva C  30mA', 'Disj. DDR 63A 3 P', 'Disj. Dif. Resid. (DDR) 63A 3 P 380V Curva C  30mA'),
]

COLUNAS = ("utilizacao", "corrente_nominal_a",
           "desc_proj_127v_1p", "desc_comercial_127v_1p",
           "desc_proj_220v_1p", "desc_comercial_220v_1p",
           "desc_proj_220v_3p", "desc_comercial_220v_3p",
           "desc_proj_380v_3p", "desc_comercial_380v_3p")


def _criar_tabela(cur, nome_tabela):
    colunas_sql = ", ".join(f"{c} TEXT" if c != "corrente_nominal_a" else f"{c} REAL NOT NULL" for c in COLUNAS)
    cur.execute(f"CREATE TABLE IF NOT EXISTS {nome_tabela} (id INTEGER PRIMARY KEY, {colunas_sql})")


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    _criar_tabela(cur, "tabela_disjuntor_termomagnetico")
    _criar_tabela(cur, "tabela_disjuntor_ddr")

    placeholders = ", ".join("?" * len(COLUNAS))
    colunas_sql = ", ".join(COLUNAS)

    cur.execute("SELECT COUNT(*) FROM tabela_disjuntor_termomagnetico")
    if cur.fetchone()[0] == 0:
        cur.executemany(f"INSERT INTO tabela_disjuntor_termomagnetico ({colunas_sql}) VALUES ({placeholders})",
                         DADOS_TERMOMAGNETICO)
        print(f"tabela_disjuntor_termomagnetico: {len(DADOS_TERMOMAGNETICO)} linha(s) inserida(s).")
    else:
        print("tabela_disjuntor_termomagnetico já tem dados — não sobrescrita.")

    cur.execute("SELECT COUNT(*) FROM tabela_disjuntor_ddr")
    if cur.fetchone()[0] == 0:
        cur.executemany(f"INSERT INTO tabela_disjuntor_ddr ({colunas_sql}) VALUES ({placeholders})", DADOS_DDR)
        print(f"tabela_disjuntor_ddr: {len(DADOS_DDR)} linha(s) inserida(s).")
    else:
        print("tabela_disjuntor_ddr já tem dados — não sobrescrita.")

    # Parâmetros globais que estavam no cabeçalho da planilha original.
    for chave, valor, desc in [
        ("disjuntor_limite_curva_c_a", 80,
         "Corrente nominal (A) até a qual o disjuntor usa Curva C — acima disso, Curva D "
         "(Tela 5 - Tabela de Disjuntores). Do cabeçalho da planilha original."),
        ("disjuntor_folga_adotada_corrente_pct", 5,
         "Folga adotada sobre a corrente nominal ao escolher o disjuntor (Tela 5 - Tabela de "
         "Disjuntores), em %. Do cabeçalho da planilha original (0,05 = 5%)."),
    ]:
        cur.execute("SELECT id FROM configuracao_global WHERE chave = ?", (chave,))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO configuracao_global (chave, valor, descricao, pendente_confirmacao) "
                        "VALUES (?, ?, ?, ?)", (chave, valor, desc, 0))
            print(f"configuracao_global.{chave} criada com valor {valor}.")
        else:
            print(f"configuracao_global.{chave} já existia — não sobrescrita.")

    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
