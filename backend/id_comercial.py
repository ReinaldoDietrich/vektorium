# -*- coding: utf-8 -*-
"""Árvore de Ids comerciais — organiza onde fica o texto/foto de cada seleção do app pra montar
memorial/proposta depois. Ver "Documentos de Criação/Instruções de Id para Organização dos
textos comerciais.docx". Duas frentes:

1. Itens AVULSOS (sem catálogo próprio: Tipo de Comando, Válvula, Automações, Estrutura/Partida/
   Modo Operação do Rack, Painéis/Portas) — a árvore inteira (categorias + itens finais) fica
   seedada na tabela IdComercial (models.py), editável em Configurações. O texto/foto de cada item
   avulso é cadastrado à parte, em CatalogoComercial, com o campo id_comercial preenchido (pelo
   seletor em cascata da tela, não digitado à mão).

2. Itens COM catálogo (Forçador de Ar = 4.2, Unidade Condensadora = 4.1.1, Condensador Remoto =
   4.4.1.x) — o texto/foto já mora no próprio catálogo (LinhaForcador/CatalogoUC/
   LinhaCondensadorRemoto). O Id é AUTO-GERADO na criação da linha: casa o Fabricante com o nó-
   folha de marca já cadastrado na árvore (ex.: "Elgin" -> 4.2.1) e numera a Linha como o próximo
   sequencial ABAIXO desse nó (4.2.1.1, 4.2.1.2...). Fabricante fora da lista fixa da árvore cai
   num galho novo, numerado na ordem de cadastro (mesmo padrão de antes). Fixo — calculado uma vez
   na criação, nunca recalculado depois pra não mudar o Id de itens antigos.

Árvore v2 (2026-08-05) — reestruturação completa, substitui a v1 (que tinha "Elétrica" com só
Tipo de Comando, Válvula como categoria 3 solta, Automação de Linhas como categoria 4 solta,
Forçador/Condensador como folha única sem marca, Painéis como categoria 8). Migração:
backend/scripts/migrar_arvore_ids_v2.py — troca o conteúdo de id_comercial e realinha o
id_comercial de todo catálogo (Forçador/UC/Condensador) já cadastrado pra bater com os novos
códigos (backup do estado anterior salvo à parte, ver scripts/migrar_arvore_ids_v2.py).
"""
from sqlalchemy.orm import Session
from . import models as m

# (codigo, nome) — seed completo da árvore de itens AVULSOS + marcas fixas dos catálogos. Ditado
# literalmente pelo usuário (inclusive a numeração de "Unidade Comercial", que pula um nível —
# 4.1.1.1.1/.2/.3 direto, sem nó "4.1.1.1" — mantido de propósito).
ARVORE_ID_COMERCIAL = [
    ("1", "Elétrica"),
    ("1.1", "Tipo de Comando"),
    ("1.1.1", "Quadro de Linhas Distribuído (QD)"),
    ("1.1.2", "Quadro de Linhas Centralizado (QL)"),
    ("1.2", "Tipo Automação Linhas"),
    ("1.2.1", "Controle Simples"),
    ("1.2.1.1", "Danfoss"),
    ("1.2.1.2", "Fullgauge"),
    ("1.2.1.3", "Carel"),
    ("1.2.2", "Controle + Acesso Remoto"),
    ("1.2.2.1", "Danfoss"),
    ("1.2.2.2", "Fullgauge"),
    ("1.2.2.3", "Carel"),
    ("1.2.3", "Supervisão (IHM)"),
    ("1.2.3.1", "Danfoss"),
    ("1.2.3.2", "Fullgauge"),
    ("1.2.3.3", "Carel"),
    ("1.3", "Tipo Automação Equipamentos"),
    ("1.3.1", "Eletromecânico"),
    ("1.3.1.1", "Danfoss"),
    ("1.3.1.2", "Elgin"),
    ("1.3.1.3", "RAC"),
    ("1.3.2", "Gerenciamento Eletrônico"),
    ("1.3.2.1", "Danfoss"),
    ("1.3.2.2", "Fullgauge"),
    ("1.3.2.3", "Carel"),

    ("2", "Mecânica"),
    ("2.1", "Gás refrigerante"),
    ("2.1.1", "HCFC"),
    ("2.1.2", "HFC"),
    ("2.1.3", "Blends"),

    ("3", "Válvula de Expansão"),
    ("3.1", "Termostática"),
    ("3.1.1", "Danfoss"),
    ("3.1.2", "Elgin"),
    ("3.1.3", "Sanhua"),
    ("3.1.4", "Emerson"),
    ("3.1.5", "Parker"),
    ("3.2", "Eletrônica"),
    ("3.2.1", "Danfoss"),
    ("3.2.2", "FullGauge"),
    ("3.2.3", "Carel"),

    ("4", "Equipamentos"),
    ("4.1", "Tipo Equip. Compressão"),
    ("4.1.1", "Unidade Condensadora Comercial"),
    ("4.1.1.1.1", "Elgin"),
    ("4.1.1.1.2", "Danfoss"),
    ("4.1.1.1.3", "Bitzer"),
    ("4.1.2", "Rack Paralelo"),
    ("4.1.2.1", "Estrutura"),
    ("4.1.2.1.1", "Carenado"),
    ("4.1.2.1.2", "Sem Carenagem"),
    ("4.1.2.2", "Acessórios e Componentes"),
    ("4.1.2.2.1", "Compressor"),
    ("4.1.2.2.1.1", "Danfoss"),
    ("4.1.2.2.1.1.1", "Hermético"),
    ("4.1.2.2.1.1.2", "Scroll"),
    ("4.1.2.2.1.2", "Copeland"),
    ("4.1.2.2.1.2.1", "Scroll"),
    ("4.1.2.2.1.2.2", "Semi Hermético"),
    ("4.1.2.2.1.3", "Bitzer"),
    ("4.1.2.2.1.3.1", "Semi-Hermético"),
    ("4.1.2.2.1.3.2", "Duplo Estágio"),
    ("4.1.2.2.1.3.3", "Parafuso"),
    ("4.1.2.2.1.4", "Dorin"),
    ("4.1.2.2.1.4.1", "Semi Hermético"),
    ("4.1.2.2.1.4.2", "Duplo Estágio"),
    ("4.1.2.2.1.4.3", "Tandem"),
    ("4.1.2.2.1.5", "Bock"),
    ("4.1.2.2.1.5.1", "Semi Hermético"),
    ("4.1.3", "Tipo de Partida Compressores"),
    ("4.1.3.1", "Direta"),
    ("4.1.3.2", "Dividida"),
    ("4.1.3.3", "Soft starter"),
    ("4.1.3.3.1", "WEG"),
    ("4.1.3.3.2", "ABB"),
    ("4.1.3.3.3", "Siemens"),
    ("4.1.3.3.4", "Danfoss"),
    ("4.1.3.3.5", "Schneider"),
    ("4.1.4", "Modo de Operação"),
    ("4.1.4.1", "Controle de Capacidade"),
    ("4.1.4.2", "Inversor de Frequência"),
    ("4.1.4.2.1", "WEG"),
    ("4.1.4.2.2", "Danfoss"),
    ("4.1.4.2.3", "Siemens"),
    ("4.1.4.2.4", "ABB"),
    ("4.2", "Forçadores de Ar"),
    ("4.2.1", "Elgin"),
    ("4.2.2", "Mipal"),
    ("4.2.3", "Trineva"),
    ("4.2.4", "Refrio"),
    ("4.2.5", "Gunter"),
    ("4.2.6", "Delta Frio"),
    ("4.3", "Expositor"),
    ("4.3.1", "Eletrofrio"),
    ("4.3.2", "Arneg"),
    ("4.4", "Condensador Remoto a Ar"),
    ("4.4.1", "Tipo Condensador"),
    ("4.4.1.1", "Plano (Fluxo Vertical)"),
    ("4.4.1.1.1", "Elgin"),
    ("4.4.1.1.2", "Mipal"),
    ("4.4.1.1.3", "Trineva"),
    ("4.4.1.1.4", "Refrio"),
    ("4.4.1.1.5", "Gunter"),
    ("4.4.1.1.6", "Delta Frio"),
    ("4.4.1.2", "Plano Onboard"),
    ("4.4.1.2.1", "Brahex"),
    ("4.4.1.3", "V (Fluxo Horizontal)"),
    ("4.4.1.3.1", "Elgin"),
    ("4.4.1.3.2", "Mipal"),
    ("4.4.1.3.3", "Trineva"),
    ("4.4.1.3.4", "Refrio"),
    ("4.4.1.3.5", "Gunter"),
    ("4.4.1.3.6", "Delta Frio"),

    ("5", "Instalação"),
    ("5.1", "Fixação Forçadores de Ar"),
    ("5.1.1", "Teto Câmara"),
    ("5.1.2", "Estrutura da Cobertura"),
    ("5.1.3", "Estrutura Auxiliar"),
    ("5.2", "Tubulação de Cobre e Suportes"),
    ("5.3", "Cabeamento e Infraestrutura elétrica"),
    ("5.4", "Isolamento térmico tubulação"),
    ("5.4.1", "Espuma Elastomérica"),
    ("5.4.2", "Alumínio com poliuretano injetado"),
    ("5.5", "Rede de Drenagem"),
    ("5.5.1", "Com resistência"),
    ("5.5.2", "Sem resistência"),
    ("5.6", "Painéis Térmicos Câmaras"),
    ("5.6.1", "Parede e Teto"),
    ("5.6.2", "Isolamento de Piso"),
]

# Nós-âncora onde o Id de catálogo (Forçador/UC/Condensador) é auto-gerado — ver
# gerar_proximo_id_catalogo(). Cada marca já cadastrada como filho fixo da âncora reaproveita seu
# próprio código; marca fora da lista cai num galho novo numerado na ordem de cadastro.
ANCORA_FORCADOR = "4.2"
ANCORA_UC = "4.1.1"
_ANCORA_CONDENSADOR_POR_TIPO = {
    "Plano (Fluxo Vertical)": "4.4.1.1",
    "Plano Onboard": "4.4.1.2",
    "V (Fluxo Horizontal)": "4.4.1.3",
}


def ancora_condensador(tipo_estrutura: str) -> str:
    """Âncora de Condensador Remoto depende do Tipo Condensador (Plano/Plano Onboard/V) — tipo
    fora da lista (ex. "Onboard" genérico da Tela 6, que não é bem um tipo de condensador de
    catálogo) cai em "Plano (Fluxo Vertical)" como default razoável."""
    return _ANCORA_CONDENSADOR_POR_TIPO.get(tipo_estrutura, "4.4.1.1")


def chave_codigo(codigo: str) -> tuple:
    """Chave de ordenacao hierarquica pro codigo (ex.: '2.2.1' -> (2, 2, 1)) -- ordena pela
    posicao real na arvore, nao por 'ordem' solto nem por ordem alfabetica/de insercao (um item
    novo cadastrado com codigo '0.0' entrava sempre na frente de tudo, fora de ordem)."""
    return tuple(int(p) for p in codigo.split("."))


def listar_arvore(db: Session):
    itens = db.query(m.IdComercial).all()
    itens.sort(key=lambda i: chave_codigo(i.codigo))
    return itens


# ---------------- Busca cruzada (itens avulsos, ver resolver_ids_avulsos_sistema) ----------------
# Desde 2026-08-08 os campos avulsos do Sistema/Projeto gravam o CÓDIGO da árvore diretamente (não
# mais o nome) — decisão do usuário: "O QUE DEVE COMANDAR A BUSCA, CONTROLE E ORGANIZAÇÃO SÃO OS
# IDs QUE SÃO OS DADOS QUE JAMAIS SERÃO REPETIDOS". Nome de nó pode mudar/duplicar; código não.


def remover_no_catalogo(db, codigo: str | None):
    """Contraparte de gerar_proximo_id_catalogo — chamada ao EXCLUIR um catálogo com Id (Linha
    Forçador/Condensador Remoto, CatalogoUC), pra não deixar nó órfão na árvore (código sem
    catálogo por trás). Só remove se o nó for FOLHA (sem filhos) — nunca arrasta subárvore, nunca
    apaga nó com filhos por engano. Sem-op se o código for None/vazio ou o nó não existir mais
    (idempotente) -- aprovado 2026-08-10, fecha a assimetria criar/apagar da árvore."""
    if not codigo:
        return
    no = db.query(m.IdComercial).filter_by(codigo=codigo).first()
    if not no:
        return
    tem_filho = db.query(m.IdComercial).filter(m.IdComercial.codigo.like(f"{codigo}.%")).first()
    if tem_filho:
        return
    db.delete(no)


def nome_por_codigo(db, codigo: str):
    """Nome ATUAL do nó da árvore pra um código salvo — usado só pra exibição/compatibilidade com
    dados de fora da árvore (catálogo de válvulas, textos de memorial), nunca pra decidir nada."""
    if not codigo:
        return None
    no = db.query(m.IdComercial).filter_by(codigo=codigo).first()
    return no.nome if no else None


def nome_pai_por_codigo(db, codigo):
    """Nome do nó-PAI de um código da árvore ("8.1" -> nome de "8"; código de 1 nível -> ele mesmo).
    Rotula a categoria de exibição pelo pai do Id Comercial (Cadastro Comercial / Memorial) — aprovado 2026-08-14."""
    if not codigo:
        return None
    partes = str(codigo).split(".")
    pai = ".".join(partes[:-1]) if len(partes) > 1 else codigo
    return nome_por_codigo(db, pai)


def resolver_ids_avulsos_sistema(db, sistema, tipo_comando: str) -> set:
    """Resolve os códigos da ARVORE_ID_COMERCIAL que as seleções AVULSAS (sem catálogo próprio) de
    um Sistema referenciam — Tipo de Comando (do Projeto), Válvula de Expansão+Fabricante, Estrutura/
    Partida/Automação Equipamentos+Fabricante (só quando Rack Paralelo), Automação Linhas+Fabricante,
    Tipo Equip. Compressão, Tipo de Condensador, Modelo Controlador Linhas/Equipamentos.
    Os campos JÁ armazenam o código da árvore diretamente — uso direto, sem tradução por nome.
    Não resolve o texto/foto em si — só devolve os códigos, pra cruzar depois com CatalogoComercial.
    Item sem seleção feita (campo em branco) simplesmente não entra no conjunto."""
    ids = set()
    for codigo in (tipo_comando, sistema.tipo_compressao, sistema.selecao_condensador_ar,
                   sistema.tipo_expansao, sistema.estrutura_compressao,
                   sistema.partida, sistema.modo_operacao, sistema.automacao, sistema.automacao_fabricante,
                   sistema.modelo_controlador_equipamentos, sistema.tipo_automacao_linhas,
                   sistema.automacao_linhas_fabricante, sistema.modelo_controlador_linhas):
        if codigo:
            ids.add(codigo)
    return ids


def gerar_proximo_id_catalogo(db: Session, model_cls, campo_fabricante: str, valor_fabricante,
                               nome_fabricante: str, ancora: str, nome_item: str | None = None) -> str:
    """Id auto-gerado pra uma linha de catálogo nova (LinhaForcador/CatalogoUC/
    LinhaCondensadorRemoto). Busca, entre os filhos-FOLHA do nó `ancora` na árvore de Ids
    Comerciais, um cujo nome bata com `nome_fabricante` (case-insensitive): se achar, a Linha
    nova entra como próximo sequencial ABAIXO desse fabricante fixo (ex.: Elgin=4.2.1 -> nova
    linha = 4.2.1.1, 4.2.1.2...). Se o fabricante não estiver na lista fixa da árvore, cai no
    comportamento antigo: cria um galho novo numerado direto sob `ancora`, na ordem de cadastro.
    Fixo — calculado uma vez na criação, nunca recalculado (itens antigos não mudam de Id) — o
    CÁLCULO do código em si não muda com `nome_item`.
    `campo_fabricante`/`valor_fabricante` identificam o fabricante no MODELO (pode ser FK id ou
    nome, usado só pra achar linhas já existentes do mesmo fabricante); `nome_fabricante` é o nome
    de exibição, usado pra casar com a árvore.
    `nome_item` (opcional, nome da própria linha/catálogo): quando informado, materializa o nó na
    árvore de Ids Comerciais (visível em Configurações, `origem_automatica=True`) — reaproveita se
    já existir, nunca duplica. Sem `nome_item`, comportamento idêntico a antes (só retorna o
    código, sem tocar na árvore) — usado pelos scripts de migração antigos que ainda não foram
    atualizados (aprovado 2026-08-06: "fecha as arestas dos ids... tudo num só lugar")."""
    descendentes = db.query(m.IdComercial).filter(m.IdComercial.codigo.like(f"{ancora}.%")).all()

    # Candidato = nó de fabricante já existente, filho DIRETO da âncora, mesmo nome (case-
    # insensitive) — reaproveitado independente de já ter catálogos (linhas) embaixo dele. Antes
    # exigia "sem filho" (not tem_filho), o que só funcionava no 1º catálogo daquele fabricante:
    # do 2º em diante, o fabricante já tinha ao menos 1 linha-filha e deixava de ser reaproveitado,
    # criando um galho "Fabricante" duplicado a cada novo catálogo -- aprovado 2026-08-11 (bug real
    # confirmado: split de EVIB AC gerou 2 nós "Mipal" novos, 4.2.7 e 4.2.8, em vez de usar 4.2.2).
    nome_norm = (nome_fabricante or "").strip().lower()
    profundidade_fabricante = ancora.count(".") + 2
    candidato = next((d for d in descendentes
                       if d.nome.strip().lower() == nome_norm
                       and d.codigo.count(".") + 1 == profundidade_fabricante), None)

    if candidato:
        base = candidato.codigo
    else:
        # Fabricante fora da árvore fixa — cria um galho novo direto sob a âncora (1 nível abaixo).
        profundidade_alvo = ancora.count(".") + 2  # ex.: ancora "4.2" (1 ponto) -> filhos diretos com 2 pontos
        diretos = [d for d in descendentes if d.codigo.count(".") + 1 == profundidade_alvo]
        nums = [int(d.codigo.rsplit(".", 1)[-1]) for d in diretos if d.codigo.rsplit(".", 1)[-1].isdigit()]
        base = f"{ancora}.{(max(nums) if nums else 0) + 1}"
        if nome_item and nome_fabricante and not db.query(m.IdComercial).filter_by(codigo=base).first():
            db.add(m.IdComercial(codigo=base, nome=nome_fabricante, ordem=0, origem_automatica=True))
            db.flush()

    existentes = (db.query(model_cls)
                  .filter(model_cls.id_comercial.isnot(None))
                  .filter(model_cls.id_comercial.like(f"{base}.%")).all())
    nums_linha = []
    for obj in existentes:
        sufixo = obj.id_comercial[len(base) + 1:]
        if "." not in sufixo and sufixo.isdigit():
            nums_linha.append(int(sufixo))
    codigo_final = f"{base}.{(max(nums_linha) if nums_linha else 0) + 1}"

    if nome_item and not db.query(m.IdComercial).filter_by(codigo=codigo_final).first():
        db.add(m.IdComercial(codigo=codigo_final, nome=nome_item, ordem=0, origem_automatica=True))
        db.flush()

    return codigo_final


def proximo_sequencial_sob(db: Session, model_cls, id_pai: str, nome_item: str | None = None) -> str:
    """Gera o próximo id_comercial ABAIXO de `id_pai` escolhido pelo usuário na tela — substitui
    a auto-detecção de `gerar_proximo_id_catalogo` quando o frontend envia o nó-pai explícito.
    Conta tanto os nós já existentes na árvore quanto os id_comercial já usados no modelo
    (LinhaForcador/CatalogoUC/LinhaCondensadorRemoto), pega o maior e incrementa."""
    prefixo = id_pai + "."
    nos = db.query(m.IdComercial).filter(m.IdComercial.codigo.like(f"{prefixo}%")).all()
    nums_arvore = [int(n.codigo[len(prefixo):]) for n in nos
                   if "." not in n.codigo[len(prefixo):] and n.codigo[len(prefixo):].isdigit()]

    existentes = (db.query(model_cls)
                  .filter(model_cls.id_comercial.isnot(None))
                  .filter(model_cls.id_comercial.like(f"{prefixo}%")).all())
    nums_modelo = [int(obj.id_comercial[len(prefixo):]) for obj in existentes
                   if "." not in obj.id_comercial[len(prefixo):] and obj.id_comercial[len(prefixo):].isdigit()]

    proximo = max(nums_arvore + nums_modelo, default=0) + 1
    codigo = f"{id_pai}.{proximo}"

    if nome_item and not db.query(m.IdComercial).filter_by(codigo=codigo).first():
        db.add(m.IdComercial(codigo=codigo, nome=nome_item, ordem=0, origem_automatica=True))
        db.flush()

    return codigo


def resolver_no_modelo(db: Session, ancora: str, nome_modelo: str) -> str:
    """Acha (ou cria) o nó-filho de `ancora` na árvore de Ids Comerciais cujo nome bate com o
    Modelo do cadastro (Catálogo Comercial — Tela D), case-insensitive. Mesmo padrão de
    gerar_proximo_id_catalogo (Forçador/UC/Condensador): cada produto distinto ganha seu próprio
    Id, em vez de vários produtos dividirem o Id de categoria/fabricante escolhido no seletor —
    sem isso o Memorial não tinha como saber qual dos N produtos daquele Id puxar (aprovado
    2026-08-06). Reaproveita o nó se já existir (Salvar de novo sem mudar nada não duplica)."""
    filhos = db.query(m.IdComercial).filter(m.IdComercial.codigo.like(f"{ancora}.%")).all()
    profundidade_alvo = ancora.count(".") + 2
    diretos = [f for f in filhos if f.codigo.count(".") + 1 == profundidade_alvo]
    nome_norm = (nome_modelo or "").strip().lower()
    existente = next((f for f in diretos if f.nome.strip().lower() == nome_norm), None)
    if existente:
        return existente.codigo
    nums = [int(f.codigo.rsplit(".", 1)[-1]) for f in diretos if f.codigo.rsplit(".", 1)[-1].isdigit()]
    novo_codigo = f"{ancora}.{(max(nums) if nums else 0) + 1}"
    db.add(m.IdComercial(codigo=novo_codigo, nome=nome_modelo.strip(), ordem=0, origem_automatica=True))
    return novo_codigo


def gerar_id_cadastro(db: Session, id_comercial_escolhido: str) -> str:
    """"Id Cadastro" de um card do Cadastro Comercial (Tela D): "{id_comercial}-{sequencial}",
    sequencial exclusivo daquele id_comercial, nunca reaproveitado (maior já usado +1 — não conta
    registros vivos, então excluir um cadastro não libera o número de volta). Gerado uma vez na
    criação, fixo depois."""
    existentes = (db.query(m.CatalogoComercial)
                  .filter(m.CatalogoComercial.id_cadastro.like(f"{id_comercial_escolhido}-%")).all())
    nums = []
    for c in existentes:
        sufixo = c.id_cadastro[len(id_comercial_escolhido) + 1:]
        if sufixo.isdigit():
            nums.append(int(sufixo))
    return f"{id_comercial_escolhido}-{(max(nums) if nums else 0) + 1}"


def resolver_ids_paineis_portas(db: Session, projeto_id: int) -> set:
    """Resolve os códigos da ARVORE_ID_COMERCIAL (categoria "5.6 Painéis Térmicos Câmaras")
    referenciados pelos Painéis Térmicos e Portas Frigoríficas do projeto (Tela 7), a partir do
    id_comercial cadastrado em LookupPainelPorta (Configurações — ver t7_paineisPortasMatriz).
    Painel: casa PainelTermico.espessura (que já guarda o valor completo, ex.: "PIR 70mm" — é ali
    que o material PIR/EPS/PUR mora, não em Tipo Painel) com LookupPainelPorta(categoria=
    "Espessura Parede/Teto" ou "Espessura Piso" conforme painel.tipo).valor. Porta: casa
    PortaFrigorifica.modelo com LookupPainelPorta(categoria="Modelo Porta").valor, restrito ao
    mesmo grupo da Função da porta (mesma lógica de filtro do dropdown em Tela 7/10 — ver
    t10_grupoFuncao no frontend) — evita colisão quando o mesmo texto de Modelo existe em mais de
    um Grupo com Ids diferentes."""
    ids = set()
    lookup = db.query(m.LookupPainelPorta).all()

    espessura_id = {(l.categoria, l.valor): l.id_comercial for l in lookup
                     if l.categoria in ("Espessura Parede/Teto", "Espessura Piso") and l.id_comercial}
    grupo_por_funcao = {l.valor: l.grupo for l in lookup if l.categoria == "Função Porta"}
    modelo_id_por_grupo = {}   # (grupo, valor) -> id_comercial
    modelo_id_sem_grupo = {}   # valor -> id_comercial (fallback quando Função não tem grupo)
    for l in lookup:
        if l.categoria == "Modelo Porta" and l.id_comercial:
            modelo_id_por_grupo[(l.grupo, l.valor)] = l.id_comercial
            modelo_id_sem_grupo.setdefault(l.valor, l.id_comercial)

    for painel in db.query(m.PainelTermico).filter_by(projeto_id=projeto_id).all():
        categoria = "Espessura Piso" if painel.tipo == "Isolamento Piso" else "Espessura Parede/Teto"
        codigo = espessura_id.get((categoria, painel.espessura))
        if codigo:
            ids.add(codigo)

    for porta in db.query(m.PortaFrigorifica).filter_by(projeto_id=projeto_id).all():
        grupo = grupo_por_funcao.get(porta.funcao)
        codigo = modelo_id_por_grupo.get((grupo, porta.modelo)) or modelo_id_sem_grupo.get(porta.modelo)
        if codigo:
            ids.add(codigo)

    return ids


def montar_memorial_projeto(db: Session, projeto_id: int) -> dict:
    """Busca cruzada pro memorial/proposta (item 1.1 do escopo): junta os Ids AVULSOS de cada
    Sistema do projeto (comando, válvula, automações), os Ids de Painéis/Portas (Tela 7, via
    resolver_ids_paineis_portas) e os Ids de CATÁLOGO já auto-gerados (Forçador considerado em cada
    câmara, UC considerada em cada sistema), sem repetir, e devolve só os itens de CatalogoComercial
    (Tela D) que realmente têm esse Id cadastrado — o que não tiver texto/foto cadastrado na Tela D
    simplesmente não entra."""
    projeto = db.get(m.Projeto, projeto_id)
    if not projeto:
        return {"erro": "Projeto não encontrado"}

    ids = set()
    ids |= resolver_ids_paineis_portas(db, projeto_id)
    sistemas = db.query(m.SistemaRefrigeracao).filter_by(projeto_id=projeto_id).all()
    for s in sistemas:
        ids |= resolver_ids_avulsos_sistema(db, s, projeto.tipo_comando)

        if s.tipo_compressao == "Unidade Condensadora Comercial":
            uc_sel = (db.query(m.UnidadeSelecaoSistema)
                      .filter_by(sistema_id=s.id, considerado=True).first())
            if uc_sel and uc_sel.catalogo_id:
                catalogo = db.get(m.CatalogoUC, uc_sel.catalogo_id)
                if catalogo and catalogo.id_comercial:
                    ids.add(catalogo.id_comercial)

        for camara in s.camaras_completo:
            for f in camara.forcadores:
                if f.considerado:
                    linha = db.get(m.LinhaForcador, f.linha_id)
                    if linha and linha.id_comercial:
                        ids.add(linha.id_comercial)
        for camara in s.camaras_simples:
            for f in camara.forcadores:
                if f.considerado:
                    linha = db.get(m.LinhaForcador, f.linha_id)
                    if linha and linha.id_comercial:
                        ids.add(linha.id_comercial)

    itens = []
    if ids:
        for i in db.query(m.CatalogoComercial).filter(m.CatalogoComercial.id_comercial.in_(ids)).all():
            itens.append({"id": f"cc-{i.id}", "id_comercial": i.id_comercial,
                          "categoria": nome_pai_por_codigo(db, i.id_comercial) or i.categoria,
                          "fabricante": i.fabricante, "nome": i.nome,
                          "descricao_comercial": i.descricao_comercial, "imagem_path": i.imagem_path})
        # Forçador e Unidade Condensadora NÃO ficam em CatalogoComercial — o texto/foto mora no
        # próprio catálogo (LinhaForcador/CatalogoUC), já carregado junto com o dado técnico
        # tabular (ver comentário no topo de routers/catalogo_comercial.py).
        for linha in db.query(m.LinhaForcador).filter(m.LinhaForcador.id_comercial.in_(ids)).all():
            itens.append({"id": f"fc-{linha.id}", "id_comercial": linha.id_comercial, "categoria": "Forçador de Ar",
                          "fabricante": linha.fabricante.nome if linha.fabricante else None, "nome": linha.nome,
                          "descricao_comercial": linha.descricao_comercial, "imagem_path": linha.imagem_path})
        for cat in db.query(m.CatalogoUC).filter(m.CatalogoUC.id_comercial.in_(ids)).all():
            itens.append({"id": f"uc-{cat.id}", "id_comercial": cat.id_comercial, "categoria": "Unidade Condensadora Comercial",
                          "fabricante": cat.fabricante_uc, "nome": cat.nome,
                          "descricao_comercial": cat.descricao_comercial, "imagem_path": cat.imagem_path})

    return {"ids_resolvidos": sorted(ids, key=chave_codigo), "itens": itens}
