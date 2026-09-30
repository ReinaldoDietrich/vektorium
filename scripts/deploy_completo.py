"""
Deploy completo — SE-055/057/058
Executar com: python scripts/deploy_completo.py
Requer: PowerShell elevado (Administrador) para copiar para Program Files
"""
import subprocess, sys, os, shutil

BASE = r"B:\Documentos Programas\App Carga Térmica"
DST = r"C:\Program Files\Vektorium\resources"
os.chdir(BASE)

def titulo(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")

# ====================================================================
# PASSO 1: Criar tabela logs_admin no Supabase
# ====================================================================
titulo("PASSO 1: Criando tabela logs_admin no Supabase Postgres")
try:
    import psycopg2
    conn = psycopg2.connect("postgresql://postgres:Vektorium35372755@db.luzvgsgxutggnbyrhswg.supabase.co:5432/postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'logs_admin')")
    if cur.fetchone()[0]:
        print("  [OK] Tabela logs_admin já existe.")
    else:
        cur.execute("""
            CREATE TABLE logs_admin (
                id BIGSERIAL PRIMARY KEY,
                usuario_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
                acao VARCHAR(100) NOT NULL,
                detalhes TEXT DEFAULT '',
                criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX idx_logs_admin_criado ON logs_admin (criado_em DESC)")
        cur.execute("CREATE INDEX idx_logs_admin_usuario ON logs_admin (usuario_id)")
        cur.execute("ALTER TABLE logs_admin ENABLE ROW LEVEL SECURITY")
        cur.execute("""
            CREATE POLICY logs_admin_service_only ON logs_admin
            FOR ALL
            USING (auth.role() = 'service_role')
            WITH CHECK (auth.role() = 'service_role')
        """)
        print("  [OK] Tabela logs_admin criada com sucesso!")
    cur.close()
    conn.close()
except Exception as e:
    print(f"  [ERRO] {e}")
    print("  Instale psycopg2: pip install psycopg2-binary")

# ====================================================================
# PASSO 2: Configurar secret no Fly.io
# ====================================================================
titulo("PASSO 2: Configurando SUPABASE_SERVICE_ROLE_KEY no Fly.io")
try:
    r = subprocess.run(["fly", "secrets", "list"], capture_output=True, text=True, cwd=BASE)
    if "SUPABASE_SERVICE_ROLE_KEY" in r.stdout:
        print("  [OK] Secret já configurada.")
    else:
        r2 = subprocess.run(
            ["fly", "secrets", "set", f"SUPABASE_SERVICE_ROLE_KEY={os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')}"],
            capture_output=True, text=True, cwd=BASE
        )
        if r2.returncode == 0:
            print("  [OK] Secret configurada.")
        else:
            print(f"  [ERRO] {r2.stderr}")
            print("  Rode: fly auth login   e depois re-execute este script.")
except FileNotFoundError:
    print("  [ERRO] fly CLI não encontrado. Instale: https://fly.io/docs/flyctl/install/")

# ====================================================================
# PASSO 3: Deploy no Fly.io
# ====================================================================
titulo("PASSO 3: Deploy no Fly.io")
try:
    print("  Iniciando deploy... (pode levar 2-3 minutos)")
    r = subprocess.run(["fly", "deploy"], capture_output=True, text=True, cwd=BASE, timeout=300)
    if r.returncode == 0:
        print("  [OK] Deploy concluído!")
    else:
        print(f"  [ERRO] {r.stderr[-500:]}")
except subprocess.TimeoutExpired:
    print("  [ERRO] Deploy excedeu tempo limite de 5 minutos.")
except FileNotFoundError:
    print("  [ERRO] fly CLI não encontrado.")

# ====================================================================
# PASSO 4: Atualizar Electron instalado
# ====================================================================
titulo("PASSO 4: Atualizando Electron em Program Files")

arquivos = [
    ("backend/auth_supabase.py", "backend/auth_supabase.py"),
    ("backend/main.py", "backend/main.py"),
    ("backend/composicao_preco.py", "backend/composicao_preco.py"),
    ("backend/routers/admin.py", "backend/routers/admin.py"),
    ("backend/routers/cloud_projetos.py", "backend/routers/cloud_projetos.py"),
    ("backend/routers/projetos.py", "backend/routers/projetos.py"),
    ("backend/routers/composicao_preco.py", "backend/routers/composicao_preco.py"),
    ("frontend/index.html", "frontend/index.html"),
    ("frontend/css/style.css", "frontend/css/style.css"),
    ("frontend/css/sidebar.css", "frontend/css/sidebar.css"),
    ("frontend/js/tela20_admin.js", "frontend/js/tela20_admin.js"),
    ("frontend/js/sidebar.js", "frontend/js/sidebar.js"),
    ("frontend/js/auth.js", "frontend/js/auth.js"),
    ("frontend/js/main.js", "frontend/js/main.js"),
    ("frontend/js/tela1.js", "frontend/js/tela1.js"),
    ("frontend/js/tela5.js", "frontend/js/tela5.js"),
    ("frontend/js/tela7.js", "frontend/js/tela7.js"),
    ("frontend/js/tela9.js", "frontend/js/tela9.js"),
    ("frontend/js/tela10.js", "frontend/js/tela10.js"),
    ("frontend/js/tela12.js", "frontend/js/tela12.js"),
    ("frontend/js/tela16.js", "frontend/js/tela16.js"),
    ("frontend/js/tela17.js", "frontend/js/tela17.js"),
    ("frontend/js/telaLuminotecnico.js", "frontend/js/telaLuminotecnico.js"),
]

ok = 0
erros = 0
for src_rel, dst_rel in arquivos:
    src = os.path.join(BASE, src_rel)
    dst = os.path.join(DST, dst_rel)
    try:
        shutil.copy2(src, dst)
        ok += 1
    except PermissionError:
        erros += 1
    except Exception as e:
        print(f"  [ERRO] {dst_rel}: {e}")
        erros += 1

if erros == 0:
    print(f"  [OK] {ok} arquivos copiados.")
else:
    print(f"  [ERRO] {erros} arquivos falharam (permissão negada).")
    print("  Execute este script como Administrador!")

titulo("CONCLUÍDO")
print("  Feche e reabra o Vektorium para aplicar as alterações.")
print()
