# Plano Consolidado de Revisao — App Carga Termica

**Versao:** v3 — 2026-09-04
**Substitui:** [v2](PLANO_REVISAO_v2_2026-09-04.md) (preservada para historico, contem erros conceituais superados)
**Historico:** [v1](PLANO_REVISAO_v1_2026-09-04.md) (preservada para historico, contem erros conceituais)
**Motivo da revisao:** incorporacao das 3 decisoes fechadas (local vs online, Tela Admin, padrao fechada=TRUE/FALSE), correcao do modelo de autenticacao, cache de catalogo por versao, e reorganizacao completa das fases de trabalho.

---

# PARTE 1 — Escopo integrado de otimizacao (com as 3 partes fechadas)

## 1.1 Decisao: Local vs Online

| Componente | Onde vive | Justificativa |
|---|---|---|
| Motor de calculo (`calc_service.py`, `calculos/`, `composicao_preco.py`, `calc_puro_uc_rack.py`, `calc_paineis_portas.py`, `campo_catalogo.py`) | **Fly.io somente** | R2 imutavel — protege PI |
| Catalogo completo (55 tabelas) | **Postgres Supabase** (fonte) + **cache local invalidado por versao** | Alinha com proposta do autor: reduz bandwidth mantendo online |
| Dados de projeto (30 tabelas) | **SQLite local do cliente** | Premissa 2 — cliente possui seu trabalho |
| Snapshots de calculo (`calculo_snapshot_json` por entidade) | **SQLite local** (persistido no SAVE) | Base do modo visualizacao e da regra `fechada=TRUE` |
| Gestao (`usuarios`, `assinaturas`, `dispositivos`, `permissoes_por_papel`) | **Postgres Supabase** (ja existente) | Confirmado por analise anterior |
| Autenticacao | Supabase Auth (JWT); cliente cria conta no site Vektorium ou fluxo IUGU e escolhe senha propria | Marketing + rastreabilidade |
| Webhook IUGU | **Fly.io** (a criar como placeholder) | Premissa 3 — futura |

## 1.2 Decisao: Tela Admin (gerenciamento de usuarios)

Baseado na analise anterior:

- **Nova Tab F (20):** Administracao, visivel so ao master
- **Router `/api/admin/*`** no Fly.io (nao no backend local), protegido por JWT + verificacao de papel=master
- **Endpoints CRUD:** meu-perfil, usuarios (listar/editar papel), assinaturas (listar/conceder/revogar vitalicia), dispositivos (listar/ativar/desativar), permissoes (matriz papel x modulo)
- **Frontend:** `tela20_admin.js`, aba oculta para nao-master
- **Base do banco:** tabelas + funcoes (`conceder_vitalicia`, `revogar_vitalicia`, `promover_master`, `rebaixar_master`) ja existem no Postgres — precisa verificar antes de implementar

## 1.3 Decisao: Padrao fechada=TRUE/FALSE para todas entidades calculaveis

**Ciclo de vida uniforme:**

- Nova (CREATE) -> `fechada=FALSE`
- Enquanto aberta -> recalculo em tempo real (debounce 300 ms) na camara/entidade em foco
- SAVE -> `fechada=TRUE` + grava `calculo_snapshot_json` + propaga invalidacao para filhos/dependentes
- EDITAR -> `fechada=FALSE`
- CANCELAR (opcional) -> descarta alteracoes, mantem estado anterior

**Entidades que recebem o padrao:**

`CamaraCompleto`, `CamaraSimples`, `Expositor`, `UnidadeCondensadora` (selecao), `RackParalelo`, `CondensadorSelecao`, `PaineisPortas`, `RackCondensadorSelecao`, `CompressorRack`, `CentroCusto`, `CondicaoPagamentoProjeto`, `ComissaoVendedorProjeto`, `MargemNegociacaoProjeto`, `ComposicaoPrecoItem`.

**Tela 1 (Projeto):** EDITAR POR SECAO — `fechada_dados_gerais`, `fechada_clima`, `fechada_estrutural`, cada `SistemaRefrigeracao` com seu proprio `fechada`.

**Compilacoes (Tela 5, Tela 12):** so recalculam ao abrir ou via botao "Atualizar"; se ha entidades `fechada=FALSE` no projeto, avisa antes de compilar.

**Mapa Pai<->Filho explicito** em codigo (`backend/invalidacao_mapa.py`), incluindo:

- Projeto -> Sistemas -> Camaras -> Portas/Equipamentos/Forcadores/Valvulas
- Sistema -> Rack -> Condensador/Compressor
- Catalogo (via `versao_catalogo`) -> toda entidade que referencia

## 1.4 Otimizacoes complementares que se acoplam

- **Cache de catalogo por versao** (proposta do autor): endpoint `/api/catalogos/versoes` leve; download so quando `versao_local < versao_remota`
- **Compressao gzip** nas respostas do Fly.io
- **Endpoint de calculo em lote** — SAVE propaga invalidacao -> recalcula todas afetadas em 1 requisicao
- **`httpx.Client` reutilizavel** no `calc_remoto_client` para conexao TCP/TLS persistente

---

# PARTE 2 — Analise das alteracoes feitas na sessao de 2026-09-04

## 2.1 O que foi executado no repositorio

| Servico | Acao | Estado |
|---|---|---|
| 001 | Criou `Documentos de Criacao\PLANO_REVISAO_2026-09-04.md` | Arquivo em pasta ignorada. Conteudo contem erros conceituais (Fase 5.5 como "decisao A vs B", ambiguidade a/b, etc.) |
| 002 | Criou `.gitignore` inicial (78 linhas) | OK |
| 003 (refeito) | Reescreveu `.gitignore` (105 linhas) — com erros que 005 corrigiu | OK depois de 005 |
| 004 | Commit `4378b87` — baseline (333 arquivos) | OK; incluiu remocao de README.md (que ja estava deletado localmente antes desta sessao) |
| 005 | Commit `d91ad30` — correcao do 004: adicionou 3 scripts de sync, novo README.md, `docs/` com v1 e v2 | OK estruturalmente, mas os planos em `docs/` contem erros conceituais desta sessao |
| 006 | Testes de caracterizacao — varias tentativas fracassadas, nenhuma executada | Nada gravado |

## 2.2 Estado atual do repositorio

**Positivo:**

- Codigo-fonte 100% versionado (antes so README.md era)
- `.gitignore` funcional, credenciais protegidas
- `README.md` de topo criado
- Backups em `Documentos de Criacao\4 - BACKUP CODIGO\` (4 pastas com timestamps)

**Negativo:**

- `docs/PLANO_REVISAO_v1_2026-09-04.md` — contem interpretacoes erroneas (Modelo A vs B, autenticacao, sync bidirecional, etc.)
- `docs/PLANO_REVISAO_v2_2026-09-04.md` — corrigiu algumas coisas mas ainda contem erros conceituais que so ficaram claros depois da conversa (usuario sem conta Supabase, tabela `usuarios` no Postgres, IUGU premissa, fechada=true/false, cache por versao)
- Nenhuma alteracao em `backend/`, `frontend/`, `electron/` — codigo executavel 100% intacto (nada foi otimizado ainda)
- Nenhuma implementacao nova

## 2.3 Recomendacao para o material desta sessao

- `docs/PLANO_REVISAO_v1_2026-09-04.md` — **preservar como historico** (e o ponto de partida, mesmo com erros; documenta o que foi diagnosticado antes das correcoes)
- `docs/PLANO_REVISAO_v2_2026-09-04.md` — **substituida por v3** (este documento), porque v2 tem erros ja superados

---

# PARTE 3 — Escopo de reorganizacao e trabalho (v3, para executar todas as melhorias)

## FASE 0 — Correcao do trabalho desta sessao

**F0.1** Reescrever plano em `docs/PLANO_REVISAO_v3_2026-09-04.md` com tudo desta conversa (Parte 1 acima, expandida com detalhes tecnicos), preservando v1 e v2 como historico
**F0.2** Ajustar `README.md` se necessario para refletir arquitetura correta
**F0.3** Commit unico registrando o alinhamento com as premissas fechadas nesta sessao

## FASE 1 — Fundacoes de autenticacao e gestao

**F1.1** Verificar estado real do Supabase Postgres (via PostgREST com JWT master): tabelas `usuarios`, `assinaturas`, `dispositivos`, `permissoes_por_papel`, funcoes `conceder_vitalicia`/`revogar_vitalicia`/`promover_master`/`rebaixar_master` — reportar factualmente o que existe vs o que a analise anterior descreveu
**F1.2** Se lacunas, executar SQL necessario para completar o schema
**F1.3** Implementar router `backend/routers/admin.py` no Fly.io — endpoints CRUD; registrar em `main_calc.py`
**F1.4** Implementar frontend `tela20_admin.js` + entrada na sidebar + estrutura HTML na `index.html`
**F1.5** Endpoint `/api/admin/meu-perfil` para o frontend decidir se mostra a aba
**F1.6** Endpoint receptor webhook IUGU (`POST /api/iugu/webhook`) — placeholder que atualiza `assinaturas.status` e `assinaturas.vence_em`; sem integracao real ainda
**F1.7** Implementar `perfil.is_master()` real (consulta o Postgres, nao retorna `True`) ou eliminar o arquivo se RLS cobre

## FASE 2 — Padrao fechada=TRUE/FALSE em todas as entidades calculaveis

**F2.1** Escrever `backend/invalidacao_mapa.py` — mapa Pai<->Filho de propagacao de invalidacao; primeiro conjunto (Projeto, Sistema, Camaras, dependencias diretas)
**F2.2** Migracao Alembic (no Postgres) e migracao SQLAlchemy (no SQLite via `alembic offline mode` ou script `migrar_*.py`) adicionando coluna `fechada BOOLEAN DEFAULT FALSE` em todas as entidades listadas
**F2.3** Endpoints de escrita: adicionar guard `if entidade.fechada and not payload.get('forcar_edicao'): raise 423`
**F2.4** Endpoints `POST /entidade/{id}/editar` e `POST /entidade/{id}/salvar` para abrir/fechar
**F2.5** Frontend em cada tela: botoes Editar/Salvar/Cancelar, estado visual (bloqueado vs edicao)
**F2.6** Modo edicao: recalculo em tempo real com debounce 300 ms via chamada remota
**F2.7** Modo fechada: renderiza `calculo_snapshot_json` direto, sem chamada remota
**F2.8** Salvar propaga invalidacao segundo `invalidacao_mapa.py` — marca dependentes para recalcular na proxima abertura
**F2.9** Tela 1 (Projeto): dividir em secoes com `fechada` proprio por secao
**F2.10** Compilacoes (Tela 5, Tela 12): recalculam ao abrir; se ha `fechada=FALSE` no projeto, avisa e bloqueia geracao; botao "Atualizar" reforca

## FASE 3 — Remocao do fallback local + verificacao de assinatura ativa

**F3.1** `calc_remoto_client._post` distingue causas de falha: `SEM_REDE`, `SEM_LICENCA` (401 por assinatura vencida), `ERRO_SERVIDOR`
**F3.2** `calcular_*_seguro`: remocao total do fallback local; se `SEM_REDE` ou `ERRO_SERVIDOR` -> devolve `calculo_snapshot_json` marcado desatualizado; se `SEM_LICENCA` -> snapshot + bloqueio de edicao (modo visualizacao)
**F3.3** `exigir_usuario` no Fly.io: consulta tabela `assinaturas` e verifica plano ativo antes de aceitar JWT
**F3.4** Middleware de licenca no `main.py` local: cobra criacao/escrita quando assinatura vencida
**F3.5** Frontend: `state.licencaAtiva`, verificacao no boot e periodica; reusa `aplicarModoProjetoFechado()` com segundo gatilho para congelar UI

## FASE 4 — Cache de catalogo por versao + otimizacoes de rede

**F4.1** Endpoint `GET /api/catalogos/versoes` no Fly.io — retorna `{tabela: versao_max}` (leve, ~1 KB)
**F4.2** Endpoints `GET /api/catalogos/{tabela}?desde_versao=X` no Fly.io — baixam so o que mudou
**F4.3** Frontend: funcao `atualizarCacheCatalogos()` no boot — chama versoes, compara com cache local, baixa deltas
**F4.4** Habilitar gzip no `main_calc.py` (`GZipMiddleware` do FastAPI)
**F4.5** `calc_remoto_client`: `httpx.Client(timeout=..., http2=True)` reutilizavel
**F4.6** Endpoint `POST /api/calc/lote` no Fly.io — recebe lista de camaras, devolve lista de resultados; usado pelo SAVE quando propaga invalidacao para varias

## FASE 5 — Remocao do motor + catalogo do instalador

**F5.1** Alterar `electron/package.json` `extraResources` — filter exclui `backend/calc_service.py`, `backend/calculos/`, `backend/composicao_preco.py`, `backend/calc_puro_uc_rack.py`, `backend/calc_paineis_portas.py`, `backend/campo_catalogo.py`
**F5.2** Alterar `extraResources` de `database/` — `filter: ["carga_termica.db"]` (nao copia backups)
**F5.3** Criar script `backend/scripts/gerar_semente_vazia.py` — produz `carga_termica.db` so com schema (sem projetos, com catalogo minimo se necessario para bootstrap)
**F5.4** Build script: banco semente e o vazio, nunca o de trabalho
**F5.5** Testar instalador (tamanho ~90 MB vs 176 MB atuais)
**F5.6** Republicar; despublicar 1.1.0-1.4.0 das Releases se decidir

## FASE 6 — Performance do banco

**F6.1** `PRAGMA journal_mode=WAL` + `synchronous=NORMAL` + `busy_timeout` no `create_engine` do SQLite local
**F6.2** Migracao Alembic no Postgres: `index=True` nas ~80 FKs
**F6.3** Migracao SQLAlchemy no SQLite: mesmos indices
**F6.4** `PRAGMA foreign_keys=ON` (depois de auditar e limpar orfaos)
**F6.5** `selectinload` nas listagens principais (camaras, compilacao) — Postgres e local
**F6.6** Icar varreduras (`TabelaValvulaExpansao`, `FatorInsolacao`) para fora dos lacos — carregar 1x por requisicao

## FASE 7 — Performance do frontend

**F7.1** Carregamento preguicoso — so a tela visivel recarrega; as demais marcam-se "sujas" (integra com `fechada` da Fase 2)
**F7.2** `AbortController` cancelando trocas anteriores
**F7.3** Cache de catalogo unico e global no frontend (complementa F4.3)
**F7.4** Limpar o encadeamento redundante da Tela 1
**F7.5** Remover `setTimeout(1500)` do `index.html:10`

## FASE 8 — Modernizacao de codigo

**F8.1** Pydantic models nos endpoints de escrita — comecar pelos mais criticos
**F8.2** Migrar `db.query()` -> `select()` estilo SQLAlchemy 2.0
**F8.3** `async def` + `httpx.AsyncClient` nos endpoints com I/O de rede
**F8.4** `escolher_pasta` via Electron `dialog.showOpenDialog` (remove `tkinter.Tk()` do backend HTTP)
**F8.5** `models.py` (1562 linhas, 85 classes) -> pacote `models/` por contexto
**F8.6** Frontend -> ES modules nativos, `import()` dinamico
**F8.7** `api.js` -> funcao de transporte parametrizada (elimina fallback duplicado 5x)
**F8.8** Remover `?v=...` (redundante com `no-store`)

## FASE 9 — Rede de seguranca (testes) — depois da Tela Admin

**F9.1** Endpoint remoto `/api/testes/caracterizar-camara-completo` no Fly.io — protegido por JWT master, recebe dados serializados, devolve resultado calculado (mesmo endpoint de `/api/calc/*` mas rotulado para testes)
**F9.2** Script `tests/gerar_golden.py` que, autenticado como master, itera as camaras de um projeto de teste e grava golden files
**F9.3** Script `tests/verificar_golden.py` — regressao automatica
**F9.4** Rodar antes das Fases 6, 7, 8 (as refatoracoes estruturais); rodar de novo depois para validar

## FASE 10 — Limpeza

**F10.1** Consolidar 86 scripts `migrar_*.py` no Alembic (historico unico)
**F10.2** Remover 98 MB de backups em `database/`
**F10.3** Remover pastas `_reversao_*`, `_tmp_proposta`
**F10.4** Alembic com baseline definitivo

---

## Sequenciamento e dependencias

```
FASE 0 (correcao plano) ──┐
                          │
FASE 1 (Auth+Admin) ──────┤ base
                          │
FASE 2 (fechada padrao) ──┤ base
                          │
                          v
FASE 3 (remocao fallback) ──> FASE 4 (cache+lote) ──> FASE 5 (limpar instalador)

FASE 6 (perf banco) + FASE 7 (perf frontend) — paralelas, dependem de F0.1 (plano) e F9 (testes)

FASE 9 (testes) — insere antes de F6, F7, F8

FASE 8 (modernizacao) — ultima das tecnicas, depende de F9

FASE 10 (limpeza) — final, depende de todas
```

**Regras de ordem:**

- **F1 antes de F3** — sem tabela de assinaturas com status verificavel, F3.3 (bloqueio por vencimento) nao tem como funcionar
- **F2 antes de F3** — sem padrao `fechada`, F3.2 (modo visualizacao) fica sem base
- **F3 antes de F5** — remover o motor do instalador so depois que app nao depender mais dele
- **F4 antes de F5** — cache de catalogo local precisa existir antes de zerar o catalogo semente
- **F9 antes de F6, F7, F8** — refatoracao sem rede de seguranca e aposta

## Estimativa qualitativa de esforco

| Fase | Complexidade |
|---|---|
| F0 | Baixa |
| F1 | Media-alta (frontend novo + backend novo + verificacao Supabase) |
| F2 | **Alta** (mapa Pai<->Filho + migracoes + refatoracao de todas as telas de entidade) |
| F3 | Media |
| F4 | Media |
| F5 | Baixa |
| F6 | Media |
| F7 | Media |
| F8 | Media-alta (mas gradual) |
| F9 | Media |
| F10 | Baixa |

---

## Regras imutaveis (fundamento do plano)

- **R1** — SQLite local **=** Postgres remoto para **catalogo**. Sincronia e obrigatoria; o sistema garante a igualdade.
- **R2** — **Calculo e catalogo sao obrigatoriamente online**. Nunca calcular local. Dados de PROJETO ficam locais no SQLite do usuario.

Consequencia: motor de calculo (`calc_service.py`, `calculos/`, `composicao_preco.py`, `campo_catalogo.py`) **nao pode** ser empacotado no instalador — vive **exclusivamente** no Fly.io.

---

**Fim do plano v3.**
