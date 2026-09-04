# -*- coding: utf-8 -*-
"""Migração idempotente de dados: sistemas_refrigeracao.tipo_automacao_linhas — o valor "Controle"
passa a se chamar "Controle Simples" (nova opção "Controle + Acesso Remoto" adicionada ao lado de
"Supervisão"). Sem essa migração, sistemas antigos com "Controle" ficariam com um valor que não
bate mais com nenhuma opção do select.

Rodar: python -m backend.scripts.migrar_tipo_automacao_linhas <caminho_db>
"""
import sys
import sqlite3


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cur.execute("UPDATE sistemas_refrigeracao SET tipo_automacao_linhas = 'Controle Simples' WHERE tipo_automacao_linhas = 'Controle'")
    print(f"{cur.rowcount} sistema(s) atualizado(s): 'Controle' -> 'Controle Simples'.")
    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
