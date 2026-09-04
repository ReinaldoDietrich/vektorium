"""Migração pontual (2026-07): adiciona ao catálogo cat_tipos_equipamento os tanques
pasteurizadores (500L/1.000L lote, 4.000L/h e 10.000L/h contínuo) e as quebradoras de ovos
(3 faixas de capacidade), a partir das tabelas de referência fornecidas pelo usuário. Potência
considerada = Calor Sensível dos Motores + Radiação Térmica do Equipamento (quando houver),
ambos no ponto médio da faixa informada. Fu=100% e Fs conforme a tabela (aditivo — não apaga
os 16 equipamentos já cadastrados)."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")

# (nome, potencia_considerada_w, fator_calor_rejeitado, fator_simultaneidade)
EQUIPAMENTOS = [
    ("Tanque Pasteurizador 500L (Lote, Elétrico/Camisa Dupla)", 3450, 1.00, 1.00),
    ("Tanque Pasteurizador 1.000L (Lote, Elétrico/Camisa Dupla)", 5150, 1.00, 1.00),
    ("Tanque Pasteurizador 4.000L/h (Contínuo, SKID Placas/Caldeira Ext.)", 14850, 1.00, 1.00),
    ("Tanque Pasteurizador 10.000L/h (Contínuo, SKID Placas/Caldeira Ext.)", 29750, 1.00, 1.00),
    ("Quebradora de Ovos ~3.000-6.000 ovos/h", 600, 1.00, 1.00),
    ("Quebradora de Ovos ~12.000-20.000 ovos/h", 1850, 1.00, 1.00),
    ("Quebradora de Ovos ~30.000-45.000 ovos/h", 4750, 1.00, 1.00),
]


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    inseridos = 0
    for nome, pot, fu, fs in EQUIPAMENTOS:
        cur.execute("SELECT id FROM cat_tipos_equipamento WHERE nome = ?", (nome,))
        if cur.fetchone():
            print(f"já existe, ignorado: {nome}")
            continue
        cur.execute("INSERT INTO cat_tipos_equipamento (nome, potencia_tipica_w, fator_calor_rejeitado, fator_simultaneidade) VALUES (?,?,?,?)",
                    (nome, pot, fu, fs))
        inseridos += 1
        print(f"inserido: {nome}")
    conn.commit()
    conn.close()
    print(f"{inseridos} equipamento(s) novo(s) inserido(s).")


if __name__ == "__main__":
    run()
