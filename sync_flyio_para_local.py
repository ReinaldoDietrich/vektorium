import requests
import getpass

SUPABASE_URL = "https://luzvgsgxutggnbyrhswg.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_BreZGIXnU6_rdBi8n3bF5w_N3HZ56-S"

FLY_URL = "https://vektorium-calc.fly.dev"
LOCAL_URL = "http://127.0.0.1:8842"

TIPOS = [
    "forcadores",
    "uc",
    "condensadores",
    "comercial",
]

print("=" * 60)
print("SYNC FLY.IO → LOCAL")
print("=" * 60)

email = input("Email: ")
senha = getpass.getpass("Senha: ")

print("\nFazendo login no Supabase...")
r_login = requests.post(
    f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
    headers={"Content-Type": "application/json", "apikey": SUPABASE_ANON_KEY},
    json={"email": email, "password": senha},
    timeout=15
)

if not r_login.ok:
    erro = r_login.json()
    print(f"✗ ERRO no login: {erro.get('error_description') or erro.get('msg') or r_login.status_code}")
    exit(1)

token = r_login.json()["access_token"]
print("✓ Login OK\n")

headers_fly = {"Authorization": f"Bearer {token}"}

for tipo in TIPOS:
    print(f"\n{'=' * 60}")
    print(f"Sincronizando: {tipo}")
    print(f"{'=' * 60}")

    try:
        response_get = requests.get(
            f"{FLY_URL}/api/catalogo-sync/exportar",
            params={"tipo": tipo},
            headers=headers_fly,
            timeout=120
        )

        response_get.raise_for_status()

        dados = response_get.json()

        print("✓ Dados recebidos do Fly.io")

        response_post = requests.post(
            f"{LOCAL_URL}/api/catalogo-sync/receber",
            json=dados,
            timeout=120
        )

        response_post.raise_for_status()

        resultado = response_post.json()

        print("✓ Dados enviados para o banco local")
        print(f"Resultado: {resultado}")

        if isinstance(resultado, dict):
            print(f"  Criados:     {resultado.get('criados', 0)}")
            print(f"  Atualizados: {resultado.get('atualizados', 0)}")

    except requests.exceptions.RequestException as e:
        print(f"✗ ERRO em '{tipo}': {e}")

    except ValueError as e:
        print(f"✗ ERRO ao interpretar JSON em '{tipo}': {e}")

print("\n" + "=" * 60)
print("SINCRONIZAÇÃO CONCLUÍDA")
print("=" * 60)
