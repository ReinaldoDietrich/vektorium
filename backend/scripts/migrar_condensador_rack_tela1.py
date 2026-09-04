# -*- coding: utf-8 -*-
"""Migração aditiva: move a seleção de estrutura do Condensador Remoto da Tela 1 (Sistema) pra
Tela 6 (Rack) e cria o novo campo "Seleção Condensador a Ar" na Tela 1.

- rack_paralelo.tipo_condensador (String) — novo, editável na Tela 6. Faz backfill a partir do
  antigo sistemas_refrigeracao.condensador_tipo de cada rack, traduzindo pro novo vocabulário
  fechado (mesmas 4 opções, só o texto mudou).
- sistemas_refrigeracao.selecao_condensador_ar (String) — novo campo "Nenhum"/"Remoto"/"Onboard",
  sem valor padrão (fica em branco até o usuário escolher).

As colunas antigas (condensador_tipo, tipo_motor_condensador, protecao_aletas em
sistemas_refrigeracao) NÃO são apagadas — só deixam de ser usadas (SQLite não dropa coluna sem
recriar a tabela inteira; mantê-las órfãs é seguro e não afeta nada).

Idempotente. Rodar: python -m backend.scripts.migrar_condensador_rack_tela1 <caminho_db>
"""
import sys
import sqlite3

MAPA_ESTRUTURA = {
    "PLANO - FLUXO VERTICAL": "Plano (Fluxo Vertical)",
    "V - FLUXO HORIZONTAL": "V (Fluxo Horizontal)",
    "ONBOARD": "Onboard",
    "PLANO - ONBOARD": "Plano Onboard",
}


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    cols_sis = _colunas(cur, "sistemas_refrigeracao")
    if "selecao_condensador_ar" not in cols_sis:
        cur.execute("ALTER TABLE sistemas_refrigeracao ADD COLUMN selecao_condensador_ar TEXT")
        print("sistemas_refrigeracao.selecao_condensador_ar adicionada.")
    else:
        print("sistemas_refrigeracao.selecao_condensador_ar já existe — nada a fazer.")

    cols_rack = _colunas(cur, "rack_paralelo")
    if "tipo_condensador" not in cols_rack:
        cur.execute("ALTER TABLE rack_paralelo ADD COLUMN tipo_condensador TEXT")
        print("rack_paralelo.tipo_condensador adicionada.")
    else:
        print("rack_paralelo.tipo_condensador já existe — nada a fazer.")

    # Backfill: só preenche onde ainda está em branco, a partir do valor antigo do Sistema.
    cur.execute("""
        SELECT r.id, s.condensador_tipo FROM rack_paralelo r
        JOIN sistemas_refrigeracao s ON s.id = r.sistema_id
        WHERE r.tipo_condensador IS NULL AND s.condensador_tipo IS NOT NULL
    """)
    linhas = cur.fetchall()
    for rack_id, condensador_tipo_antigo in linhas:
        novo = MAPA_ESTRUTURA.get((condensador_tipo_antigo or "").strip().upper())
        if novo:
            cur.execute("UPDATE rack_paralelo SET tipo_condensador=? WHERE id=?", (novo, rack_id))
            print(f"rack_paralelo id={rack_id}: tipo_condensador preenchido com '{novo}' "
                  f"(a partir de Sistema.condensador_tipo='{condensador_tipo_antigo}').")

    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
