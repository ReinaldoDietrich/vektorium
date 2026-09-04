# Plano Consolidado de Revisão — App Carga Térmica

**Versão:** v2 — 2026-09-04
**Substitui:** [v1](PLANO_REVISAO_v1_2026-09-04.md) (preservada para histórico)
**Motivo da revisão:** incorporação das **regras imutáveis** confirmadas pelo autor após publicação da v1; auditoria dos serviços 001–004 executados sobre a v1.

---

## 0. Regras imutáveis (fundamento do plano)

- **R1** — SQLite local **≡** Postgres remoto para **catálogo**. Sincronia é obrigatória; o sistema garante a igualdade.
- **R2** — **Cálculo e catálogo são obrigatoriamente online**. Nunca calcular local. Dados de PROJETO ficam locais no SQLite do usuário.

Consequência: motor de cálculo (`calc_service.py`, `calculos/`, `composicao_preco.py`, `campo_catalogo.py`) **não pode** ser empacotado no instalador — vive **exclusivamente** no Fly.io.

---

## 1. Inventário completo dos achados

Preservado da v1 (nenhum achado descartado). Coluna "Fase" atualizada onde a revisão realocou o item.

### A. Performance — a lentidão ao trocar de projeto

| # | Achado | Evidência | Fase |
|---|---|---|---|
| A1 | 10 telas recarregam simultaneamente no evento `projeto-changed`, inclusive invisíveis | `main.js:100` | 2 |
| A2 | Tela 1 encadeia +4 recargas após o evento; sistemas carregados 2× | `tela1.js:513`, `tela1.js:333` | 2 |
| A3 | Recálculo integral em toda leitura; mesmas câmaras recalculadas 3–4× em paralelo | `camaras_completo.py:42`, `compilacao.py:562` | 2 |
| A4 | `db.commit()` dentro de GET — N commits por requisição | `calc_service.py:1044` | 2/3 |
| A5 | `journal_mode=delete` (não WAL), `synchronous` default | verificado no banco | 2 |
| A6 | `httpx.post` sem Client reutilizável; 1 handshake TLS por câmara; timeout 20 s | `calc_remoto_client.py:24` | 2 |
| A7 | Zero eager loading em todo o backend (`selectinload`/`joinedload` = 0 ocorrências) | busca global | 2 |
| A8 | Zero índices explícitos em 80 chaves estrangeiras | `sqlite_master` | 2 |
| A9 | `PRAGMA foreign_keys = 0` — integridade referencial desligada | verificado | 2 |
| A10 | Sem `AbortController` — trocas rápidas empilham requisições | `api.js` | 2 |
| A11 | Cache de catálogo por tela, duplicado; Tela 4 sem cache nenhum | `tela4.js:22` | 2 |
| A12 | `setTimeout(1500)` escondendo boot lento | `index.html:10` | 2 |
| A13 | Lock de escritor único do SQLite serializa as 4 requisições paralelas | consequência de A4 | 2 |

### B. Empacotamento e proteção do ativo

| # | Achado | Evidência | Fase |
|---|---|---|---|
| B1 | Banco semente = banco de desenvolvimento: 7 projetos, 23 sistemas, 66 câmaras reais entregues a cada cliente | `resources\database\carga_termica.db` | 1 |
| B2 | `filter: ["**/*"]` empacota 57 arquivos / 97,9 MB — 90 MB de backups por instalador | `package.json:58` | 1 |
| B3 | Catálogo proprietário completo no instalador (209 produtos, 249 campos, 74 válvulas, 193 estações) | verificado | 3 |
| B4 | Motor de cálculo em `.py` legível: `calc_service`, `composicao_preco`, `calculos/` | `resources\backend` | **3** (era 5) |
| B5 | `allow_origins=["*"]` no app remoto | `main_calc.py:22` | 3 |
| B6 | Routers de projeto publicados no remoto "por simplicidade" | `main_calc.py:6` | 3 |

### C. Licenciamento — a regra que ficou pela metade

| # | Achado | Evidência | Fase |
|---|---|---|---|
| C1 | Nenhuma verificação de assinatura existe em todo o sistema | busca global | 3 |
| C2 | `exigir_usuario` valida só a assinatura criptográfica do JWT, não o plano | `auth_supabase.py:25` | 3 |
| C3 | `POST /api/projetos` sem gate — criar projeto novo é livre | `projetos.py:51` | 3 |
| C4 | Escrita bloqueada só por "Projeto Fechado" (ação manual), sem relação com pagamento | `_bloqueio_projeto.py` | 3 |
| C5 | `calc is None` cai no cálculo local ao vivo, não no snapshot — recálculo irrestrito | `calc_service.py:1040` | 3 |
| C6 | `None` é ambíguo: sem token / sem rede / servidor fora → tratados igual | `calc_remoto_client.py:29` | 3 |
| C7 | Front não consome `_snapshot_desatualizado` (0 ocorrências) — usuário não é avisado | busca global | 3 |
| C8 | `perfil.is_master()` sempre `True` | `perfil.py:17` | 3 |
| C9 | Soft-lock contornável não fazendo login: `_base()` retorna `''` antes de checar `_LEITURA_SEM_FALLBACK` | `api.js:59` | 3 |

### D. Fundações de engenharia

| # | Achado | Evidência | Fase |
|---|---|---|---|
| D1 | Código-fonte não versionado — GitHub existe e funciona, mas só para Releases | 1 commit, 1 arquivo | 0 |
| D2 | `.env` com credenciais Supabase, sem `.gitignore` | `.env` | 0 |
| D3 | 86 scripts `migrar_*.py` ad-hoc, sem Alembic, sem registro de estado | `backend/scripts/` | 0 |
| D4 | Zero testes em 24.043 linhas de Python | busca global | 0 |
| D5 | `except Exception:` silencioso mascara erro de cálculo como "snapshot" | `calc_service.py:1046` | 0/3 |
| D6 | 3,7 GB de repositório; 48 `.db` de backup (98,5 MB) | medido | 4 |

### E. Estrutura e modernização

| # | Achado | Evidência | Fase |
|---|---|---|---|
| E1 | `models.py`: 85 classes, 1.562 linhas — Large Class + Divergent Change | `models.py` | 4 |
| E2 | 27 scripts globais, sem módulos; acoplamento por variáveis globais | `index.html:1589` | 4 |
| E3 | Cache-busting manual `?v=...` em 29 linhas + `no-store` redundante | `main.py:22` | 4 |
| E4 | `onProjetoChanged` estruturalmente idêntico em 10 arquivos — Shotgun Surgery | telas 2,3,4,5,10,11,12 | 4 |
| E5 | `api.js`: fallback remoto→local repetido 5× (~100 linhas) | `api.js:97` | 4 |
| E6 | Pydantic 2 instalado mas não usado — `payload: dict = Body(...)` cru em ~160 endpoints | routers | 5 |
| E7 | SQLAlchemy 2.0 usado com API estilo 1.x (`db.query`) | backend | 5 |
| E8 | Endpoints todos `def`, com I/O de rede bloqueante ocupando threads | `calc_remoto_client.py` | 5 |
| E9 | `tkinter.Tk()` instanciado dentro de endpoint HTTP | `projetos.py:31` | 5 |

---

## 2. As fases (revisadas à luz de R1/R2)

### FASE 0 — Rede de segurança

*Sem isto, todas as fases seguintes são apostas.*

| # | Ação | Itens |
|---|---|---|
| 0.1 | `.gitignore` antes do primeiro `git add` (venv, python-embed, node_modules, `*.db`, `.env`, MSIs, `Instalação EXE/`, particulares, mockups, previews, backups escapados) | D2 |
| 0.2 | Commit do código-fonte no repositório que já existe; daí em diante, um commit por alteração | D1 |
| 0.3 | **Testes de caracterização SÓ REMOTOS** — golden files JSON com a resposta do endpoint remoto `POST https://vektorium-calc.fly.dev/api/calc/*` (não usar `calcular_camara_completo` local) | D4 |
| 0.4 | **Alembic com baseline no Postgres remoto** (fonte de verdade); SQLite local herda por sincronia | D3 |
| 0.5 | Trocar `except Exception:` silencioso por log + distinção de causa nos 3 pontos críticos; **absorvido no item 3.5** (fallback local será removido, o `except` some junto) | D5 |

**Fundamento:** Feathers, *Working Effectively with Legacy Code*, cap. 1 (código sem teste não é refatorável); Humble & Farley, *Continuous Delivery*, cap. 2 (versionar tudo).

### FASE 1 — Contenção do vazamento

*Antes do próximo release. Independente de tudo o mais.*

| # | Ação | Itens |
|---|---|---|
| 1.1 | Banco semente **vazio** no instalador (schema + catálogo mínimo; catálogo será baixado do Postgres na primeira sincronia) | B1 |
| 1.2 | `filter: ["carga_termica.db"]` no `extraResources` de `database` | B2 |
| 1.3 | Republicar; considerar despublicar 1.1.0–1.4.0 das Releases | B1 |

### FASE 2 — Performance

*Alvo: troca de projeto de segundos para sub-segundo. Foco: código Python (roda no Fly.io) + SQLite local como cache/projeto.*

**2A — Postgres remoto (fonte de verdade)**

| # | Ação | Itens |
|---|---|---|
| 2.1a | `index=True` nas 80 FKs, via migração Alembic no Postgres | A8 |
| 2.2a | Tuning de pool e `synchronous_commit=off` para leituras em `main_calc.py` | A6 |

**2B — SQLite local (cache read-replica de catálogo + projeto local)**

| # | Ação | Itens |
|---|---|---|
| 2.3b | `PRAGMA journal_mode=WAL` + `synchronous=NORMAL` + `busy_timeout` no `create_engine` local | A5, A13 |
| 2.4b | `PRAGMA foreign_keys=ON` — depois de auditar e limpar órfãos (projeto local) | A9 |
| 2.5b | Remover `db.commit()` de `calcular_*_seguro` — desaparece junto com o fallback local (item 3.5) | A4 |

**2C — Código Python (roda no Fly.io)**

| # | Ação | Itens |
|---|---|---|
| 2.6 | `selectinload` na listagem e na compilação | A7 |
| 2.7 | Içar as varreduras de tabela (`TabelaValvulaExpansao`, `FatorInsolacao`) para fora do laço | A3, A7 |
| 2.8 | `httpx.Client` reutilizável (para o app local chamar o Fly.io eficientemente) | A6 |
| 2.9 | Endpoint remoto de cálculo **em lote** (1 chamada por projeto, não por câmara) | A6 |
| 2.10 | Timeouts realistas (3 s connect / 8 s read) em vez de 20 s | A6 |

**2D — Frontend**

| # | Ação | Itens |
|---|---|---|
| 2.11 | Carregamento preguiçoso: só a tela visível recarrega | A1 |
| 2.12 | `AbortController` cancelando a troca anterior | A10 |
| 2.13 | Cache de catálogo único e global, com invalidação explícita | A11 |
| 2.14 | Limpar o encadeamento redundante da Tela 1 | A2 |
| 2.15 | Remover o `setTimeout(1500)` | A12 |

**Fundamento:** Fowler (*PoEAA*) — Lazy Load / N+1; Meyer (*CQS*) — consulta não altera estado; Nielsen (*Usability Engineering*, cap. 5) — 1 s.

**Ordem sugerida:** 2.3b → 2.5b → 2.1a primeiro, isoladamente, e medir.

### FASE 3 — Licenciamento e proteção (núcleo do plano após v2)

*Implementa R2 explicitamente: assinatura vencida = ver dados já calculados, não alterar; sem licença ativa = zero cálculo local, zero fallback.*

**3A — Fonte de verdade**

| # | Ação | Itens |
|---|---|---|
| 3.1 | Tabela `assinaturas` no Supabase (ou custom claim no JWT) com status e validade | C1 |
| 3.2 | `exigir_usuario` passa a verificar plano ativo, não só validade do token | C2 |
| 3.3 | `GET /api/licenca` no remoto → `{ativa, expira_em, motivo}` | C1 |

**3B — Desambiguação e remoção do fallback local (crítico para R2)**

| # | Ação | Itens |
|---|---|---|
| 3.4 | `calc_remoto_client` distingue `SEM_REDE`, `SEM_LICENCA`, `ERRO_SERVIDOR` | C6 |
| 3.5 | `calcular_*_seguro`: **removido o fallback local**. Sem rede → snapshot; sem licença → snapshot + bloqueio; **NUNCA cálculo local ao vivo** | C5, A4, D5 |
| 3.6 | **Motor de cálculo fora do `extraResources`** do instalador (`calc_service.py`, `calculos/`, `composicao_preco.py`, `campo_catalogo.py`). Não é decisão — é regra R2 | B4 |

**3C — Aplicação**

| # | Ação | Itens |
|---|---|---|
| 3.7 | `state.licencaAtiva` no front, verificado no boot e periodicamente, com carência offline (7 dias) | C1 |
| 3.8 | Reusar `aplicarModoProjetoFechado()` com segundo gatilho: licença vencida congela tudo | C4 |
| 3.9 | Middleware de licença no `main.py` cobrindo criação e escrita | C3 |
| 3.10 | Mover a checagem de `_LEITURA_SEM_FALLBACK` para antes do `return ''` em `_base()` | C9 |
| 3.11 | Front exibe `_snapshot_desatualizado` como aviso visível nas telas 2, 3, 5, 12 | C7 |
| 3.12 | `perfil.is_master()` ligado ao perfil real do usuário autenticado | C8 |

**3D — Higiene do remoto**

| # | Ação | Itens |
|---|---|---|
| 3.13 | `allow_origins` restrito à origem do app | B5 |
| 3.14 | Routers de projeto fora do `main_calc` | B6 |
| 3.15 | Catálogo sai da semente local; baixado no 1º login, cache com validade | B3 |

### FASE 4 — Estrutura

| # | Ação | Itens |
|---|---|---|
| 4.1 | `models.py` → pacote `models/` por contexto, preservando nomes exportados | E1 |
| 4.2 | Frontend → ES modules nativos, um arquivo por vez, sem bundler; `import()` dinâmico reforça 2.11 | E2 |
| 4.3 | Módulo `projetoContext.js` com registro de telas — elimina os 10 `onProjetoChanged` | E4 |
| 4.4 | `api.js` → uma função de transporte parametrizada | E5 |
| 4.5 | Remover `?v=...` (redundante com `no-store`) | E3 |
| 4.6 | Limpeza dos 98,5 MB de backups e das pastas `_*` — seguro apenas após a Fase 0 | D6 |

**Fundamento:** Fowler (*Refactoring* 2ª ed., cap. 3); Yourdon & Constantine (*Structured Design*).

### FASE 5 — Modernização

*Item 5.5 da v1 removido — motor fora do instalador é regra R2 (item 3.6), não decisão.*

| # | Ação | Itens |
|---|---|---|
| 5.1 | Pydantic models nos endpoints de escrita, começando pelos críticos; response models | E6 |
| 5.2 | Migrar `db.query()` → `select()` estilo 2.0, junto com 2.6 | E7 |
| 5.3 | `async def` + `httpx.AsyncClient` nos endpoints com I/O de rede | E8 |
| 5.4 | `escolher_pasta` via `dialog.showOpenDialog` do Electron, saindo do Tkinter | E9 |

---

## 3. Sequenciamento e dependências

**Regras de ordem:**

- 1.1 e 1.2 antes de qualquer novo release — o custo de adiar cresce a cada versão publicada
- 0.1 antes de 0.2 — por causa do `.env`; commitado, exige reescrita de histórico
- 0.3 antes de 2.6 e 4.1 — refatorar cálculo sem golden files é aposta
- 0.4 antes de 2.1a e 2.4b — índices e FK entram como migração versionada
- 2.4b depois de auditar órfãos — ligar FK com dados inconsistentes quebra o app
- 3.4 antes de 3.5 a 3.11 — sem desambiguar `None`, R2 não tem como existir
- 3.6 depois de 3.5 — só remover o motor do instalador quando o app não depender dele para nada

---

## 4. Histórico de execução (serviços 001–005 desta sessão)

| Serviço | Data | Ação | Status |
|---|---|---|---|
| 001 | 2026-09-04 | Salvou plano v1 em `Documentos de Criação\PLANO_REVISAO_2026-09-04.md` | Executado — plano v1 preserved em `docs/PLANO_REVISAO_v1_2026-09-04.md` |
| 002 | 2026-09-04 | `.gitignore` inicial (78 linhas) | Executado — sem erros |
| 003 refeito | 2026-09-04 | `.gitignore` final (105 linhas) | Executado — corrigido no 005 |
| 004 | 2026-09-04 | Commit inicial `4378b87` (333 add + 1 delete) | Executado — corrigido no 005 |
| 005 | 2026-09-04 | Correção de erros dos 001-004 (auditoria PEI); adiciona 3 scripts de sync, README.md, docs/ com v1 e v2 | Em execução |

---

## 5. Auditoria dos serviços 001–004 (motivo desta v2)

Erros catalogados na revisão de 2026-09-04:

- **1.1 (ALTA)** — v1 salva em pasta ignorada (`Documentos de Criação/`), sem versionamento → corrigido em 005 movendo para `docs/`
- **1.2 (ALTA)** — Conteúdo v1 desatualizado (sem R1/R2) → corrigido em 005 gerando esta v2
- **1.3 (MÉDIA)** — Nome sem versão → corrigido em 005 renomeando como `v1` e `v2`
- **3.1 (CRÍTICA)** — 3 scripts de sync (`push_local_para_flyio.py`, `sync_flyio_para_local.py`, `converter_fotos_base64.py`) indevidamente ignorados → corrigido em 005
- **3.2/3.3 (MÉDIA — reavaliadas)** — `rodar_servidor_teste_alpha.py` e `Iniciar Carga Térmica.vbs` **permanecem ignorados** por decisão do autor
- **4.1 (CRÍTICA herdada)** — commit `4378b87` sem os 3 scripts → corrigido em 005 (commit corretivo aditivo)
- **4.2 (MÉDIA)** — README.md deletado sem substituto → corrigido em 005 criando novo

---

**Fim do plano v2.**
