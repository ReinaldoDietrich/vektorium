# -*- coding: utf-8 -*-
"""Aplica TODOS os arquivos SQL no Supabase, em ordem, via conexão direta ao Postgres.
   Execução: 1 comando único; tenta os 3 formatos de conexão do Supabase automaticamente.

   USO:
     cd "B:\\Documentos Programas\\App Carga Térmica"
     $env:SUPABASE_DB_PASSWORD="sua_senha_do_banco"
     .\\venv\\Scripts\\python.exe vektorium_online\\aplicar_no_supabase.py

   A senha nunca sai do seu computador.
"""
import os, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent

# Deduzido da URL do projeto que você já me passou (SUPABASE_URL no .env):
PROJETO_REF = "luzvgsgxutggnbyrhswg"
REGIAO = "sa-east-1"  # projeto criado em São Paulo

# 3 formatos possíveis, em ordem de preferência:
CANDIDATOS = [
    ("Direct (IPv6)",
     f"postgresql://postgres:{{SENHA}}@db.{PROJETO_REF}.supabase.co:5432/postgres"),
    ("Pooler Session (IPv4, porta 5432)",
     f"postgresql://postgres.{PROJETO_REF}:{{SENHA}}@aws-0-{REGIAO}.pooler.supabase.com:5432/postgres"),
    ("Pooler Transaction (IPv4, porta 6543)",
     f"postgresql://postgres.{PROJETO_REF}:{{SENHA}}@aws-0-{REGIAO}.pooler.supabase.com:6543/postgres"),
]

def main():
    senha = os.environ.get("SUPABASE_DB_PASSWORD", "").strip()
    if not senha:
        # aceita também SUPABASE_DB_URL completa, caso o usuário prefira
        url_completa = os.environ.get("SUPABASE_DB_URL", "").strip()
        if not url_completa:
            print("ERRO: defina a senha do banco Postgres antes de rodar:")
            print('  $env:SUPABASE_DB_PASSWORD="sua_senha"')
            print("(A senha foi gerada quando você criou o projeto no Supabase.)")
            sys.exit(1)
        candidatos_uso = [("URL fornecida", url_completa)]
    else:
        candidatos_uso = [(nome, tpl.format(SENHA=senha)) for nome, tpl in CANDIDATOS]

    try:
        import psycopg2
    except ImportError:
        print("Instalando psycopg2-binary...")
        os.system(f'"{sys.executable}" -m pip install --quiet psycopg2-binary')
        import psycopg2

    conn = None
    usado = None
    for nome, url in candidatos_uso:
        print(f"Tentando: {nome}...")
        try:
            conn = psycopg2.connect(url, connect_timeout=8)
            usado = nome
            print(f"  OK conectado via {nome}\n")
            break
        except Exception as e:
            print(f"  falhou: {e}\n")
    if not conn:
        print("Nenhum formato de conexão funcionou. Possíveis causas:")
        print("- senha incorreta")
        print("- projeto Supabase ainda inicializando (aguarde 1 min e tente de novo)")
        print("- firewall/rede bloqueando saída")
        sys.exit(2)

    conn.autocommit = False
    cur = conn.cursor()

    arquivos = [OUT / "0_reset.sql", OUT / "1_schema_postgres.sql"]
    arquivos += sorted(OUT.glob("2_dados_*.sql"))
    arquivos += [OUT / "4_ajustar_sequences.sql", OUT / "3_rls_policies.sql"]

    total = len(arquivos)
    for i, arq in enumerate(arquivos, 1):
        sql = arq.read_text(encoding="utf-8")
        try:
            cur.execute(sql)
            conn.commit()
            print(f"[{i:3d}/{total}] {arq.name}  OK")
        except Exception as e:
            conn.rollback()
            print(f"[{i:3d}/{total}] {arq.name}  ERRO: {e}")
            sys.exit(3)

    print("\n--- Validação (contagem de registros por tabela) ---")
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
    tabelas = [r[0] for r in cur.fetchall()]
    total_reg = 0
    for t in tabelas:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        n = cur.fetchone()[0]
        total_reg += n
        marker = "" if n else "  (vazia)"
        print(f"  {t:45s} {n:8d}{marker}")
    print(f"\nTOTAL: {len(tabelas)} tabelas, {total_reg} registros no Supabase.")
    print(f"Conexão usada: {usado}")

    cur.close()
    conn.close()
    print("\nOK Fase 1 aplicada com sucesso.")

if __name__ == "__main__":
    main()
