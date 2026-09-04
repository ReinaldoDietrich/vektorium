# Protocolo de extração de catálogos de Unidades Condensadoras (Tela B)

Guia que eu (assistente) sigo ao escrever o script de extração de um catálogo completo (PDF) de um
novo fabricante. Não existe mais o fluxo de Documento Word + colar prints — o usuário fornece o
catálogo inteiro e eu escrevo um script específico para aquele fabricante, que gera o `.xlsx` no
schema abaixo (o mesmo lido por `uc_import.py`, sem mudança nenhuma no app).

## Schema de saída (fixo, não muda por fabricante)

5 abas — `Unidades`, `Eletricas`, `Capacidades`, `Nomenclatura`, `Fatores_Gas` (opcional) — colunas
exatamente como em `COLUNAS_UNIDADES` / `COLUNAS_ELETRICAS` / `COLUNAS_CAPACIDADES` em
`uc_import.py`. Coluna sem dado no catálogo: célula em branco, nunca inventar valor.

`Unidades` inclui `Nome_Catalogo` (OBRIGATÓRIO) — identifica o documento de origem, porque
Fabricante+Versão sozinhos não diferenciam catálogos publicados na mesma data (ex.: Elgin publica
vários catálogos "02/2025" pra faixas de HP diferentes). Use um nome que descreva o catálogo (ex.:
"US 10 a 66HP - 2 e 3 Compressores", geralmente próximo do nome do arquivo/documento fonte).
`Unidades` também tem a coluna `Descricao_Comercial` (opcional) — texto do catálogo, o mesmo repetido
em todas as linhas (vale pro catálogo inteiro, não por modelo); se o catálogo/documento fonte não
trouxer nenhum texto descritivo, deixe em branco, nunca invente. Só a foto do catálogo NÃO vai na
planilha — é enviada depois direto na tela (não há caminho de imagem pela planilha).

`Unidades` carrega só o que é **físico/dimensional** (não varia por tensão nem por compressor no
catálogo real: conexões, tanque, ruído, diâmetro de ventilador, dimensões, peso). Toda a **elétrica**
(tensão, fases, frequência, modelo do compressor, MCC/RLA/LRA, elétrica dos ventiladores) vai na aba
`Eletricas` — confirmado em catálogo real que o mesmo Modelo+Tensão pode ter mais de uma opção de
compressor, cada uma com corrente própria (ex.: `U*HMB4120J*D2` com compressor `H5O5CC` OU `H7O5CC`,
MCC/RLA/LRA diferentes em cada linha). Gere **uma linha em `Eletricas` para cada combinação**
Modelo × Tensão × Modelo_Compressor que aparecer no catálogo — nunca resuma numa linha só.

## Regra 1 — modelo + gás = registros separados, nunca fundir

Fabricantes frequentemente reduzem catálogo mostrando um único código mecânico (ex.: `U*HMB4120`)
cobrindo blocos de gases diferentes (ex.: R-404A/R-507 e R-134a) com faixas de evaporação e
capacidades diferentes. São **máquinas diferentes**. Cada combinação (Fabricante_UC, Modelo, Gas,
Fabricante_Compressor, Versao_Catalogo) vira uma linha própria na aba `Unidades`, com seu próprio
conjunto de capacidades na aba `Capacidades` e suas linhas na aba `Eletricas`. `uc_import.py` já faz
upsert por essa chave — nunca sobrescreve um gás com dado de outro.

`Fabricante_Compressor` faz parte da chave porque dois fabricantes de compressor podem usar o
mesmo código de modelo mecânico com especificações elétricas diferentes — isso se resolve por essa
coluna, e NÃO deve ser embutido no texto do campo `Modelo` (ex.: nunca `"U*CMB4120 Copeland"` —
o campo `Modelo` fica limpo, a marca do compressor vai só em `Fabricante_Compressor` na aba
`Unidades` e `Modelo_Compressor` na aba `Eletricas`).

## Regra 2 — nomenclatura em 3 camadas (não confundir extração com seleção)

A nomenclatura completa de uma UC (ex.: `U`+`S`+`H`+`MB`+`4`+`120`+`J`+`T`+`D`+`2`+`C`+`C`+`C`) tem
campos de três naturezas diferentes. Só a primeira categoria é extraída do catálogo:

1. **Técnicos** — vêm do catálogo, sempre extraídos: Tipo_Compressor, Modelo_Compressor (aba
   `Eletricas`, por Tensão), Fabricante_Compressor (aba `Unidades`), HP, `Numero_Compressores`
   (coluna própria — usada no cálculo de consumo elétrico da Tela D, não confundir com `Vent_Qtd`
   que é quantidade de ventiladores).
2. **De filtro** — também existem no catálogo (Sistema/Aplicação, Gas/Fluído, Tensão), mas na hora
   da seleção da UC no app eles são comparados contra o projeto/sistema, não perguntados de novo —
   a Tensão específica de cada projeto resolve automaticamente qual linha da aba `Eletricas` usar.
3. **Flutuantes** — NÃO existem nas tabelas técnicas de capacidade/elétrica/física do catálogo (não
   têm coluna própria ali, não fazem parte da aba `Unidades`): Fluxo de Ar (S/V), Linha de Líquido,
   Versão, Opcional Mecânico, Opcional Elétrico. **Nunca tentar extrair um VALOR desses campos por
   modelo** — quem escolhe qual valor se aplica é o usuário no app, por sistema, no momento da
   seleção da UC (Tela 1 → seleção por sistema), compondo o código comercial completo junto com o
   código técnico dos campos 1 e 2 (ver `_gerar_codigo`/`_gerar_codigo_comercial` em
   `backend/routers/unidades_condensadoras.py`).

   **Mas o DICIONÁRIO de código dessas categorias (o que cada letra/código SIGNIFICA) é dado de
   catálogo sim, e deve ser extraído** — ele está na página de nomenclatura do código de compra do
   fabricante (a tabela que decompõe o código, ex.: "S = Fluxo Horizontal, V = Fluxo Vertical").
   Diferença: o VALOR por modelo não se extrai (é escolha do comprador); o SIGNIFICADO de cada
   código, sim (é informação do fabricante). Sempre que o catálogo trouxer essa página, extraia
   TODAS as categorias nela (técnicas, de filtro E flutuantes) para a aba `Nomenclatura` —
   Categoria/Valor/Codigo, uma linha por opção de cada campo do código de compra. Não pule as
   categorias flutuantes achando que "não é extraível" — o que não é extraível é o valor por
   modelo, não o dicionário de códigos.

## Regra 3 — reconhecer dado pelo rótulo/unidade, não pela posição

Um fabricante pode misturar categorias dentro da mesma tabela (ex.: dado físico dentro da tabela
elétrica). Não presumir que "tabela elétrica só tem dado elétrico". Identificar cada valor pelo
que ele É (nome do campo, unidade de medida — mm→dimensão, A→corrente, kg→peso, dB→ruído, L→volume)
e não pela seção/tabela onde apareceu. Varrer o catálogo inteiro em vez de esperar layout fixo.

## Regra 4 — dicionário de termos entre fabricantes

Termos variam mas o conceito é o mesmo. Mapear pelo sentido, não pela grafia exata:
- Capacidade: "Capacidade Frigorífica", "Cooling Capacity", "Q"
- Corrente de operação: "MCC", "Corrente Máx. Operação", "FLA"
- Corrente nominal: "RLA", "Corrente Nominal" — se ausente e só houver MCC: RLA ≈ MCC/1,56 (Copeland: MCC/1,4)
- Corrente de rotor bloqueado: "LRA", "Corrente de Partida"
- Vazão de ar / corrente de ventilador, tensão, etc. — mesma lógica de sinônimo.

## Regra 5 — nunca inventar dado ausente

Coluna/valor que não aparece no catálogo para aquele modelo: deixar em branco. Nunca extrapolar,
nunca copiar de um modelo vizinho, nunca assumir units metric/elétrico padrão sem a fonte dizer.
Só a coluna de temperatura de evaporação pode legitimamente variar/faltar por modelo (catálogos
reduzem a faixa tabelada pra compressores menores) — todo o resto ausente é mesmo ausente.

## Regra 6 — evitar duplicidade na extração

Ao processar o PDF em blocos/páginas, cuidado com blocos que se repetem ou se sobrepõem (o mesmo
modelo aparecendo em duas páginas, ou uma tabela dividida em duas colunas de PDF lidas duas vezes).
Antes de gerar o Excel final, validar que não existem duas linhas de `Capacidades` para a mesma
combinação (Modelo, Temp_Ambiente_C, Temp_Evaporacao_C) — se houver, é sinal de bloco processado
duas vezes, não duas leituras legítimas.

## Regra 7 — depois de extrair, revisar na matriz da tela, não perguntar antes

Gerar o Excel com o melhor julgamento, sem interromper para confirmar cada célula. A prévia de
importação da Tela B (matriz editável, 2 sub-abas Mecânica / Elétrica — a de Elétrica mostra uma
linha por Tensão × Modelo de Compressor, podendo ter várias linhas por unidade) é o lugar certo
para o usuário conferir e corrigir antes de confirmar — dúvidas/gaps viram uma nota depois da
extração, não uma pergunta antes dela.

## Notas específicas por fabricante

### Danfoss / Optyma
- Danfoss não informa RLA nem LRA no catálogo — só MOC (Corrente Máxima de Operação). MOC é o
  mesmo conceito de MCC (falha de nomenclatura do fabricante, não um dado a mais). Tratar MOC
  como MCC_A; usar o mesmo valor de MOC também em RLA_A. LRA_A fica em branco para esse fabricante.
- Peso Bruto/Líquido varia por código de configuração do produto (D20/D39/D49, podendo aparecer
  variação pontual como D40 por exceção do próprio catálogo) para o mesmo Modelo. Como a aba
  `Unidades` só guarda um par Peso_Bruto_kg/Peso_Liquido_kg por modelo (não por configuração),
  usar o MAIOR valor de peso bruto e o MAIOR valor de peso líquido entre as configurações
  disponíveis daquele modelo. Não alterar o schema de importação por causa disso.
