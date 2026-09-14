# -*- coding: utf-8 -*-
"""Cria índices em todas as colunas FK que ainda não possuem.
Funciona tanto em SQLite (banco local) quanto em Postgres (Fly.io).
Seguro para re-executar: usa CREATE INDEX IF NOT EXISTS."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

FK_INDICES = [
    ("projetos", "estacao_climatologica_id"),
    ("projetos", "estacao_inmet_id"),
    ("projetos", "revisao_de"),
    ("sistemas_refrigeracao", "projeto_id"),
    ("cat_faixa_area_tabela02", "tabela02_id"),
    ("cat_modelos_expositor", "banco_id"),
    ("forcador_linhas", "fabricante_id"),
    ("forcador_linhas", "linha_anterior_id"),
    ("forcador_modelos", "linha_id"),
    ("forcador_capacidades", "modelo_id"),
    ("forcador_eletricos", "modelo_id"),
    ("forcador_fisicos", "modelo_id"),
    ("forcador_dimensionais", "modelo_id"),
    ("forcador_importacoes", "linha_id"),
    ("forcador_fatores_gas", "linha_id"),
    ("condensador_linhas", "fabricante_id"),
    ("condensador_linhas", "linha_anterior_id"),
    ("condensador_modelos", "linha_id"),
    ("condensador_fatores", "linha_id"),
    ("condensador_importacoes", "linha_id"),
    ("cat_modelos_valvula", "fabricante_id"),
    ("camaras_completo", "sistema_id"),
    ("camaras_completo", "produto_id"),
    ("camaras_completo", "tipo_embalagem_id"),
    ("camaras_completo", "isolamento_parede_id"),
    ("camaras_completo", "isolamento_teto_id"),
    ("camaras_completo", "isolamento_piso_id"),
    ("camaras_completo", "tipo_ambiente_lumino_id"),
    ("camaras_completo", "modelo_luminaria_id"),
    ("camara_completo_portas", "camara_id"),
    ("camara_completo_equipamentos", "camara_id"),
    ("camara_completo_equipamentos", "tipo_equipamento_id"),
    ("camara_completo_forcadores", "camara_id"),
    ("camara_completo_forcadores", "fabricante_id"),
    ("camara_completo_forcadores", "linha_id"),
    ("camara_completo_valvulas", "forcador_selecao_id"),
    ("camaras_simples", "sistema_id"),
    ("camaras_simples", "tabela02_id"),
    ("camaras_simples", "tipo_ambiente_lumino_id"),
    ("camaras_simples", "modelo_luminaria_id"),
    ("camara_simples_forcadores", "camara_id"),
    ("camara_simples_forcadores", "fabricante_id"),
    ("camara_simples_forcadores", "linha_id"),
    ("camara_simples_valvulas", "forcador_selecao_id"),
    ("expositores", "sistema_id"),
    ("expositores", "setor_id"),
    ("expositores", "modelo_expositor_id"),
    ("expositor_modulos", "expositor_id"),
    ("uc_unidades", "catalogo_id"),
    ("uc_eletricas", "unidade_id"),
    ("uc_capacidades", "unidade_id"),
    ("campo_catalogo_opcao", "campo_id"),
    ("uc_selecao_sistema", "sistema_id"),
    ("uc_selecao_sistema", "catalogo_id"),
    ("id_comercial", "fator_venda_padrao_id"),
    ("paineis_termicos", "projeto_id"),
    ("paineis_termicos", "camara_completo_id"),
    ("paineis_termicos", "camara_simples_id"),
    ("portas_frigorificas", "projeto_id"),
    ("portas_frigorificas", "camara_completo_id"),
    ("portas_frigorificas", "camara_simples_id"),
    ("rack_paralelo", "sistema_id"),
    ("rack_condensador_selecao", "rack_id"),
    ("compressor_rack", "rack_id"),
    ("material_rack", "rack_id"),
    ("material_tela10", "projeto_id"),
    ("material_tela10", "centro_custo_id"),
    ("equipamento_valor_tela10", "projeto_id"),
    ("equipamento_valor_tela10", "centro_custo_id"),
    ("item_composicao_mestre", "centro_custo_id"),
    ("item_composicao_mestre", "fator_id"),
    ("composicao_preco_item", "projeto_id"),
    ("composicao_preco_item", "centro_custo_id"),
    ("composicao_preco_item", "fator_id"),
    ("condicao_pagamento_projeto", "projeto_id"),
    ("condicao_pagamento_parcela", "projeto_id"),
    ("comissao_vendedor_projeto", "projeto_id"),
    ("comissao_vendedor_projeto", "vendedor_id"),
]


def migrar(db_path=None):
    if db_path:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # Limpar órfãos antes de ativar foreign_keys
        cur.execute("PRAGMA foreign_key_check")
        orfaos = cur.fetchall()
        if orfaos:
            from collections import Counter
            por_tabela = Counter(r[0] for r in orfaos)
            for tabela, qtd in por_tabela.items():
                rowids = [r[1] for r in orfaos if r[0] == tabela]
                for rid in rowids:
                    cur.execute(f"DELETE FROM [{tabela}] WHERE rowid=?", (rid,))
                print(f"  Removidos {qtd} orfaos de {tabela}")
            conn.commit()
        # Criar índices
        criados = 0
        for tabela, coluna in FK_INDICES:
            nome = f"ix_{tabela}_{coluna}"
            try:
                cur.execute(f"CREATE INDEX IF NOT EXISTS [{nome}] ON [{tabela}] ([{coluna}])")
                criados += 1
            except Exception as e:
                print(f"  AVISO: {nome} -> {e}")
        conn.commit()
        conn.close()
        print(f"  {criados} indices criados/verificados em SQLite")
    else:
        from sqlalchemy import create_engine, text
        pg_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
        if not pg_url:
            print("Sem DATABASE_URL/POSTGRES_URL — pulando Postgres")
            return
        engine = create_engine(pg_url)
        with engine.begin() as conn:
            criados = 0
            for tabela, coluna in FK_INDICES:
                nome = f"ix_{tabela}_{coluna}"
                try:
                    conn.execute(text(f'CREATE INDEX IF NOT EXISTS "{nome}" ON "{tabela}" ("{coluna}")'))
                    criados += 1
                except Exception as e:
                    print(f"  AVISO: {nome} -> {e}")
            print(f"  {criados} indices criados/verificados em Postgres")


if __name__ == "__main__":
    db = os.path.join(os.path.dirname(__file__), "..", "..", "database", "carga_termica.db")
    if os.path.exists(db):
        print("Migrando SQLite...")
        migrar(db)
    print("Migrando Postgres...")
    migrar()
    print("Concluido.")
