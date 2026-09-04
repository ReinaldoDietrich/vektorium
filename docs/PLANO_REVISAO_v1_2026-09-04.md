Plano Consolidado de Revisão — App Carga Térmica
Inventário completo dos achados
Nada abaixo foi descartado. A coluna "Fase" mostra onde cada item entra.

A. Performance — a lentidão ao trocar de projeto
#	Achado	Evidência	Fase
A1	10 telas recarregam simultaneamente no evento projeto-changed, inclusive invisíveis	main.js:100	2
A2	Tela 1 encadeia +4 recargas após o evento; sistemas carregados 2×	tela1.js:513, tela1.js:333	2
A3	Recálculo integral em toda leitura; mesmas câmaras recalculadas 3–4× em paralelo	camaras_completo.py:42, compilacao.py:562	2
A4	db.commit() dentro de GET — N commits por requisição	calc_service.py:1044	2
A5	journal_mode=delete (não WAL), synchronous default	verificado no banco	2
A6	httpx.post sem Client reutilizável; 1 handshake TLS por câmara; timeout 20 s	calc_remoto_client.py:24	2
A7	Zero eager loading em todo o backend (selectinload/joinedload = 0 ocorrências)	busca global	2
A8	Zero índices explícitos em 80 chaves estrangeiras	sqlite_master	2
A9	PRAGMA foreign_keys = 0 — integridade referencial desligada	verificado	2
A10	Sem AbortController — trocas rápidas empilham requisições	api.js	2
A11	Cache de catálogo por tela, duplicado; Tela 4 sem cache nenhum	tela4.js:22	2
A12	setTimeout(1500) escondendo boot lento	index.html:10	2
A13	Lock de escritor único do SQLite serializa as 4 requisições paralelas	consequência de A4	2
B. Empacotamento e proteção do ativo
#	Achado	Evidência	Fase
B1	Banco semente = banco de desenvolvimento: 7 projetos, 23 sistemas, 66 câmaras reais entregues a cada cliente	resources\database\carga_termica.db	1
B2	filter: ["**/*"] empacota 57 arquivos / 97,9 MB — 90 MB de backups por instalador	package.json:58	1
B3	Catálogo proprietário completo no instalador (209 produtos, 249 campos, 74 válvulas, 193 estações)	verificado	3
B4	Motor de cálculo em .py legível: calc_service, composicao_preco, calculos/	resources\backend	5
B5	allow_origins=["*"] no app remoto	main_calc.py:22	3
B6	Routers de projeto publicados no remoto "por simplicidade"	main_calc.py:6	3
C. Licenciamento — a regra que ficou pela metade
#	Achado	Evidência	Fase
C1	Nenhuma verificação de assinatura existe em todo o sistema	busca global	3
C2	exigir_usuario valida só a assinatura criptográfica do JWT, não o plano	auth_supabase.py:25	3
C3	POST /api/projetos sem gate — criar projeto novo é livre	projetos.py:51	3
C4	Escrita bloqueada só por "Projeto Fechado" (ação manual), sem relação com pagamento	backend/routers/_bloqueio_projeto.py	3
C5	calc is None cai no cálculo local ao vivo, não no snapshot — recálculo irrestrito	calc_service.py:1040	3
C6	None é ambíguo: sem token / sem rede / servidor fora → tratados igual	calc_remoto_client.py:29	3
C7	Front não consome _snapshot_desatualizado (0 ocorrências) — usuário não é avisado	busca global	3
C8	perfil.is_master() sempre True	perfil.py:17	3
C9	Soft-lock contornável não fazendo login: _base() retorna '' antes de checar _LEITURA_SEM_FALLBACK	api.js:59	3
D. Fundações de engenharia
#	Achado	Evidência	Fase
D1	Código-fonte não versionado — GitHub existe e funciona, mas só para Releases	1 commit, 1 arquivo	0
D2	.env com credenciais Supabase, sem .gitignore	.env	0
D3	86 scripts migrar_*.py ad-hoc, sem Alembic, sem registro de estado	backend/scripts/	0
D4	Zero testes em 24.043 linhas de Python	busca global	0
D5	except Exception: silencioso mascara erro de cálculo como "snapshot"	calc_service.py:1046	0
D6	3,7 GB de repositório; 48 .db de backup (98,5 MB)	medido	4
E. Estrutura e modernização
#	Achado	Evidência	Fase
E1	models.py: 85 classes, 1.562 linhas — Large Class + Divergent Change	models.py	4
E2	27 scripts globais, sem módulos; acoplamento por variáveis globais	index.html:1589	4
E3	Cache-busting manual ?v=... em 29 linhas + no-store redundante	main.py:22	4
E4	onProjetoChanged estruturalmente idêntico em 10 arquivos — Shotgun Surgery	telas 2,3,4,5,10,11,12	4
E5	api.js: fallback remoto→local repetido 5× (~100 linhas)	api.js:97	4
E6	Pydantic 2 instalado mas não usado — payload: dict = Body(...) cru em ~160 endpoints	routers	5
E7	SQLAlchemy 2.0 usado com API estilo 1.x (db.query)	backend	5
E8	Endpoints todos def, com I/O de rede bloqueante ocupando threads	calc_remoto_client.py	5
E9	tkinter.Tk() instanciado dentro de endpoint HTTP	projetos.py:31	5
As fases
FASE 0 — Rede de segurança
Sem isto, todas as fases seguintes são apostas.

Ação	Itens	Esforço
0.1	.gitignore antes do primeiro git add (venv, python-embed, node_modules, *.db, .env, MSIs, Instalação EXE/)	D2	30 min
0.2	Commit do código-fonte no repositório que já existe; daí em diante, um commit por alteração	D1	1 h
0.3	Testes de caracterização: congelar a saída de calcular_camara_completo para as 66 câmaras como golden files	D4	4–8 h
0.4	Alembic com baseline no schema atual	D3	3–4 h
0.5	Trocar except Exception: silencioso por log + distinção de causa nos 3 pontos críticos	D5	2 h
Fundamento: Feathers (Working Effectively with Legacy Code, cap. 1) — código sem teste não é refatorável, é reescrevível no escuro. Humble & Farley (Continuous Delivery, cap. 2) — versionar tudo é pré-requisito das demais práticas. Os golden files de 0.3 são o que permite validar as Fases 2 e 4 sem entender toda a física antes.

FASE 1 — Contenção do vazamento
Antes do próximo release. Independente de tudo o mais.

Ação	Itens	Esforço
1.1	Banco semente vazio: schema + catálogo, zero projetos. Script de geração no build, nunca a cópia do banco de trabalho	B1	2–3 h
1.2	filter: ["carga_termica.db"] no extraResources de database	B2	1 linha
1.3	Republicar; considerar despublicar 1.1.0–1.4.0 das Releases	B1	—
Efeito: instalador de 176 MB → ~90 MB, e fim da distribuição dos seus projetos e dos seus clientes. Este é o item de maior consequência e menor esforço de todo o plano.

FASE 2 — Performance
Alvo: troca de projeto de segundos para sub-segundo.

2A — Banco (baixo risco, alto retorno)

Ação	Itens
2.1	PRAGMA journal_mode=WAL + synchronous=NORMAL + busy_timeout no create_engine	A5, A13
2.2	Remover db.commit() de calcular_*_seguro; gravar snapshot só em escrita real	A4
2.3	index=True nas 80 FKs, via migração Alembic	A8
2.4	PRAGMA foreign_keys=ON — depois de auditar e limpar órfãos	A9
2B — Consultas

Ação	Itens
2.5	selectinload na listagem e na compilação (câmaras → sistema, portas, equipamentos, forçadores → linha/modelos/válvulas)	A7
2.6	Içar as varreduras de tabela (TabelaValvulaExpansao, FatorInsolacao) para fora do laço — carregar 1× por requisição	A3, A7
2C — Rede

Ação	Itens
2.7	httpx.Client reutilizável no módulo (conexão persistente, TLS reaproveitado)	A6
2.8	Endpoint remoto de cálculo em lote: 1 chamada por projeto, não por câmara	A6
2.9	Timeouts realistas (3 s connect / 8 s read) em vez de 20 s	A6
2D — Frontend

Ação	Itens
2.10	Carregamento preguiçoso: só a tela visível recarrega; as demais marcam-se "sujas" e recarregam ao serem exibidas	A1
2.11	AbortController cancelando a troca anterior	A10
2.12	Cache de catálogo único e global, com invalidação explícita	A11
2.13	Limpar o encadeamento redundante da Tela 1	A2
2.14	Remover o setTimeout(1500)	A12
Fundamento: Fowler (PoEAA) — o par Lazy Load / N+1 e sua correção por eager loading no ponto de agregação. Meyer (CQS) — consulta não altera estado, que é exatamente o que 2.2 restaura. Nielsen (Usability Engineering, cap. 5) — 1 s é o limite para manter o fluxo de pensamento; hoje o fan-out sozinho já o consome.

Ordem sugerida: 2.1 → 2.2 → 2.3 primeiro, isoladamente, e medir. São pequenos e podem resolver a maior parte sozinhos; medir antes de seguir evita otimizar o que já está resolvido.

FASE 3 — Licenciamento e proteção
Implementa a regra que você definiu: assinatura vencida = ver, não alterar.

3A — Fonte de verdade

Ação	Itens
3.1	Tabela assinaturas no Supabase (ou custom claim no JWT) com status e validade	C1
3.2	exigir_usuario passa a verificar plano ativo, não só validade do token	C2
3.3	GET /api/licenca no remoto → {ativa, expira_em, motivo}	C1
3B — Desambiguação (o item central)

Ação	Itens
3.4	calc_remoto_client deixa de devolver None para tudo: distinguir SEM_REDE, SEM_LICENCA, ERRO_SERVIDOR	C6
3.5	calcular_*_seguro: SEM_REDE → snapshot; SEM_LICENCA → snapshot e bloqueio; nunca cálculo local ao vivo	C5
3C — Aplicação

Ação	Itens
3.6	state.licencaAtiva no front, verificado no boot e periodicamente, com carência offline (7 dias)	C1
3.7	Reusar aplicarModoProjetoFechado() com segundo gatilho: licença vencida congela tudo	C4
3.8	Middleware de licença no main.py cobrindo criação e escrita	C3
3.9	Mover a checagem de _LEITURA_SEM_FALLBACK para antes do return '' em _base()	C9
3.10	Front exibe _snapshot_desatualizado como aviso visível nas telas 2, 3, 5, 12	C7
3.11	perfil.is_master() ligado ao perfil real do usuário autenticado	C8
3D — Higiene do remoto

Ação	Itens
3.12	allow_origins restrito à origem do app	B5
3.13	Routers de projeto fora do main_calc	B6
3.14	Catálogo sai da semente local; baixado no 1º login, cache com validade	B3
FASE 4 — Estrutura
Ação	Itens	Esforço
4.1	models.py → pacote models/ por contexto, preservando nomes exportados	E1	médio
4.2	Frontend → ES modules nativos, um arquivo por vez, sem bundler; import() dinâmico reforça 2.10	E2	médio
4.3	Módulo projetoContext.js com registro de telas — elimina os 10 onProjetoChanged	E4	médio
4.4	api.js → uma função de transporte parametrizada	E5	pequeno
4.5	Remover ?v=... (redundante com no-store)	E3	pequeno
4.6	Limpeza dos 98,5 MB de backups e das pastas _* — seguro apenas após a Fase 0	D6	pequeno
Fundamento: Fowler (Refactoring 2ª ed., cap. 3) para Large Class, Divergent Change, Shotgun Surgery. Yourdon & Constantine (Structured Design) — o acoplamento por dados globais de E2 é o grau mais nocivo depois do acoplamento por conteúdo.

FASE 5 — Modernização
Ação	Itens
5.1	Pydantic models nos endpoints de escrita, começando pelos críticos; response models	E6
5.2	Migrar db.query() → select() estilo 2.0, junto com 2.5	E7
5.3	async def + httpx.AsyncClient nos endpoints com I/O de rede	E8
5.4	escolher_pasta via dialog.showOpenDialog do Electron, saindo do Tkinter	E9
5.5	Motor de cálculo fora do instalador — depende da decisão estratégica abaixo	B4
A decisão estratégica pendente
O item 5.5 não é técnico. O código hoje tenta dois modelos ao mesmo tempo:

Calcula offline	Motor no cliente	Proteção possível
Modelo A — app instalado autônomo	sim	obrigatório	licença (Fase 3) trava o usuário comum; código legível para quem insistir
Modelo B — app cliente-servidor	não	desnecessário	real — o ativo nunca sai
Hoje o sistema carrega o peso dos dois e a proteção de nenhum: o motor está na máquina do cliente (custo do Modelo A) e a arquitetura remota está construída (custo do Modelo B), mas o fallback local anula o benefício do B.

A Fase 3 resolve ~99% do risco real — o usuário que deixou de pagar. Só o Modelo B resolve o usuário determinado. Essa escolha é sua, e ela define se 5.5 existe.

Sequenciamento e dependências
Regras de ordem:

1.1 e 1.2 antes de qualquer novo release — o custo de adiar cresce a cada versão publicada
0.1 antes de 0.2 — por causa do .env; commitado, exige reescrita de histórico
0.3 antes de 2.5 e 4.1 — refatorar cálculo sem golden files é aposta
0.4 antes de 2.3 e 2.4 — índices e FK entram como migração versionada
2.4 depois de auditar órfãos — ligar FK com dados inconsistentes quebra o app
3.4 antes de 3.5 a 3.10 — sem desambiguar None, a regra não tem como existir