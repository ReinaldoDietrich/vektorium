# Fase 1 — Migração para o Supabase (Vektorium)

**Gerado em:** 2026-08-20
**Projeto Supabase:** `vektorium` (organização Vektorium Sistemas)
**URL:** https://luzvgsgxutggnbyrhswg.supabase.co

---

## O que este pacote contém

| Arquivo | O quê |
|---|---|
| `INVENTARIO.md` | Auditoria: quais tabelas viram catálogo online (Supabase) e quais permanecem locais (projeto do cliente) |
| `1_schema_postgres.sql` | Criação das **60 tabelas** de catálogo no Postgres |
| `2_dados_XX_*.sql` | **74 arquivos** de INSERT com os **26.261 registros** atuais (um por tabela; tabelas grandes em blocos ≤ 1000 linhas) |
| `3_rls_policies.sql` | Row Level Security habilitado em todas as tabelas + policy inicial de leitura para autenticados |
| `gerar_migracao_supabase.py` | Script que gerou este pacote (regerar quando o catálogo mudar) |

**Todos os arquivos são texto puro (SQL/MD).** Nenhum toca no seu SQLite local — foram gerados **em modo leitura**.

---

## Passo a passo — o que você precisa fazer

### Passo 1 — Abrir o SQL Editor do Supabase
1. Acesse https://supabase.com → entre → selecione o projeto `vektorium`.
2. No menu lateral, clique em **SQL Editor** (ícone `<>`).
3. Clique em **"+ New query"**.

### Passo 2 — Criar as tabelas
1. Abra o arquivo **`1_schema_postgres.sql`** no bloco de notas / VS Code.
2. Copie **tudo** (Ctrl+A, Ctrl+C).
3. Cole no SQL Editor do Supabase.
4. Clique em **Run** (canto inferior direito).
5. Deve aparecer "Success. No rows returned".

### Passo 3 — Importar os dados
Faça o mesmo para **cada arquivo `2_dados_*.sql`**, em ordem numérica (2_dados_01, 02, 03, …):
1. Abra o arquivo.
2. Copie tudo.
3. Cole no SQL Editor.
4. Run.

**Ordem importa** por causa das foreign keys — siga a numeração.

**Tabelas grandes** (com `_p1`, `_p2`, ...): execute em ordem também. Ex.: `2_dados_27_p1_polinomio_compressor.sql` antes de `2_dados_27_p2_polinomio_compressor.sql`.

### Passo 4 — Ativar segurança (RLS)
1. Abra **`3_rls_policies.sql`**.
2. Cole no SQL Editor.
3. Run.

Isso liga o RLS em todas as tabelas e cria uma policy inicial: **apenas usuários autenticados podem LER** (na Fase 2 refinamos por papel/assinatura).

### Passo 5 — Validar
No SQL Editor, rode:
```sql
SELECT table_name, (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name = t.table_name) AS existe
FROM (VALUES ('cat_produtos'),('forcador_modelos'),('uc_unidades'),('paineis_termicos')) AS t(table_name);
```
Todas devem retornar `1`.

E:
```sql
SELECT 'forcador_modelos' AS tabela, COUNT(*) FROM forcador_modelos
UNION ALL SELECT 'uc_unidades', COUNT(*) FROM uc_unidades
UNION ALL SELECT 'polinomio_compressor', COUNT(*) FROM polinomio_compressor;
```
Compare com os números do relatório abaixo.

---

## Números da migração (para conferência)

- **60 tabelas** de catálogo criadas no Postgres
- **26.261 registros** exportados do SQLite atual
- **74 arquivos** de INSERT gerados (todos < 600 KB, cabem no SQL Editor)

---

## O que NÃO foi migrado (por decisão)

Os dados de **projeto** ficam no SQLite local de cada cliente (soft-lock — ver ADR seção 3.2). Não vão para o Supabase:

- Projetos, sistemas de refrigeração, câmaras (completo/simples), forçadores selecionados, UCs selecionadas, expositores, rack, centro de custo, composição de preço, comissão vendedor, condição de pagamento, vendedores, logs de importação.

Lista completa em **INVENTARIO.md**.

---

## Próximos passos (após você concluir a Fase 1)

- **Fase 2:** Auth + RLS refinado — login, papéis (Master/comum), matriz `tela × {ver, editar}`.
- **Fase 3:** Realojar FastAPI no Fly.io, apontar para Postgres do Supabase.

**Me avise quando tiver executado tudo** — vou validar as contagens e liberamos a Fase 2.
