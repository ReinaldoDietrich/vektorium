# -*- coding: utf-8 -*-
"""Insere no FINAL da Tela A - Tabelas de Válvulas de Expansão os 11 modelos novos da linha VALEX
(Full Gauge) lançados no FG Toolbox v4.0.0 (release notes oficiais, mar/2025): série SB5xx
(SB513/517/520/525/530/535/540) e SB8xx (SB840/845/855/865). Numeração = orifício em décimos de mm.

Mecânica: SB513 e SB520 vêm COMPLETAS (fonte: relatório VEE Selector do próprio projeto —
5/16"x5/16", 12 Vdc <> 10%, Unipolar) + compatibilidade confirmada com VX-1025E. Os demais entram
só com fabricante/tipo/modelo — sem inventar conexões/tipo não publicados (editar em Configurações
quando houver datasheet).

Idempotente e ADITIVO: só insere modelo/par que ainda não existe; não altera nada existente.
Rodar: ./venv/Scripts/python.exe -m backend.scripts.inserir_valvulas_sb5_sb8 <caminho_db>
"""
import sys
import sqlite3

_T = "12 Vdc <> 10%"
# (modelo, entrada, saida, tensao, tipo_motor) — None = desconhecido (não inventar)
MODELOS = [
    ("SB513", '5/16"', '5/16"', _T, "Unipolar"),   # confirmado (relatório VEE Selector)
    ("SB517", None, None, None, None),
    ("SB520", '5/16"', '5/16"', _T, "Unipolar"),   # confirmado (relatório VEE Selector)
    ("SB525", None, None, None, None),
    ("SB530", None, None, None, None),
    ("SB535", None, None, None, None),
    ("SB540", None, None, None, None),
    ("SB840", None, None, None, None),
    ("SB845", None, None, None, None),
    ("SB855", None, None, None, None),
    ("SB865", None, None, None, None),
]
COMPATIBILIDADE = [("SB513", "VX-1025E"), ("SB520", "VX-1025E")]  # só o confirmado no relatório


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    ins_v = ins_c = 0
    for modelo, ent, sai, tensao, tipo in MODELOS:
        if cur.execute("SELECT 1 FROM tabela_valvula_expansao WHERE modelo=?", (modelo,)).fetchone():
            print(f"{modelo}: já existe — pulado.")
            continue
        cur.execute("""INSERT INTO tabela_valvula_expansao
            (fabricante, tipo_expansao, modelo, conexao_entrada, conexao_saida, tensao, tipo_motor,
             equalizacao, gas_compativel) VALUES ('FullGauge','Eletrônica',?,?,?,?,?,NULL,NULL)""",
            (modelo, ent, sai, tensao, tipo))
        ins_v += 1
    for valv, ctrl in COMPATIBILIDADE:
        if cur.execute("SELECT 1 FROM tabela_compatibilidade_valvula WHERE valvula_modelo=? AND controlador_modelo=?",
                        (valv, ctrl)).fetchone():
            print(f"compat {valv}×{ctrl}: já existe — pulado.")
            continue
        cur.execute("INSERT INTO tabela_compatibilidade_valvula (valvula_modelo, controlador_modelo) VALUES (?,?)",
                    (valv, ctrl))
        ins_c += 1
    con.commit()
    con.close()
    print(f"Concluído: {ins_v} válvula(s) e {ins_c} compatibilidade(s) inseridas no final das tabelas.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
