-- ============================================================
-- VEKTORIUM — FASE 2: Auth + RLS refinado por papel/assinatura
-- ============================================================
-- O que este arquivo faz:
--   1. Cria tabelas de identidade: usuarios, assinaturas, dispositivos
--   2. Cria matriz de permissões: permissoes_por_papel (papel × módulo × ver/editar)
--   3. Cria trigger que preenche `usuarios` quando alguém se cadastra no Supabase Auth
--   4. Cria função has_module_perm(modulo, acao) usada nas policies RLS
--   5. Substitui as policies "auth_read_*" da Fase 1 por policies condicionadas a:
--         - assinatura ativa
--         - papel do usuário tem VER=true no módulo daquela tabela
--   6. Cria papéis iniciais: 'master' (acesso total, gerencia catálogos) e 'comum' (só usa)
--   7. Semeia matriz de permissões default para 'comum' (todos os módulos vendáveis)
--
-- Executar no SQL Editor do Supabase OU pelo script aplicar_no_supabase.py
-- ============================================================

-- ============================================================
-- 1. TABELAS DE IDENTIDADE / ASSINATURA
-- ============================================================

CREATE TABLE IF NOT EXISTS "usuarios" (
  "id"          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  "email"       TEXT NOT NULL,
  "nome"        TEXT,
  "papel"       TEXT NOT NULL DEFAULT 'comum',     -- 'master' | 'comum'
  "criado_em"   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "assinaturas" (
  "id"                    SERIAL PRIMARY KEY,
  "usuario_id"            UUID NOT NULL REFERENCES "usuarios"("id") ON DELETE CASCADE,
  "status"                TEXT NOT NULL DEFAULT 'trial',   -- 'active' | 'trial' | 'past_due' | 'canceled'
  "plano"                 TEXT NOT NULL DEFAULT 'trial',
  "iugu_subscription_id"  TEXT,
  "vence_em"              TIMESTAMPTZ,
  "criado_em"             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  "atualizado_em"         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS "idx_assinaturas_usuario" ON "assinaturas"("usuario_id");

CREATE TABLE IF NOT EXISTS "dispositivos" (
  "id"             SERIAL PRIMARY KEY,
  "usuario_id"     UUID NOT NULL REFERENCES "usuarios"("id") ON DELETE CASCADE,
  "fingerprint"    TEXT NOT NULL,
  "ultimo_acesso"  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  "ativo"          BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE ("usuario_id", "fingerprint")
);

-- ============================================================
-- 2. MATRIZ DE PERMISSÕES: papel × módulo × ver/editar
-- ============================================================
-- Módulos vendáveis mapeados no ADR (seção 3.6):
--   'camara_completo', 'camara_simples', 'expositor', 'compilacao_linhas',
--   'rack', 'paineis_portas', 'compilacao_geral', 'consumo', 'materiais',
--   'luminotecnico', 'comparativo', 'proposta',
--   'cat_forcadores', 'cat_uc', 'cat_condensadores',
--   'cadastro_comercial', 'configuracoes'

CREATE TABLE IF NOT EXISTS "permissoes_por_papel" (
  "papel"   TEXT NOT NULL,
  "modulo"  TEXT NOT NULL,
  "ver"     BOOLEAN NOT NULL DEFAULT FALSE,
  "editar"  BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY ("papel", "modulo")
);

-- ============================================================
-- 3. TRIGGER: quando um user cria conta no Supabase Auth, popula 'usuarios'
-- ============================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.usuarios (id, email, nome, papel)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'nome', split_part(NEW.email, '@', 1)),
    'comum'
  )
  ON CONFLICT (id) DO NOTHING;
  -- também cria uma assinatura em modo trial (7 dias)
  INSERT INTO public.assinaturas (usuario_id, status, plano, vence_em)
  VALUES (NEW.id, 'trial', 'trial', NOW() + INTERVAL '7 days')
  ON CONFLICT DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Backfill: users que já existem em auth.users antes deste script rodar
INSERT INTO public.usuarios (id, email, nome, papel)
SELECT u.id,
       u.email,
       COALESCE(u.raw_user_meta_data->>'nome', split_part(u.email, '@', 1)),
       'comum'
  FROM auth.users u
 WHERE u.id NOT IN (SELECT id FROM public.usuarios);

INSERT INTO public.assinaturas (usuario_id, status, plano, vence_em)
SELECT u.id, 'trial', 'trial', NOW() + INTERVAL '7 days'
  FROM public.usuarios u
 WHERE u.id NOT IN (SELECT usuario_id FROM public.assinaturas);

-- ============================================================
-- 4. FUNÇÕES HELPER para RLS
-- ============================================================

-- Retorna o papel do usuário logado
CREATE OR REPLACE FUNCTION public.current_papel()
RETURNS TEXT AS $$
  SELECT papel FROM public.usuarios WHERE id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Retorna TRUE se o usuário tem assinatura ativa (status = active OU trial ainda válido)
CREATE OR REPLACE FUNCTION public.tem_assinatura_ativa()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.assinaturas
    WHERE usuario_id = auth.uid()
      AND (status = 'active' OR (status = 'trial' AND vence_em > NOW()))
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Retorna TRUE se o papel do usuário tem 'ver' no módulo
CREATE OR REPLACE FUNCTION public.pode_ver(p_modulo TEXT)
RETURNS BOOLEAN AS $$
  SELECT COALESCE(
    (SELECT ver FROM public.permissoes_por_papel
     WHERE papel = public.current_papel() AND modulo = p_modulo),
    FALSE
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Retorna TRUE se pode editar no módulo (editar sempre exige ver)
CREATE OR REPLACE FUNCTION public.pode_editar(p_modulo TEXT)
RETURNS BOOLEAN AS $$
  SELECT COALESCE(
    (SELECT editar FROM public.permissoes_por_papel
     WHERE papel = public.current_papel() AND modulo = p_modulo),
    FALSE
  );
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- Atalho: master ignora tudo
CREATE OR REPLACE FUNCTION public.eh_master()
RETURNS BOOLEAN AS $$
  SELECT public.current_papel() = 'master';
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- ============================================================
-- 5. RLS nas tabelas de identidade
-- ============================================================

ALTER TABLE "usuarios" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "usuario_le_a_si_mesmo" ON "usuarios";
CREATE POLICY "usuario_le_a_si_mesmo" ON "usuarios"
  FOR SELECT TO authenticated USING (id = auth.uid() OR public.eh_master());
DROP POLICY IF EXISTS "master_edita_usuarios" ON "usuarios";
CREATE POLICY "master_edita_usuarios" ON "usuarios"
  FOR UPDATE TO authenticated USING (public.eh_master()) WITH CHECK (public.eh_master());

ALTER TABLE "assinaturas" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "usuario_le_propria_assinatura" ON "assinaturas";
CREATE POLICY "usuario_le_propria_assinatura" ON "assinaturas"
  FOR SELECT TO authenticated USING (usuario_id = auth.uid() OR public.eh_master());

ALTER TABLE "dispositivos" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "usuario_gerencia_seus_dispositivos" ON "dispositivos";
CREATE POLICY "usuario_gerencia_seus_dispositivos" ON "dispositivos"
  FOR ALL TO authenticated USING (usuario_id = auth.uid() OR public.eh_master())
  WITH CHECK (usuario_id = auth.uid() OR public.eh_master());

ALTER TABLE "permissoes_por_papel" ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "todos_leem_permissoes" ON "permissoes_por_papel";
CREATE POLICY "todos_leem_permissoes" ON "permissoes_por_papel"
  FOR SELECT TO authenticated USING (TRUE);
DROP POLICY IF EXISTS "master_gerencia_permissoes" ON "permissoes_por_papel";
CREATE POLICY "master_gerencia_permissoes" ON "permissoes_por_papel"
  FOR ALL TO authenticated USING (public.eh_master()) WITH CHECK (public.eh_master());

-- ============================================================
-- 6. RLS refinado no CATÁLOGO
-- Substitui as policies "auth_read_*" da Fase 1 por regras baseadas em
-- assinatura ativa + permissão por módulo. Master ignora tudo.
-- ============================================================

-- Mapeamento tabela → módulo. Aqui usamos regra simples: todo o catálogo é
-- controlado pelo módulo 'catalogo_base' até a matriz por módulo estar em uso.
-- Master sempre passa. Cliente comum: precisa de assinatura ativa E ver='catalogo_base'.

DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename NOT IN ('usuarios','assinaturas','dispositivos','permissoes_por_papel')
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS "auth_read_%s" ON %I', r.tablename, r.tablename);
    EXECUTE format('DROP POLICY IF EXISTS "cat_read_%s" ON %I', r.tablename, r.tablename);
    EXECUTE format('DROP POLICY IF EXISTS "cat_write_%s" ON %I', r.tablename, r.tablename);
    EXECUTE format(
      'CREATE POLICY "cat_read_%s" ON %I FOR SELECT TO authenticated
         USING (public.eh_master() OR (public.tem_assinatura_ativa() AND public.pode_ver(''catalogo_base'')))',
      r.tablename, r.tablename);
    -- Só master escreve no catálogo. Clientes comuns nunca alteram.
    EXECUTE format(
      'CREATE POLICY "cat_write_%s" ON %I FOR ALL TO authenticated
         USING (public.eh_master()) WITH CHECK (public.eh_master())',
      r.tablename, r.tablename);
  END LOOP;
END $$;

-- ============================================================
-- 6.b FUNÇÕES ADMIN — conceder/revogar vitalícia, promover master
-- Só master pode executar (a função checa antes).
-- Uso:
--   SELECT conceder_vitalicia('fulano@empresa.com');
--   SELECT revogar_vitalicia('fulano@empresa.com');
--   SELECT promover_master('parceiro@empresa.com');
--   SELECT rebaixar_master('parceiro@empresa.com');   -- volta a 'comum'
-- ============================================================

CREATE OR REPLACE FUNCTION public.conceder_vitalicia(p_email TEXT)
RETURNS TEXT AS $$
DECLARE v_id UUID;
BEGIN
  IF NOT public.eh_master() THEN
    RAISE EXCEPTION 'Apenas master pode conceder vitalícia';
  END IF;
  SELECT id INTO v_id FROM public.usuarios WHERE email = p_email;
  IF v_id IS NULL THEN
    RETURN 'Usuário não encontrado: ' || p_email || ' (peça pra ele criar conta antes)';
  END IF;
  UPDATE public.assinaturas
     SET status='active', plano='vitalicio', vence_em=NULL, atualizado_em=NOW()
   WHERE usuario_id = v_id;
  IF NOT FOUND THEN
    INSERT INTO public.assinaturas (usuario_id, status, plano, vence_em)
    VALUES (v_id, 'active', 'vitalicio', NULL);
  END IF;
  RETURN 'OK: ' || p_email || ' agora tem assinatura vitalícia';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.revogar_vitalicia(p_email TEXT)
RETURNS TEXT AS $$
DECLARE v_id UUID;
BEGIN
  IF NOT public.eh_master() THEN
    RAISE EXCEPTION 'Apenas master pode revogar';
  END IF;
  SELECT id INTO v_id FROM public.usuarios WHERE email = p_email;
  IF v_id IS NULL THEN RETURN 'Usuário não encontrado'; END IF;
  UPDATE public.assinaturas
     SET status='canceled', atualizado_em=NOW()
   WHERE usuario_id = v_id;
  RETURN 'OK: assinatura de ' || p_email || ' cancelada';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.promover_master(p_email TEXT)
RETURNS TEXT AS $$
BEGIN
  IF NOT public.eh_master() THEN
    RAISE EXCEPTION 'Apenas master pode promover outro master';
  END IF;
  UPDATE public.usuarios SET papel='master' WHERE email = p_email;
  IF NOT FOUND THEN RETURN 'Usuário não encontrado'; END IF;
  RETURN 'OK: ' || p_email || ' agora é master';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.rebaixar_master(p_email TEXT)
RETURNS TEXT AS $$
BEGIN
  IF NOT public.eh_master() THEN
    RAISE EXCEPTION 'Apenas master pode rebaixar outro master';
  END IF;
  UPDATE public.usuarios SET papel='comum' WHERE email = p_email;
  IF NOT FOUND THEN RETURN 'Usuário não encontrado'; END IF;
  RETURN 'OK: ' || p_email || ' agora é comum';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- 7. SEED — permissões iniciais
-- ============================================================

INSERT INTO "permissoes_por_papel" ("papel","modulo","ver","editar") VALUES
  -- master: acesso total a todos os módulos e catálogos
  ('master','catalogo_base',      TRUE, TRUE),
  ('master','cat_forcadores',     TRUE, TRUE),
  ('master','cat_uc',             TRUE, TRUE),
  ('master','cat_condensadores',  TRUE, TRUE),
  ('master','cadastro_comercial', TRUE, TRUE),
  ('master','configuracoes',      TRUE, TRUE),
  ('master','camara_completo',    TRUE, TRUE),
  ('master','camara_simples',     TRUE, TRUE),
  ('master','expositor',          TRUE, TRUE),
  ('master','compilacao_linhas',  TRUE, TRUE),
  ('master','rack',               TRUE, TRUE),
  ('master','paineis_portas',     TRUE, TRUE),
  ('master','compilacao_geral',   TRUE, TRUE),
  ('master','consumo',            TRUE, TRUE),
  ('master','materiais',          TRUE, TRUE),
  ('master','luminotecnico',      TRUE, TRUE),
  ('master','comparativo',        TRUE, TRUE),
  ('master','proposta',           TRUE, TRUE),
  -- comum: consome catálogo (RLS) + usa todos os módulos de projeto (que rodam local no cliente)
  ('comum','catalogo_base',      TRUE, FALSE),
  ('comum','camara_completo',    TRUE, TRUE),
  ('comum','camara_simples',     TRUE, TRUE),
  ('comum','expositor',          TRUE, TRUE),
  ('comum','compilacao_linhas',  TRUE, TRUE),
  ('comum','rack',               TRUE, TRUE),
  ('comum','paineis_portas',     TRUE, TRUE),
  ('comum','compilacao_geral',   TRUE, TRUE),
  ('comum','consumo',            TRUE, TRUE),
  ('comum','materiais',          TRUE, TRUE),
  ('comum','luminotecnico',      TRUE, TRUE),
  ('comum','comparativo',        TRUE, TRUE),
  ('comum','proposta',           TRUE, TRUE)
ON CONFLICT ("papel","modulo") DO UPDATE
   SET "ver" = EXCLUDED."ver", "editar" = EXCLUDED."editar";

-- ============================================================
-- FIM
-- ============================================================
