# -*- coding: utf-8 -*-
"""Envia os catálogos do banco local (já com fotos em base64) para o Fly.io."""
import sys

LOCAL_URL = "http://localhost:8842"
FLY_URL = "https://vektorium-calc.fly.dev"
SUPABASE_URL = "https://luzvgsgxutggnbyrhswg.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_BreZGIXnU6_rdBi8n3bF5w_N3HZ56-S"
TIPOS = ["forcadores", "uc", "condensadores", "comercial"]

try:
    import requests
except ImportError:
    print("ERRO: módulo 'requests' não encontrado.")
    sys.exit(1)

if len(sys.argv) < 3:
    print('Uso: python push_local_para_flyio.py "email" "senha"')
    sys.exit(1)

email = sys.argv[1]
senha = sys.argv[2]

print("=" * 60)
print("PUSH LOCAL → FLY.IO")
print("=" * 60)
print(f"Email: {email}")
print(f"Senha recebida: {len(senha)} caracteres")

print("\nTentativa 1: header apikey...")
r1 = requests.post(
    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
    headers={"Content-Type": "application/json", "apikey": SUPABASE_ANON_KEY},
    json={"email": email, "password": senha},
    timeout=15,
)
if r1.ok:
    token = r1.json()["access_token"]
    print("Login OK (apikey)")
else:
    print(f"  Falhou: {r1.status_code} {r1.text[:200]}")
    print("\nTentativa 2: header Authorization Bearer...")
    r2 = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={
            "Content-Type": "application/json",
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        },
        json={"email": email, "password": senha},
        timeout=15,
    )
    if r2.ok:
        token = r2.json()["access_token"]
        print("Login OK (Bearer)")
    else:
        print(f"  Falhou: {r2.status_code} {r2.text[:200]}")
        print("\nTentativa 3: sem apikey, só Bearer...")
        r3 = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            },
            json={"email": email, "password": senha},
            timeout=15,
        )
        if r3.ok:
            token = r3.json()["access_token"]
            print("Login OK (só Bearer)")
        else:
            print(f"  Falhou: {r3.status_code} {r3.text[:200]}")
            print("\nTodas as tentativas falharam.")
            print("Verifique email e senha no painel do Supabase.")
            sys.exit(1)

print("\nIniciando push...\n")
for tipo in TIPOS:
    print(f"{'='*60}")
    print(f"Enviando: {tipo}")
    print(f"{'='*60}")
    try:
        r_export = requests.get(
            f"{LOCAL_URL}/api/catalogo-sync/exportar",
            params={"tipo": tipo},
            timeout=30,
        )
        r_export.raise_for_status()
        dados = r_export.json()
        print(f"  Exportado do local: OK")

        r_push = requests.post(
            f"{FLY_URL}/api/catalogo-sync/receber",
            json=dados,
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        r_push.raise_for_status()
        resultado = r_push.json()
        print(f"  Enviado para Fly.io: {resultado}")
    except Exception as e:
        print(f"  ERRO: {e}")

print(f"\n{'='*60}")
print("PUSH CONCLUÍDO")
print(f"{'='*60}")
