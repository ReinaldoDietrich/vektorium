# -*- coding: utf-8 -*-
"""Migração aditiva: cria a chave "reducao_ec_condensador_pct" em configuracao_global — redução
MÁXIMA de consumo do ventilador do Condensador Remoto quando o motor é EC (Eletronicamente
Comutado), independente do reducao_inversor_pct do compressor (equipamento e decisão diferentes,
confirmado pelo usuário 2026-07-21). Só INSERT se a chave ainda não existir -- idempotente, nunca
sobrescreve valor já customizado.

Rodar: python -m backend.scripts.migrar_reducao_ec_condensador <caminho_db>
"""
import sys
import sqlite3


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    cur.execute("SELECT id FROM configuracao_global WHERE chave = 'reducao_ec_condensador_pct'")
    if cur.fetchone() is None:
        cur.execute("INSERT INTO configuracao_global (chave, valor, descricao, pendente_confirmacao) VALUES (?, ?, ?, ?)",
                     ("reducao_ec_condensador_pct", 40,
                      "Redução MÁXIMA de consumo do ventilador do Condensador Remoto (Rack Paralelo, Tela 6) "
                      "quando o modelo escolhido tem motor EC, aplicada quando o condensador opera no piso de "
                      "20% de carga (mesma folga de referência do Inversor de Frequência, tecnologia "
                      "equivalente) — decresce linearmente até 0% em 100% de carga. Faixa típica de literatura "
                      "(EC vs. motor AC de rotação fixa, ventiladores de condensador): 30%-50% — ver "
                      "calculo_consumo.py", 0))
        print("configuracao_global.reducao_ec_condensador_pct criada com valor 40.")
    else:
        print("configuracao_global.reducao_ec_condensador_pct já existia — não sobrescrita.")
    con.commit()
    con.close()


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
