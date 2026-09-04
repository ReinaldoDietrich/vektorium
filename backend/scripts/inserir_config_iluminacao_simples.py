# -*- coding: utf-8 -*-
"""Insere 3 configurações globais pra estimar a Potência Ilum. da Câmara Simples (que não tem
qtd_luminarias/potencia_luminaria como a Câmara Completo): W/m², lm/m² e Potência da Lâmpada (W).
Fórmula (Tela 3): Potência Ilum. = ((área x W/m²) / lm/m²) x potência_lâmpada.

Idempotente — não duplica se a chave já existir. Começam em 0 (pendente_confirmacao=True), mesmo
padrão de potencia_dreno_wm/potencia_portas_wm — o usuário preenche o valor real em Configurações.

Rodar direto: python -m backend.scripts.inserir_config_iluminacao_simples <caminho_db>
"""
import sys
import sqlite3

CONFIGS = [
    ("iluminacao_simples_w_m2", "Iluminação Câmara Simples — Potência de referência (W/m²), usada na Potência Ilum."),
    ("iluminacao_simples_lm_m2", "Iluminação Câmara Simples — Iluminância de referência (lm/m², nível de lux do projeto luminotécnico), usada na Potência Ilum."),
    ("iluminacao_simples_potencia_lampada_w", "Iluminação Câmara Simples — Potência de uma lâmpada de referência (W), usada na Potência Ilum."),
]


def inserir(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()
    criadas = 0
    for chave, descricao in CONFIGS:
        cur.execute("SELECT id FROM configuracao_global WHERE chave = ?", (chave,))
        if cur.fetchone():
            print(f"Já existe, pulando: {chave}")
            continue
        cur.execute(
            "INSERT INTO configuracao_global (chave, valor, descricao, pendente_confirmacao) VALUES (?, 0, ?, 1)",
            (chave, descricao))
        criadas += 1
        print(f"Criada: {chave}")
    con.commit()
    con.close()
    print(f"Concluído — {criadas} configuração(ões) inserida(s).")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    inserir(caminho)
