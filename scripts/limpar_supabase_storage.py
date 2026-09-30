# -*- coding: utf-8 -*-
"""SE-054 — Limpar projetos do Supabase Storage (bucket vektorium-projetos).

Remove todos os arquivos .json de projetos e .session_lock do bucket.
Mantém: auth (contas), tabela assinaturas (licenças).

Uso:
    python scripts/limpar_supabase_storage.py

O script pede o email e senha do Supabase para autenticar.
Mostra o que vai apagar e pede confirmação antes de deletar.
"""

import sys

import httpx

SUPABASE_URL = "https://luzvgsgxutggnbyrhswg.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_BreZGIXnU6_rdBi8n3bF5w_N3HZ56-S"
BUCKET = "vektorium-projetos"


def login(email: str, senha: str) -> dict:
    r = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        json={"email": email, "password": senha},
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        timeout=10,
    )
    if r.status_code != 200:
        print(f"ERRO no login: {r.status_code} {r.text}")
        sys.exit(1)
    return r.json()


def listar_arquivos(token: str, prefix: str) -> list:
    r = httpx.post(
        f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}",
        json={"prefix": prefix, "limit": 1000, "offset": 0},
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    if r.status_code == 200:
        return r.json()
    return []


def deletar_arquivo(token: str, path: str) -> bool:
    r = httpx.delete(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}",
        json=[path],
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    return r.status_code in (200, 204)


def main():
    print("=== Limpeza do Supabase Storage ===")
    print(f"Bucket: {BUCKET}")
    print()

    email = input("Email Supabase: ").strip()
    senha = input("Senha Supabase: ").strip()
    if not email or not senha:
        print("Email e senha obrigatórios.")
        sys.exit(1)

    print("Autenticando...")
    sessao = login(email, senha)
    token = sessao["access_token"]
    user_id = sessao["user"]["id"]
    print(f"Logado como: {sessao['user']['email']} (id: {user_id})")
    print()

    print("Listando arquivos no bucket...")
    arquivos = listar_arquivos(token, f"{user_id}/")

    if not arquivos:
        print("Nenhum arquivo encontrado.")
        return

    print(f"Encontrados: {len(arquivos)} arquivos")
    print()
    for arq in arquivos:
        nome = arq.get("name", "")
        tamanho = arq.get("metadata", {}).get("size", "?")
        print(f"  {nome}  ({tamanho} bytes)")

    print()
    confirma = input(f"DELETAR TODOS os {len(arquivos)} arquivos acima? (sim/nao): ").strip().lower()
    if confirma != "sim":
        print("Cancelado.")
        return

    print()
    deletados = 0
    erros = 0
    for arq in arquivos:
        nome = arq.get("name", "")
        path = f"{user_id}/{nome}"
        if deletar_arquivo(token, path):
            print(f"  DELETADO: {nome}")
            deletados += 1
        else:
            print(f"  ERRO: {nome}")
            erros += 1

    print()
    print(f"Concluído: {deletados} deletados, {erros} erros.")


if __name__ == "__main__":
    main()
