# -*- coding: utf-8 -*-
"""Insere bombas de água/processo (diversos portes, motor trifásico padrão IR3/NBR 17094-1) na
tabela de equipamentos (cat_tipos_equipamento) — mesmo padrão do seed.py, idempotente (não
duplica se já existir um registro com o mesmo nome).

Potência elétrica = potência nominal do motor (CV x 735,5W) / rendimento mínimo IR3 por porte
(estimativa de mercado, motor trifásico 4 polos padrão — não é dado de catálogo de um fabricante
específico; ajustar depois com dado real do fabricante da bomba selecionada, quando disponível).

fator_calor_rejeitado: diferente da maioria dos outros equipamentos da tabela (que dissipam ~100%
da potência como calor sensível no ambiente), a energia de uma bomba vai majoritariamente para a
água bombeada (sai da câmara pela tubulação) — só a ineficiência do motor (1 - rendimento) mais uma
pequena margem de perda mecânica da bomba (mancal/selo) vira calor no ambiente onde o conjunto está
instalado. Por isso o fator cai conforme o motor fica maior/mais eficiente.

fator_simultaneidade: 0,40 (uso intermitente típico — recirculação/lavagem/dreno) por padrão,
ajustável conforme o uso real de cada bomba no projeto.

Rodar direto: python -m backend.scripts.inserir_bombas_agua <caminho_db>
"""
import sys
import sqlite3

BOMBAS = [
    # (nome, potencia_w, fator_calor_rejeitado, fator_simultaneidade)
    ("Bomba de Água/Processo 1 CV", 900, 0.20, 0.40),
    ("Bomba de Água/Processo 3 CV", 2600, 0.15, 0.40),
    ("Bomba de Água/Processo 5 CV", 4200, 0.13, 0.40),
    ("Bomba de Água/Processo 10 CV", 8200, 0.11, 0.40),
    ("Bomba de Água/Processo 20 CV", 16000, 0.09, 0.40),
    ("Bomba de Água/Processo 50 CV", 39300, 0.07, 0.40),
]


def inserir(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    criadas = 0
    for nome, pot, fu, fs in BOMBAS:
        cur.execute("SELECT id FROM cat_tipos_equipamento WHERE nome = ?", (nome,))
        if cur.fetchone():
            print(f"Já existe, pulando: {nome}")
            continue
        cur.execute(
            "INSERT INTO cat_tipos_equipamento (nome, potencia_tipica_w, fator_calor_rejeitado, fator_simultaneidade) "
            "VALUES (?, ?, ?, ?)", (nome, pot, fu, fs))
        criadas += 1
        print(f"Criada: {nome} ({pot}W)")
    con.commit()
    con.close()
    print(f"Concluído — {criadas} bomba(s) inserida(s).")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    inserir(caminho)
