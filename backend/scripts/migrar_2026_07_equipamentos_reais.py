"""Migração pontual (2026-07): substitui o campo único "calor_liberado_kcal_h" de
cat_tipos_equipamento por fator_calor_rejeitado + fator_simultaneidade (Cenário 1 ASHRAE — motor
e carga no mesmo ambiente) e popula com as 16 estimativas de mercado (fundo de loja/logística)."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")

EQUIPAMENTOS = [
    ("Moedor de Carne / Máquina de Moagem", 3100, 1.00, 0.50),
    ("Serra Fita", 1650, 1.00, 0.40),
    ("Fatiadora de Frios", 400, 1.00, 0.60),
    ("Amaciador de Bifes", 560, 1.00, 0.25),
    ("Embaladora/Seladora Manual", 1000, 0.85, 0.70),
    ("Seladora Automática (Termoencolhível)", 5000, 0.85, 0.60),
    ("Lavadora de Caixas/Louças", 4500, 0.60, 0.40),
    ("Compactador de Papelão/Plástico", 5600, 1.00, 0.15),
    ("Inversor de Frequência (consumo típico 3kW considerado)", 3000, 0.04, 0.90),
    ("Esteira Transportadora/Sorger", 3500, 1.00, 0.75),
    ("Carregador de Bateria (Empilhadeiras)", 8000, 0.15, 0.65),
    ("Terminal de Computador/Coletor (Fixo)", 200, 1.00, 1.00),
    ("Empilhadeira Elétrica (operação)", 10000, 1.00, 1.00),
    ("Transpaleteira Elétrica", 2000, 1.00, 1.00),
    ("Balança Industrial", 60, 1.00, 1.00),
    ("Paletizadora (Filme)", 3750, 1.00, 1.00),
]


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cols = [r[1] for r in cur.execute("PRAGMA table_info(cat_tipos_equipamento)")]
    if "fator_calor_rejeitado" not in cols:
        cur.execute("ALTER TABLE cat_tipos_equipamento ADD COLUMN fator_calor_rejeitado FLOAT")
        print("+ fator_calor_rejeitado")
    if "fator_simultaneidade" not in cols:
        cur.execute("ALTER TABLE cat_tipos_equipamento ADD COLUMN fator_simultaneidade FLOAT")
        print("+ fator_simultaneidade")

    cur.execute("SELECT COUNT(*) FROM camara_completo_equipamentos")
    (qtd_uso,) = cur.fetchone()
    if qtd_uso > 0:
        raise RuntimeError(f"{qtd_uso} linha(s) de câmara já referenciam um tipo de equipamento — "
                            "migração abortada para não quebrar dado real.")

    cur.execute("DELETE FROM cat_tipos_equipamento")
    for nome, pot, fu, fs in EQUIPAMENTOS:
        cur.execute("INSERT INTO cat_tipos_equipamento (nome, potencia_tipica_w, fator_calor_rejeitado, fator_simultaneidade) VALUES (?,?,?,?)",
                    (nome, pot, fu, fs))
    print(f"{len(EQUIPAMENTOS)} tipos de equipamento inseridos")

    conn.commit()
    conn.close()
    print("Migração concluída.")


if __name__ == "__main__":
    run()
