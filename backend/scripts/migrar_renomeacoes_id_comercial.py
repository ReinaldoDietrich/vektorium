# -*- coding: utf-8 -*-
"""Migracao idempotente: aplica as renomeacoes de campo/opcao pedidas em "Instrucoes de Id para
Organizacao dos textos comerciais.docx" (Tela 1 + reflexos em Valvula/CatalogoComercial) nos
DADOS JA SALVOS -- sem isso, projetos existentes ficariam com valor antigo (nao aparece mais no
select, texto "perdido" visualmente ate o usuario reeditar).

Rodar: python -m backend.scripts.migrar_renomeacoes_id_comercial <caminho_db>"""
import sqlite3
import sys


RENOMEACOES = {
    "sistemas_refrigeracao": {
        "tipo_expansao": {"Direta": "Termostática", "Fluído Secundário": "Reguladora de Vazão Manual"},
        "estrutura_compressao": {"Aberta": "Sem Carenagem", "Carenada": "Carenado"},
        "partida": {"Softstarter": "SoftStarter", "Inversor": "Inversor de Frequência",
                    "Inversor + Softstarter": "Inversor de Frequência + SoftStarter"},
        "automacao": {"Gerenciamento": "Gerenciamento Eletrônico"},
        "tipo_automacao_linhas": {"Supervisão": "Supervisão (IHM)"},
    },
    "projetos": {
        "tipo_comando": {"Quadro Distribuído": "Quadro Distribuído (QD)", "Quadro Centralizado": "Quadro de Linhas (QL)"},
    },
    "valvula_selecao_simples": {
        "tipo_expansao": {"Direta": "Termostática", "Fluído Secundário": "Reguladora de Vazão Manual"},
    },
    "valvula_selecao_completo": {
        "tipo_expansao": {"Direta": "Termostática", "Fluído Secundário": "Reguladora de Vazão Manual"},
    },
    "catalogo_comercial": {
        "categoria": {"Supervisão": "Supervisão (IHM)", "Gerenciamento": "Gerenciamento Eletrônico"},
    },
}


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    # Coluna nova: sistemas_refrigeracao.fabricante_valvula
    if "fabricante_valvula" not in _colunas(cur, "sistemas_refrigeracao"):
        cur.execute("ALTER TABLE sistemas_refrigeracao ADD COLUMN fabricante_valvula TEXT")
        print("sistemas_refrigeracao.fabricante_valvula adicionada.")

    tabelas_existentes = {row[0] for row in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    total_linhas = 0
    for tabela, campos in RENOMEACOES.items():
        if tabela not in tabelas_existentes:
            print(f"[aviso] tabela '{tabela}' não existe, pulando.")
            continue
        cols = _colunas(cur, tabela)
        for campo, mapa in campos.items():
            if campo not in cols:
                print(f"[aviso] {tabela}.{campo} não existe, pulando.")
                continue
            for valor_antigo, valor_novo in mapa.items():
                cur.execute(f"UPDATE {tabela} SET {campo} = ? WHERE {campo} = ?", (valor_novo, valor_antigo))
                if cur.rowcount:
                    print(f"{tabela}.{campo}: '{valor_antigo}' -> '{valor_novo}' ({cur.rowcount} linha(s))")
                    total_linhas += cur.rowcount

    con.commit()
    con.close()
    print(f"Concluído. Total de valores renomeados: {total_linhas}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m backend.scripts.migrar_renomeacoes_id_comercial <caminho_db>")
        sys.exit(1)
    migrar(sys.argv[1])
