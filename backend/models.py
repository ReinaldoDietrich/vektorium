from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


# ===================== PROJETO E SISTEMAS =====================

class Projeto(Base):
    __tablename__ = "projetos"
    id = Column(Integer, primary_key=True)
    codigo_projeto = Column(String, nullable=False)
    data = Column(String)
    cliente = Column(String)
    cidade_instalacao = Column(String)
    altitude_m = Column(Float)
    temp_ambiente = Column(Float)
    # Substituídos por Estado+Estação INMET (ver estado_uf/estacao_inmet_id) — mantidos só pra não
    # perder dado de projeto antigo já salvo; não usados mais na Tela 1 (discussão real 2026-07-18:
    # eliminado o seletor de Critério de Projeto, fonte única agora é a Temperatura Máxima Histórica).
    estacao_climatologica_id = Column(Integer, ForeignKey("cat_condicoes_climaticas.id"), nullable=True, index=True)
    criterio_climatico = Column(String, default="pico_sazonal")  # pico_sazonal | media_anual | maxima_absoluta
    estado_uf = Column(String)  # sigla (ver EstadoBrasileiro) — filtra a lista de Estação Climatológica
    estacao_inmet_id = Column(Integer, ForeignKey("dados_climatologicos_inmet.id"), nullable=True, index=True)
    ur_externa = Column(Float)  # preenchido a partir da estação (Temp. Máxima Histórica), editável
    contato = Column(String)
    telefone = Column(String)
    tipo_comando = Column(String)
    tensao_equipamentos = Column(String)
    tensao_comando = Column(String)
    custo_energia = Column(Float)
    # Pasta do Windows onde as exportações EXCEL deste projeto são salvas direto (Compilação
    # Linhas, Painéis e Portas, Compilação Geral, Consumo Elétrico) — em branco = comportamento
    # padrão (download do navegador). PDF não usa isso (sempre impressão do navegador).
    pasta_salvamento = Column(String)
    condicao_salao = Column(String, default="25°C - 60% UR (com ar condicionado)")

    # ---- Tela E — Painéis e Portas: medidas de placa não variam dentro do mesmo projeto ----
    largura_placa_painel_m = Column(Float, default=1.15)  # parede/teto — padrão do fabricante escolhido
    piso_placa_largura_m = Column(Float)
    piso_placa_comprimento_m = Column(Float)
    largura_min_aproveitamento_placa_m = Column(Float)  # sobra de placa (Parede/Teto) abaixo desse
    # valor é descartada do reaproveitamento entre painéis do mesmo Id — ver calc_paineis_portas.py

    # ---- Tela 5 — Compilação: observação técnica sobre as cargas elétricas (potência total/
    # demandada, degelo, iluminação) — NULL usa o texto padrão gerado automaticamente com os
    # valores reais do projeto; editável e persistido aqui quando o usuário customiza.
    observacao_compilacao_eletrica = Column(Text)
    # NULL usa o texto padrão da Tela D (Consumo Elétrico); editável e persistido aqui quando
    # o usuário customiza — mesmo padrão de observacao_compilacao_eletrica.
    observacao_consumo_eletrica = Column(Text)
    # Texto de responsabilidade sobre os dados de entrada fornecidos pelo cliente (Tela F —
    # Compilação Geral). NULL usa o texto padrão; editável e persistido aqui quando customizado.
    observacao_dados_entrada = Column(Text)

    # Considerar a carga elétrica de iluminação AMBIENTE (Câmara Completo/Simples) nos cálculos de
    # potência (Tela 5) e consumo (Tela D) — NUNCA afeta Expositor, cuja iluminação é obrigatória
    # (embutida na carga elétrica própria do equipamento).
    considerar_iluminacao_ambiente = Column(Boolean, default=True)

    # Fonte de tensão dos "Quadro de Linhas" no Resumo de Potência por Sistema (Tela 5) — decisão do
    # projetista ELÉTRICO, não do de refrigeração: "comando" ou "equipamentos" (default, mantém o
    # comportamento anterior a essa opção existir). Único valor pro projeto inteiro — não é por
    # sistema, pra não exigir do projetista de refrigeração decidir detalhe elétrico linha a linha.
    quadro_linhas_tensao_fonte = Column(String, default="equipamentos")

    # ---- Controle de Revisão ----
    # Cada revisão é um Projeto próprio (cópia editável, NÃO congela). `codigo_base` agrupa todas as
    # revisões de um mesmo projeto; `revisao` é o número (0 = R00, 1 = R01…); `revisao_de` aponta o
    # projeto de onde esta revisão foi gerada (a anterior). Cálculo/exportações não mudam — uma
    # revisão é só outro projeto, com os mesmos dados amarrados por projeto_id.
    codigo_base = Column(String)
    revisao = Column(Integer, default=0)
    revisao_de = Column(Integer, ForeignKey("projetos.id"), nullable=True, index=True)

    # ---- Dados de Faturamento/Obra (Tela 1 — aprovado 2026-08-12) ----
    razao_social_faturamento = Column(String)
    cnpj_faturamento = Column(String)
    cep_faturamento = Column(String)
    endereco_faturamento = Column(String)
    endereco_obra = Column(String)
    cep_obra = Column(String)

    # Projeto "Fechado" — trava reversível de edição (aprovado 2026-08-12). Checado no meio-termo
    # do fluxo de escrita (ver backend/routers/_bloqueio_projeto.py); nunca no meio de leitura.
    fechado = Column(Boolean, default=False)
    fechada_dados_gerais = Column(Boolean, default=False)
    fechada_clima = Column(Boolean, default=False)
    fechada_estrutural = Column(Boolean, default=False)

    # UUID que identifica o projeto na nuvem (Supabase Storage). Gerado no primeiro push;
    # persiste na máquina destino após o pull. Permite detectar duplicatas entre terminais.
    cloud_id = Column(String, nullable=True)

    sistemas = relationship("SistemaRefrigeracao", back_populates="projeto", cascade="all, delete-orphan")
    estacao_climatologica = relationship("CondicaoClimatica")


class SistemaRefrigeracao(Base):
    __tablename__ = "sistemas_refrigeracao"
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False, index=True)
    nome = Column(String, nullable=False)
    classificacao = Column(String)
    gas_refrigerante = Column(String)
    tipo_expansao = Column(String)  # "Eletrônica" | "Termostática" | "Reguladora de Vazão Manual" | "Reguladora de Vazão Automática"
    fabricante_valvula = Column(String)  # Danfoss/Carel/FullGauge/Belimo — campo próprio, não reaproveita automacao_linhas_fabricante
    temp_evaporacao = Column(Float)
    precisa_revisar = Column(Boolean, default=False)
    fechada = Column(Boolean, default=False)

    # ---- Compressão ----
    tipo_compressao = Column(String)  # "Unidade Condensadora Comercial" | "Rack Paralelo"
    estrutura_compressao = Column(String)  # "Carenado" | "Sem Carenagem"
    # Como o compressor liga — puramente descritivo, compõe a descrição técnica de compra do
    # equipamento (memorial/Id Comercial). NÃO tem efeito em cálculo de consumo (Tela D): partida
    # (Direta/Dividida/SoftStarter) só reduz corrente de pico no instante de partida, não o consumo
    # em regime — confirmado na literatura (ver discussão real 2026-07-17). "Dividida" = partida
    # estrela-triângulo.
    partida = Column(String)  # "Direta" | "Dividida" | "SoftStarter"
    # Como o compressor opera em regime (independente de como liga — ver `partida`). None/"" =
    # Liga/Desliga tradicional (padrão), sem redução de consumo. "Controle de Capacidade" =
    # descarregamento mecânico de cilindros (ex.: Bitzer CR). "Inversor de Frequência" = modulação
    # real de rotação (VFD). Cada um tem seu próprio fator de redução em Configurações Globais
    # (reducao_controle_capacidade_pct / reducao_inversor_pct) — ver calculo_consumo.py pra
    # fundamentação técnica e fontes.
    modo_operacao = Column(String)  # None | "Controle de Capacidade" | "Inversor de Frequência"
    automacao = Column(String)  # "Eletromecânico" | "Gerenciamento Eletrônico" — Rack ou UC (compressão)
    automacao_fabricante = Column(String)  # Danfoss/Fullgauge/Carel, só quando automacao = "Gerenciamento Eletrônico"
    # Automação das linhas de evaporador (controle da(s) válvula(s) de expansão) — sempre com
    # fornecedor, independente de Controle/Supervisão.
    tipo_automacao_linhas = Column(String)  # "Controle Simples" | "Controle + Acesso Remoto" | "Supervisão"
    automacao_linhas_fabricante = Column(String)  # Danfoss/Fullgauge/Carel
    # Modelo do controlador — nó-filho do fornecedor (1.2.n.m) na árvore de Ids Comerciais, cadastrado
    # via campo Modelo do Catálogo Comercial (Tela D). Opcional (aprovado 2026-08-08).
    modelo_controlador_linhas = Column(String)
    modelo_controlador_equipamentos = Column(String)  # idem, ramo 1.3.n.m (Automação Equipamentos)
    temp_apos_condensador = Column(Float)  # linha de líquido
    temp_apos_subresfriamento = Column(Float)  # linha de líquido

    # ---- Consumo elétrico / payback (Tela D) ----
    quantidade_degelo_dia = Column(Float, default=4)  # nº de ciclos de degelo elétrico por dia
    tempo_degelo_min = Column(Float, default=60)  # duração de 1 ciclo — Quantidade x Tempo/60 dá as
    # horas de degelo/dia, usadas no consumo (Tela D) e na estimativa de simultaneidade (Tela 5)
    custo_sistema_simples = Column(Float)  # instalação sem inversor/EEV/degelo a gás — p/ payback
    custo_sistema_projeto = Column(Float)  # instalação conforme selecionado no projeto
    horas_iluminacao_dia = Column(Float, default=10)  # usada no consumo (Tela D) pra TODAS as
    # câmaras do sistema (Completo/Simples/Expositor) — ignora a premissa de 24h do cálculo de
    # carga térmica (Q6), que é conservadora de propósito pra dimensionamento, não pra custo real.
    # Editável direto na Tela D; valor documentado nas Observações Técnicas (Tela 5).

    # ---- Condensação ----
    # condensador_tipo/tipo_motor_condensador/protecao_aletas saíram daqui (2026-07-20): a seleção
    # de condensador é por-Rack agora (RackParalelo.tipo_condensador/protecao_aletas_condensador),
    # não por-Sistema — colunas antigas continuam no banco (não mapeadas), sem uso.
    selecao_condensador_ar = Column(String)  # "Nenhum" | "Remoto" | "Onboard"
    delta_condensacao = Column(Float)  # temp. condensação = temp. ambiente do projeto + delta

    projeto = relationship("Projeto", back_populates="sistemas")
    camaras_completo = relationship("CamaraCompleto", back_populates="sistema", cascade="all, delete-orphan")
    camaras_simples = relationship("CamaraSimples", back_populates="sistema", cascade="all, delete-orphan")
    expositores = relationship("Expositor", back_populates="sistema", cascade="all, delete-orphan")
    # N racks por sistema (alternativas, padrão "múltiplas opções + considerado" igual forçador/UC).
    racks = relationship("RackParalelo", back_populates="sistema", cascade="all, delete-orphan",
                         order_by="RackParalelo.id")

    @property
    def rack_paralelo(self):
        """Rack CONSIDERADO do sistema (o que entra em cálculo/compilação/consumo). Compat: todo o
        código de leitura continua acessando `sistema.rack_paralelo` como objeto único — recebe o
        considerado (ou o primeiro, se nenhum marcado). Retorna None se o sistema não tem rack."""
        if not self.racks:
            return None
        for r in self.racks:
            if r.considerado:
                return r
        return self.racks[0]


# ===================== CATÁLOGOS — PRODUTOS E EMBALAGEM =====================

class Produto(Base):
    __tablename__ = "cat_produtos"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False, unique=True)
    temp_conservacao = Column(String)
    umidade_relativa = Column(String)
    tempo_conservacao = Column(String)
    pct_agua = Column(Float)
    ponto_congelamento = Column(Float)
    calor_esp_antes = Column(Float)
    calor_esp_depois = Column(Float)
    calor_latente = Column(Float)
    calor_respiracao = Column(Float)
    classe = Column(Integer)
    fonte_status = Column(String)


class TipoEmbalagem(Base):
    __tablename__ = "cat_tipos_embalagem"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False, unique=True)
    calor_especifico = Column(Float)  # kcal/kg.K


# ===================== CATÁLOGOS — ISOLAMENTO E EQUIPAMENTOS =====================

class IsolamentoParedeTeto(Base):
    __tablename__ = "cat_isolamento_parede_teto"
    id = Column(Integer, primary_key=True)
    material = Column(String, nullable=False)
    espessura_mm = Column(Integer, nullable=False)
    u_valor = Column(Float, nullable=False)  # kcal/h.m2.C
    vao_maximo_apoios_mm = Column(Integer)  # datasheet do fabricante — informativo, por material+espessura


class IsolamentoPiso(Base):
    __tablename__ = "cat_isolamento_piso"
    id = Column(Integer, primary_key=True)
    material = Column(String, nullable=False)
    espessura_mm = Column(Integer)
    u_valor = Column(Float, nullable=False)
    valido_apenas_acima_zero = Column(Boolean, default=False)


class TipoEquipamento(Base):
    """Cenário 1 (ASHRAE) — motor e carga no mesmo ambiente: todo o calor emitido é
    potencia_tipica_w x fator_calor_rejeitado x fator_simultaneidade. Valores de mercado
    (não normativos), editáveis em Configurações."""
    __tablename__ = "cat_tipos_equipamento"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False, unique=True)
    potencia_tipica_w = Column(Float)
    fator_calor_rejeitado = Column(Float)  # fração (0-1) da potência que vira calor sensível na sala
    fator_simultaneidade = Column(Float)   # fração (0-1) de uso concorrente sugerida


# ===================== CATÁLOGOS — CLIMA, TABELA 02, AJUSTES =====================

class CondicaoClimatica(Base):
    """Normal Climatológica do Brasil 1991-2020 (INMET), por estação. Três critérios de projeto
    pré-calculados (pico sazonal / média anual / máxima absoluta) — o usuário escolhe qual usar
    por projeto (Tela 1)."""
    __tablename__ = "cat_condicoes_climaticas"
    id = Column(Integer, primary_key=True)
    cidade = Column(String, nullable=False, unique=True)  # nome da estação INMET
    uf = Column(String)
    codigo_estacao = Column(Integer)
    tbs_pico_sazonal = Column(Float)  # maior TMAX mensal
    tbu_pico_sazonal = Column(Float)  # TMEDUMID no mesmo mês do pico de TMAX
    ur_pico_sazonal = Column(Float)   # UR no mesmo mês do pico de TMAX
    tbs_media_anual = Column(Float)
    tbu_media_anual = Column(Float)
    ur_media_anual = Column(Float)
    tbs_maxima_absoluta = Column(Float)  # recorde histórico (TMAXABS), sem TBU/UR pareado


class EstadoBrasileiro(Base):
    """Tela 1 - Lista de Estados Brasileiros (Configurações) — fonte: Tabela Lista Estados.xlsx.
    Usado pro campo Estado (Tela 1) e pra filtrar a lista de Estação Climatológica por UF."""
    __tablename__ = "estado_brasileiro"
    id = Column(Integer, primary_key=True)
    estado = Column(String, nullable=False)
    sigla = Column(String, nullable=False, unique=True)
    capital = Column(String)
    regiao = Column(String)


class DadosClimatologicosInmet(Base):
    """Tela 1 - Dados Climatológicos INMET 1990-2020 (Configurações) — fonte: Tabela de Dados
    Climatológicos.xlsx (aba TMAXABS). Substitui o antigo seletor "Critério de Projeto" (pico
    sazonal/média anual/máxima absoluta) — fonte única agora: Temperatura Máxima Histórica + UR
    Média pareada (discussão real 2026-07-18). O cabeçalho de origem da planilha rotulava essas
    duas colunas como "JANEIRO" (mesclado) — renomeado pra "Histórica" por instrução do usuário,
    já que representa o recorde histórico da estação, não um mês específico."""
    __tablename__ = "dados_climatologicos_inmet"
    id = Column(Integer, primary_key=True)
    codigo = Column(String, nullable=False)
    nome_estacao = Column(String, nullable=False)
    uf = Column(String, nullable=False)
    temp_maxima_historica = Column(Float)
    ur_media_historica = Column(Float)


class TabelaTipo02(Base):
    """Tipo de câmara/produto da Tabela 02 (Téchne/UCI). O valor de carga não é mais um fator
    linear por m² — é consultado por faixa de área em FaixaAreaTabela02 (tabela real do usuário
    não é linear: valores crescem de forma decrescente por m² conforme a área aumenta)."""
    __tablename__ = "cat_tabela_tipo02"
    id = Column(Integer, primary_key=True)
    tipo = Column(String, nullable=False, unique=True)
    temp_interna_default = Column(Float)


class FaixaAreaTabela02(Base):
    """Uma linha da tabela real do usuário: para a faixa de área [area_de, area_ate], a carga
    térmica (kcal/h) já tabelada para este tipo de câmara — ainda falta multiplicar pelo Fator
    Altura (pé-direito)."""
    __tablename__ = "cat_faixa_area_tabela02"
    id = Column(Integer, primary_key=True)
    tabela02_id = Column(Integer, ForeignKey("cat_tabela_tipo02.id"), nullable=False, index=True)
    area_de = Column(Float, nullable=False)
    area_ate = Column(Float, nullable=False)
    carga_kcal_h = Column(Float, nullable=False)
    tabela02 = relationship("TabelaTipo02")


class FatorAltura(Base):
    __tablename__ = "cat_fator_altura"
    id = Column(Integer, primary_key=True)
    pe_direito_ate_m = Column(Float, nullable=False)
    fator = Column(Float, nullable=False)


class FatorInsolacao(Base):
    """Referência de majoração de insolação por orientação/exposição (Q3 Penetração) — valores de
    mercado, não é uma tabela ASHRAE fechada. Editável em Configuração."""
    __tablename__ = "cat_fator_insolacao"
    id = Column(Integer, primary_key=True)
    orientacao = Column(String, nullable=False, unique=True)
    fator = Column(Float, nullable=False)


class ConfiguracaoGlobal(Base):
    """Configurações globais de cálculo (% de ajuste simples, majoração de insolação, etc.)."""
    __tablename__ = "configuracao_global"
    id = Column(Integer, primary_key=True)
    chave = Column(String, nullable=False, unique=True)
    valor = Column(Float, nullable=False)
    descricao = Column(String)
    pendente_confirmacao = Column(Boolean, default=False)


class FaixaTrocasAr(Base):
    __tablename__ = "cat_faixas_trocas_ar"
    id = Column(Integer, primary_key=True)
    tipo_aplicacao = Column(String, nullable=False, unique=True)
    minimo = Column(Float, nullable=False)
    maximo = Column(Float, nullable=False)


class ClasseProduto(Base):
    __tablename__ = "cat_classes_produto"
    id = Column(Integer, primary_key=True)
    classe = Column(Integer, nullable=False, unique=True)
    dt_evap_min = Column(Float)
    dt_evap_max = Column(Float)
    ur_min = Column(Float)
    ur_max = Column(Float)
    aplicacao = Column(String)


# ===================== CATÁLOGOS — EXPOSITOR =====================

class SetorExpositor(Base):
    __tablename__ = "cat_setores_expositor"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False, unique=True)


class BancoExpositor(Base):
    __tablename__ = "cat_bancos_expositor"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False, unique=True)

    modelos = relationship("ModeloExpositor", back_populates="banco", cascade="all, delete-orphan")


class ModeloExpositor(Base):
    __tablename__ = "cat_modelos_expositor"
    id = Column(Integer, primary_key=True)
    banco_id = Column(Integer, ForeignKey("cat_bancos_expositor.id"), nullable=False, index=True)
    nome = Column(String, nullable=False)
    carga_termica_25 = Column(Float)  # kcal/h, salão 25C/60%UR
    carga_termica_28 = Column(Float)  # kcal/h, salão 28C/70%UR
    carga_eletrica_w = Column(Float)
    vazao_ar_m3h = Column(Float)

    banco = relationship("BancoExpositor", back_populates="modelos")


# ===================== FABRICANTE (compartilhado: forçadores e válvulas) =====================

class Fabricante(Base):
    __tablename__ = "cat_fabricantes"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False, unique=True)

    # cascade obrigatório: excluir um Fabricante sem arrastar Linhas/Válvulas deixa registros
    # órfãos que quebram os endpoints de listagem (AttributeError ao acessar .fabricante.nome).
    linhas_forcador = relationship("LinhaForcador", cascade="all, delete-orphan",
                                    foreign_keys="LinhaForcador.fabricante_id")
    modelos_valvula = relationship("ModeloValvula", cascade="all, delete-orphan")
    linhas_condensador = relationship("LinhaCondensadorRemoto", cascade="all, delete-orphan",
                                       foreign_keys="LinhaCondensadorRemoto.fabricante_id")


# ===================== FORÇADORES DE AR (Etapa 3) =====================

class LinhaForcador(Base):
    __tablename__ = "forcador_linhas"
    id = Column(Integer, primary_key=True)
    fabricante_id = Column(Integer, ForeignKey("cat_fabricantes.id"), nullable=False, index=True)
    nome = Column(String, nullable=False)
    versao_catalogo = Column(String)  # ex.: "2024", "2026"
    ativo_comercial = Column(Boolean, default=True)  # False = fora de linha (só uso técnico/reformas)
    observacao_versao = Column(Text)  # ex.: "vale para 2024 e 2026, sem alterações"
    linha_anterior_id = Column(Integer, ForeignKey("forcador_linhas.id"), nullable=True, index=True)
    descricao_comercial = Column(Text)  # texto único do catálogo inteiro, não por modelo
    imagem_path = Column(Text)  # foto do equipamento, uma por catálogo (base64 data URI)
    # Id comercial auto-gerado na criação (categoria 6 = Forçador de Ar), formato "6.<fabricante>.
    # <linha>" — ver id_comercial.py. Fixo, não recalcula depois (evita mudar Id de itens antigos).
    id_comercial = Column(String)

    fabricante = relationship("Fabricante", back_populates="linhas_forcador")
    modelos = relationship("ModeloForcador", back_populates="linha", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("fabricante_id", "nome", "versao_catalogo", name="uq_linha_versao"),)


class ModeloForcador(Base):
    __tablename__ = "forcador_modelos"
    id = Column(Integer, primary_key=True)
    linha_id = Column(Integer, ForeignKey("forcador_linhas.id"), nullable=False, index=True)
    modelo = Column(String, nullable=False)
    fpi = Column(Integer)  # aletas por polegada
    num_ventiladores = Column(Integer)
    diametro_ventilador_mm = Column(Float)
    tipo_degelo = Column(String)
    carga_gas_kg = Column(Float)
    pot_resistencia_degelo_w = Column(Float)
    vazao_ar_m3h = Column(Float)
    dt_referencia_c = Column(Float)  # DT do catálogo (geralmente 6)
    pdl_referencia_m = Column(Float)  # pé-direito limite de referência
    flecha_ar_m = Column(Float)
    altura_max_instalacao_m = Column(Float)
    coletores_por_forcador = Column(Integer, default=1)
    nomenclatura_compra = Column(Text)  # regra de composição do nome de compra (texto livre, etapa futura)
    descricao_comercial = Column(Text)
    imagem_path = Column(Text)

    linha = relationship("LinhaForcador", back_populates="modelos")
    capacidades = relationship("CapacidadeForcador", back_populates="modelo", cascade="all, delete-orphan")
    eletricas = relationship("DadosEletricosForcador", back_populates="modelo", cascade="all, delete-orphan")
    fisicos = relationship("DadosFisicosForcador", back_populates="modelo", uselist=False, cascade="all, delete-orphan")
    dimensionais = relationship("DadosDimensionaisForcador", back_populates="modelo", uselist=False, cascade="all, delete-orphan")


class CapacidadeForcador(Base):
    """Capacidade do modelo (kcal/h) em cada temperatura de evaporação tabelada, no DT/pdl de referência da linha."""
    __tablename__ = "forcador_capacidades"
    id = Column(Integer, primary_key=True)
    modelo_id = Column(Integer, ForeignKey("forcador_modelos.id"), nullable=False, index=True)
    temp_evaporacao_c = Column(Float, nullable=False)
    capacidade_kcal_h = Column(Float, nullable=False)

    modelo = relationship("ModeloForcador", back_populates="capacidades")


class DadosEletricosForcador(Base):
    __tablename__ = "forcador_eletricos"
    id = Column(Integer, primary_key=True)
    modelo_id = Column(Integer, ForeignKey("forcador_modelos.id"), nullable=False, index=True)
    tensao = Column(String, nullable=False)  # ex.: "220V/1F/60Hz"
    degelo_w = Column(Float)
    degelo_a = Column(Float)
    motores_w = Column(Float)
    motores_a = Column(Float)

    modelo = relationship("ModeloForcador", back_populates="eletricas")


class DadosFisicosForcador(Base):
    __tablename__ = "forcador_fisicos"
    id = Column(Integer, primary_key=True)
    modelo_id = Column(Integer, ForeignKey("forcador_modelos.id"), nullable=False, index=True)
    linha_liquido = Column(String)
    linha_succao = Column(String)
    equalizador = Column(String)
    dreno = Column(String)
    peso_liquido_kg = Column(Float)  # sempre peso líquido (sem embalagem) — peso bruto não é capturado
    carga_refrigerante_kg = Column(Float)

    modelo = relationship("ModeloForcador", back_populates="fisicos")


class DadosDimensionaisForcador(Base):
    __tablename__ = "forcador_dimensionais"
    id = Column(Integer, primary_key=True)
    modelo_id = Column(Integer, ForeignKey("forcador_modelos.id"), nullable=False, index=True)
    comprimento_mm = Column(Float)
    largura_mm = Column(Float)
    altura_mm = Column(Float)
    num_fixacoes = Column(Integer)  # quase nunca vem do catálogo; preenchido manualmente quando disponível

    modelo = relationship("ModeloForcador", back_populates="dimensionais")



class ImportacaoCatalogo(Base):
    """Registro de cada importação de catálogo (PDF/imagem) com status de revisão/confirmação."""
    __tablename__ = "forcador_importacoes"
    id = Column(Integer, primary_key=True)
    linha_id = Column(Integer, ForeignKey("forcador_linhas.id"), nullable=True, index=True)
    nome_arquivo = Column(String)
    tipo_arquivo = Column(String)  # "pdf_nativo" | "pdf_escaneado" | "imagem"
    data_importacao = Column(DateTime, default=datetime.utcnow)
    confirmado_pelo_usuario = Column(Boolean, default=False)
    dados_extraidos_json = Column(Text)  # snapshot da extração antes da revisão
    observacao = Column(Text)


class FatorCorrecaoGasForcador(Base):
    """Fator de correção de capacidade por gás refrigerante, específico de cada linha (cada
    fabricante publica o seu). Multiplicado na capacidade corrigida do forçador:
    Capacidade corrigida = Tabela × correção de ΔT × fator do gás."""
    __tablename__ = "forcador_fatores_gas"
    id = Column(Integer, primary_key=True)
    linha_id = Column(Integer, ForeignKey("forcador_linhas.id"), nullable=False, index=True)
    gas = Column(String, nullable=False)  # ex.: "R-404A"
    fator = Column(Float, nullable=True)  # None = ainda não preenchido pelo usuário

    linha = relationship("LinhaForcador")

    __table_args__ = (UniqueConstraint("linha_id", "gas", name="uq_linha_gas"),)


# ===================== CONDENSADORES REMOTOS A AR (Tela C) =====================
# Espelho fiel do módulo Forçador (LinhaForcador/ModeloForcador), com as diferenças técnicas do
# produto condensador: capacidade é um VALOR ÚNICO por modelo (não tabela por temp. de evaporação),
# não há tabela elétrica separada (motor/corrente ficam na própria linha do modelo), e a correção
# de capacidade usa 5 fatores multiplicativos em cascata (FatorCorrecaoCondensador), não interpolação.

class LinhaCondensadorRemoto(Base):
    """Catálogo/linha de condensador remoto — nível equivalente a LinhaForcador. Tipo Estrutura
    (Plano/V) faz parte da unicidade: um mesmo catálogo físico com os dois tipos vira DUAS linhas
    separadas, cada uma com seu próprio texto/foto comercial (decisão do usuário 2026-07-19)."""
    __tablename__ = "condensador_linhas"
    id = Column(Integer, primary_key=True)
    fabricante_id = Column(Integer, ForeignKey("cat_fabricantes.id"), nullable=False, index=True)
    nome = Column(String, nullable=False)
    versao_catalogo = Column(String)
    tipo_estrutura = Column(String)  # "Plano (Fluxo Vertical)" | "V (Fluxo Horizontal)"
    dt_catalogo_c = Column(Float)  # ΔT de condensação de referência das capacidades do catálogo
    ativo_comercial = Column(Boolean, default=True)
    observacao_versao = Column(Text)
    linha_anterior_id = Column(Integer, ForeignKey("condensador_linhas.id"), nullable=True, index=True)
    descricao_comercial = Column(Text)  # texto único do catálogo (por tipo de estrutura)
    imagem_path = Column(Text)
    id_comercial = Column(String)  # auto-gerado, categoria 7 = Condensador Remoto (ver id_comercial.py)

    fabricante = relationship("Fabricante", back_populates="linhas_condensador")
    modelos = relationship("ModeloCondensadorRemoto", back_populates="linha", cascade="all, delete-orphan")
    fatores = relationship("FatorCorrecaoCondensador", back_populates="linha", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("fabricante_id", "nome", "versao_catalogo", "tipo_estrutura",
                                        name="uq_condensador_linha_versao"),)


class ModeloCondensadorRemoto(Base):
    """Modelo de condensador remoto — nível equivalente a ModeloForcador. Todos os dados técnicos
    (mecânica + elétrica + físico + dimensional) ficam achatados aqui: o catálogo de condensador
    não separa tabela elétrica (documento do usuário)."""
    __tablename__ = "condensador_modelos"
    id = Column(Integer, primary_key=True)
    linha_id = Column(Integer, ForeignKey("condensador_linhas.id"), nullable=False, index=True)
    modelo = Column(String, nullable=False)
    fpi = Column(Integer)  # aletas por polegada (filtro de seleção)
    qtd_ventiladores = Column(Integer)
    diametro_ventilador_mm = Column(Float)  # em branco se o catálogo do fabricante não publicar
    vazao_ar_m3h = Column(Float)
    polos_ou_rpm = Column(String)  # nº de polos (motor AC) ou rotação em RPM (motor EC)
    tipo_motor = Column(String)  # "AC" | "EC" (filtro de seleção)
    num_fileiras = Column(Integer)
    capacidade_kcal_h = Column(Float)  # capacidade única de catálogo (corrigida por 5 fatores no cálculo)
    potencia_kw = Column(Float)
    corrente_220v = Column(Float)
    corrente_380v = Column(Float)
    corrente_460v = Column(Float)
    ruido_db = Column(Float)  # nível de ruído a 10m (dBa)
    carga_refrigerante_kg = Column(Float)
    coletor_entrada_pol = Column(String)
    coletor_saida_pol = Column(String)
    peso_liquido_kg = Column(Float)
    peso_bruto_kg = Column(Float)
    comprimento_mm = Column(Float)
    largura_mm = Column(Float)
    altura_mm = Column(Float)
    num_fixacoes = Column(Integer)
    nomenclatura_compra = Column(Text)
    descricao_comercial = Column(Text)
    imagem_path = Column(Text)

    linha = relationship("LinhaCondensadorRemoto", back_populates="modelos")


class FatorCorrecaoCondensador(Base):
    """Fator de correção de capacidade do condensador, por linha. Tabela única com discriminador
    `tipo` (5 tipos): delta_condensacao | gas | aleta | altitude | temp_entrada_ar. A capacidade
    corrigida do condensador = capacidade de catálogo × produto de todos os fatores aplicáveis."""
    __tablename__ = "condensador_fatores"
    id = Column(Integer, primary_key=True)
    linha_id = Column(Integer, ForeignKey("condensador_linhas.id"), nullable=False, index=True)
    tipo = Column(String, nullable=False)  # delta_condensacao|gas|aleta|altitude|temp_entrada_ar
    chave = Column(String, nullable=False)  # ex.: "5" (delta), "R-404A" (gás), "Padrão" (aleta), "600"/"45" (faixa até)
    fator = Column(Float, nullable=True)  # None = ainda não preenchido

    linha = relationship("LinhaCondensadorRemoto", back_populates="fatores")

    __table_args__ = (UniqueConstraint("linha_id", "tipo", "chave", name="uq_condensador_fator"),)


class ImportacaoCondensador(Base):
    """Registro de cada importação de catálogo de condensador (histórico), espelho de ImportacaoCatalogo."""
    __tablename__ = "condensador_importacoes"
    id = Column(Integer, primary_key=True)
    linha_id = Column(Integer, ForeignKey("condensador_linhas.id"), nullable=True, index=True)
    nome_arquivo = Column(String)
    tipo_arquivo = Column(String)
    data_importacao = Column(DateTime, default=datetime.utcnow)
    confirmado_pelo_usuario = Column(Boolean, default=False)
    dados_extraidos_json = Column(Text)
    observacao = Column(Text)


# ===================== VÁLVULAS DE EXPANSÃO (catálogo) =====================

class ModeloValvula(Base):
    __tablename__ = "cat_modelos_valvula"
    id = Column(Integer, primary_key=True)
    fabricante_id = Column(Integer, ForeignKey("cat_fabricantes.id"), nullable=False, index=True)
    tipo_expansao = Column(String, nullable=False)  # Eletrônica / Direta / Fluído Secundário
    modelo = Column(String, nullable=False)
    capacidade_nominal_kcal_h = Column(Float, nullable=False)

    fabricante = relationship("Fabricante", back_populates="modelos_valvula")


# ===================== TELA A - TABELAS DE VÁLVULAS DE EXPANSÃO (Configurações) =====================
# Fonte: "Documentos de Criação/Tabela Válvulas de Expansão.xlsx". Informações MECÂNICAS por modelo
# — capacidade NÃO fica aqui (catálogos dos fabricantes são imprecisos; capacidade vem sempre do
# relatório de dimensionamento importado ou digitada manualmente). A matriz Sim/Não da planilha
# vira formato longo (uma linha por par válvula×controlador compatível) pra caber no CRUD genérico
# e aceitar novos fabricantes sem mudar schema. Modelos gravados como texto (Id comercial), sem FK
# — decisão explícita do usuário (árvore de Ids será reformulada depois, sem quebrar isto).

class TabelaValvulaExpansao(Base):
    __tablename__ = "tabela_valvula_expansao"
    id = Column(Integer, primary_key=True)
    fabricante = Column(String, nullable=False)       # Carel / FullGauge / Danfoss...
    tipo_expansao = Column(String, nullable=False)    # Eletrônica / Termostática
    modelo = Column(String, nullable=False)
    conexao_entrada = Column(String)
    conexao_saida = Column(String)
    tensao = Column(String)                           # ex.: "12 Vdc <> 10%" (FullGauge); vazio p/ Carel/Danfoss
    tipo_motor = Column(String)                       # Unipolar / Bipolar (só eletrônica)
    equalizacao = Column(String)                      # ex.: 1/4" (só termostática)
    gas_compativel = Column(String)                   # ex.: R22 / R407C / R134a / R404A/R507 (só Danfoss)


class TabelaControladorValvula(Base):
    __tablename__ = "tabela_controlador_valvula"
    id = Column(Integer, primary_key=True)
    fabricante = Column(String, nullable=False)       # Carel / FullGauge
    modelo = Column(String, nullable=False)
    tipo_expansao = Column(String, nullable=False)    # Eletrônica / Termostática (tipo de válvula que atende)
    classificacao = Column(String)                    # Universal / Alta-Média / Baixa (temp. de evaporação)
    observacao = Column(String)                       # ex.: nota do VX-1225 (2 forçadores/1 coletor etc.)


class TabelaCompatibilidadeValvula(Base):
    __tablename__ = "tabela_compatibilidade_valvula"
    id = Column(Integer, primary_key=True)
    valvula_modelo = Column(String, nullable=False)
    controlador_modelo = Column(String, nullable=False)


# ===================== CÂMARA — CÁLCULO COMPLETO =====================

class CamaraCompleto(Base):
    __tablename__ = "camaras_completo"
    id = Column(Integer, primary_key=True)
    sistema_id = Column(Integer, ForeignKey("sistemas_refrigeracao.id"), nullable=False, index=True)
    nome = Column(String, nullable=False)
    linha_succao = Column(String)
    linha_eletrica = Column(String)
    temp_interna = Column(Float)
    largura = Column(Float)
    comprimento = Column(Float)
    pedireito = Column(Float)

    # Válvula Reguladora de Pressão (Temperatura de Saturação controlada) — só aparece na tela
    # quando o Δt de evaporação calculado da câmara (temp_interna - sistema.temp_evaporacao) é
    # > 10°C. Se "Sim", dt_evaporacao_desejado (4 a 10°C) substitui — SÓ PRA ESSA CÂMARA — a
    # Temp. Evaporação e o Δt usados no dimensionamento do forçador: Temp.Evap virtual =
    # temp_interna - dt_evaporacao_desejado (ver calc_service.py). Nunca afeta outras câmaras do
    # mesmo Sistema, que continuam usando a Temp. Evaporação real do Sistema (Tela 1).
    utilizar_valv_reg_pressao = Column(String)  # "Sim" | "Não" | None
    dt_evaporacao_desejado = Column(Float)

    # Seção 1 — Calor de Produto
    produto_id = Column(Integer, ForeignKey("cat_produtos.id"), nullable=True, index=True)
    qtd_estocada = Column(Float, default=0)
    mov_diaria = Column(Float, default=0)
    tempo_processo = Column(Float)
    temp_entrada = Column(Float)
    temp_saida = Column(Float)

    # Seção 2 — Embalagem
    tipo_embalagem_id = Column(Integer, ForeignKey("cat_tipos_embalagem.id"), nullable=True, index=True)
    massa_embalagem = Column(Float, default=0)

    # Seção 3 — Penetração
    isolamento_parede_id = Column(Integer, ForeignKey("cat_isolamento_parede_teto.id"), nullable=True, index=True)
    isolamento_teto_id = Column(Integer, ForeignKey("cat_isolamento_parede_teto.id"), nullable=True, index=True)
    isolamento_piso_id = Column(Integer, ForeignKey("cat_isolamento_piso.id"), nullable=True, index=True)

    # Seção 4 — Infiltração
    num_portas = Column(Integer, default=0)
    porta_largura = Column(Float)
    porta_altura = Column(Float)
    freq_abertura_min_h = Column(Float)  # minutos de porta aberta por hora
    protecao_porta = Column(String, default="Nenhuma")
    # Fonte do ar que entra/troca com a câmara (usado na infiltração Q4 e na penetração Q3
    # parede/teto). "Externo" = ar externo do projeto (temp_ambiente/ur_externa); "Adjacente" =
    # ambiente vizinho (ex.: galpão interno não climatizado, ou sala climatizada), com temperatura
    # e umidade próprias abaixo. Default "Externo" preserva o comportamento anterior.
    fonte_ar = Column(String, default="Externo")  # "Externo" | "Adjacente"
    temp_adjacente = Column(Float, default=25)     # usado só quando fonte_ar = "Adjacente"
    umidade_adjacente = Column(Float, default=60)  # UR % do ambiente adjacente

    # Seção 5 — Pessoas
    num_pessoas = Column(Integer, default=0)
    tempo_pessoas = Column(Float, default=0)

    # Seção 6 — Iluminação
    qtd_luminarias = Column(Integer, default=0)
    # potencia_luminaria: campo LEGADO — só usado como fallback quando potencia_luminaria_texto está
    # em branco (câmara antiga, cadastrada antes do Estudo Luminotécnico, aprovado 2026-08-08). Nunca
    # recalculado/sobrescrito automaticamente — só muda se o usuário escolher uma Potência
    # manualmente. Q6 continua Qtd x Potência x Horas, sem mudança de fórmula.
    potencia_luminaria = Column(Float, default=0)
    tipo_ambiente_lumino_id = Column(Integer, ForeignKey("lookup_ambiente_luminotecnico.id"), nullable=True, index=True)
    # modelo_luminaria_id: LEGADO, coluna mantida no banco sem uso — substituída pelas 2 abaixo
    # (aprovado 2026-08-08: Potência e Modelo viram seleções em cascata na árvore "1.4", em vez de
    # 1 FK só pra um cadastro à parte).
    modelo_luminaria_id = Column(Integer, ForeignKey("lookup_lampada.id"), nullable=True, index=True)
    # Texto EXATO do nó da árvore escolhido (ex.: "36W", filho direto de "1.4"). É a partir daqui
    # que o Fluxo Luminoso é buscado em "Cadastro Lâmpadas" (extrai o número e casa com Potência (W)).
    potencia_luminaria_texto = Column(String)
    # Texto EXATO do nó-filho da Potência escolhida (ex.: "LED HERMÉTICA 36W") — cascata, informativo/Id.
    modelo_luminaria_texto = Column(String)
    # Horas de iluminação/dia usadas no CÁLCULO DA CARGA (Q6). Default 24 preserva a premissa
    # conservadora anterior. Independente do horas_iluminacao_dia por SISTEMA (Consumo/Tela 7),
    # que não pode ser unificado por causa da Câmara Simples e do Expositor.
    horas_iluminacao_carga = Column(Float, default=24)

    # Parâmetros de dimensionamento
    fator_seguranca = Column(Float, default=10)
    tempo_func_compressores = Column(Float, default=18)
    # qtd_evaporadores removido (2026-07-03) — cada linha de forçador (ForcadorSelecaoCompleto/
    # Simples.quantidade) já controla quantas unidades daquele modelo, sem multiplicador
    # duplicado no nível da câmara.

    # Snapshot do último cálculo (Q1-Q9 + forçador/UC selecionados + tudo que veio do catálogo)
    # gravado no momento em que a câmara é calculada — permite abrir/visualizar/exportar o projeto
    # sem depender do catálogo remoto (sem internet ou assinatura vencida). Só um recálculo de
    # verdade (usuário editando algo que alimenta o cálculo) exige catálogo/assinatura ativos.
    calculo_snapshot_json = Column(Text)
    calculo_desatualizado = Column(Boolean, default=True)
    fechada = Column(Boolean, default=False)

    sistema = relationship("SistemaRefrigeracao", back_populates="camaras_completo")
    produto = relationship("Produto")
    tipo_embalagem = relationship("TipoEmbalagem")
    isolamento_parede = relationship("IsolamentoParedeTeto", foreign_keys=[isolamento_parede_id])
    isolamento_teto = relationship("IsolamentoParedeTeto", foreign_keys=[isolamento_teto_id])
    isolamento_piso = relationship("IsolamentoPiso")
    tipo_ambiente_lumino = relationship("LookupAmbienteLuminotecnico")
    modelo_luminaria = relationship("LookupLampada")
    equipamentos = relationship("EquipamentoCamaraCompleto", cascade="all, delete-orphan")
    forcadores = relationship("ForcadorSelecaoCompleto", cascade="all, delete-orphan", order_by="ForcadorSelecaoCompleto.id")
    portas = relationship("PortaCamara", cascade="all, delete-orphan", order_by="PortaCamara.ordem")


class PortaCamara(Base):
    """Uma porta (ou tipo de porta) da câmara para o cálculo de infiltração (Q4). Cada porta tem
    sua própria fonte de ar (Externo/Adjacente) — uma pode dar para fora, outra para o galpão
    interno — e o Q4 total da câmara é a SOMA da infiltração de todas as portas. Os campos antigos
    de porta única em CamaraCompleto (num_portas/porta_largura/...) ficaram legados após a migração."""
    __tablename__ = "camara_completo_portas"
    id = Column(Integer, primary_key=True)
    camara_id = Column(Integer, ForeignKey("camaras_completo.id"), nullable=False, index=True)
    quantidade = Column(Integer, default=1)
    largura = Column(Float)
    altura = Column(Float)
    freq_abertura_min_h = Column(Float)  # minutos aberta por hora
    protecao = Column(String, default="Nenhuma")
    fonte_ar = Column(String, default="Externo")  # "Externo" | "Adjacente"
    temp_adjacente = Column(Float, default=25)
    umidade_adjacente = Column(Float, default=60)
    ordem = Column(Integer, default=0)


class EquipamentoCamaraCompleto(Base):
    __tablename__ = "camara_completo_equipamentos"
    id = Column(Integer, primary_key=True)
    camara_id = Column(Integer, ForeignKey("camaras_completo.id"), nullable=False, index=True)
    tipo_equipamento_id = Column(Integer, ForeignKey("cat_tipos_equipamento.id"), nullable=False, index=True)
    qtd = Column(Integer, default=1)
    tempo = Column(Float, default=0)

    tipo_equipamento = relationship("TipoEquipamento")


class ForcadorSelecaoCompleto(Base):
    __tablename__ = "camara_completo_forcadores"
    id = Column(Integer, primary_key=True)
    camara_id = Column(Integer, ForeignKey("camaras_completo.id"), nullable=False, index=True)
    fabricante_id = Column(Integer, ForeignKey("cat_fabricantes.id"), nullable=False, index=True)
    linha_id = Column(Integer, ForeignKey("forcador_linhas.id"), nullable=False, index=True)
    folga_desejada = Column(Float, default=10)
    considerado = Column(Boolean, default=False)
    quantidade = Column(Integer, default=1)  # nº de unidades do modelo escolhido nessa linha
    tipo_degelo = Column(String)  # Natural | Elétrico | Gás quente — escolhido pelo usuário
    nomenclatura_selecionada = Column(Text)  # JSON {nome_campo: valor_escolhido} — código comercial
    # Código curto (F1, F2...) — identifica a opção de forçador nos relatórios externos de
    # dimensionamento de válvula (Coolselector2/VEE Selector/CPQ), somado ao código da câmara.
    codigo_curto = Column(String)

    fabricante = relationship("Fabricante")
    linha = relationship("LinhaForcador")
    valvulas = relationship("ValvulaSelecaoCompleto", back_populates="forcador_selecao",
                             cascade="all, delete-orphan", order_by="ValvulaSelecaoCompleto.id")


class ValvulaSelecaoCompleto(Base):
    __tablename__ = "camara_completo_valvulas"
    id = Column(Integer, primary_key=True)
    forcador_selecao_id = Column(Integer, ForeignKey("camara_completo_forcadores.id"), nullable=False, index=True)
    # Danfoss/Fullgauge/Carel — mesma lista fixa da Automação (Tela 1), não é o catálogo técnico de
    # forçador (cat_fabricantes). Válvula não tem catálogo de capacidade próprio no sistema.
    fabricante = Column(String, nullable=False)
    tipo_expansao = Column(String, nullable=False)
    # Resultado trazido do app de dimensionamento do fabricante (Coolselector2/VEE Selector/CPQ).
    # modelo_selecao grava o Id COMERCIAL do produto (assim como orificio e controlador).
    modelo_selecao = Column(String)
    carga_abertura_pct = Column(Float)   # Abert. Válv. = (Carga Térmica ÷ Qtd. Coletores) ÷ Capacidade Unit.
    conexao_entrada = Column(String)
    conexao_saida = Column(String)
    folga_desejada = Column(Float, default=10)
    considerado = Column(Boolean, default=False)
    # Campos por tipo (Tela 1 §3): capacidade/orifício vêm SEMPRE do relatório importado ou de
    # digitação manual (nunca do banco — catálogos imprecisos); mecânica (tensão/tipo motor/conexões)
    # pode ser completada pela Tabela de Válvulas de Expansão; controlador é seleção manual.
    capacidade_unit_kcal_h = Column(Float)
    orificio = Column(String)            # Id comercial (só termostática)
    tensao = Column(String)              # só eletrônica
    tipo_motor = Column(String)          # Unipolar / Bipolar (só eletrônica)
    controlador = Column(String)         # Id comercial do controlador/driver

    forcador_selecao = relationship("ForcadorSelecaoCompleto", back_populates="valvulas")


# ===================== CÂMARA — CÁLCULO SIMPLES =====================

class CamaraSimples(Base):
    __tablename__ = "camaras_simples"
    id = Column(Integer, primary_key=True)
    sistema_id = Column(Integer, ForeignKey("sistemas_refrigeracao.id"), nullable=False, index=True)
    nome = Column(String, nullable=False)
    linha_succao = Column(String)
    linha_eletrica = Column(String)
    tabela02_id = Column(Integer, ForeignKey("cat_tabela_tipo02.id"), nullable=True, index=True)
    # Largura/Comprimento (novos, aprovado 2026-08-08 — Estudo Luminotécnico precisa dos 2
    # separados pro Índice do Ambiente, não só a Área). `area` continua existindo e é a fonte usada
    # pelo cálculo de carga térmica (Q1..Q7 simplificado) — passa a ser AUTOCALCULADA
    # (largura x comprimento) sempre que os 2 estiverem preenchidos; câmaras antigas (só com area
    # manual, sem largura/comprimento) mantêm o valor como está.
    largura = Column(Float)
    comprimento = Column(Float)
    area = Column(Float)
    pedireito = Column(Float)
    temp_interna = Column(Float)

    # Seção Iluminação (Estudo Luminotécnico) — mesmos campos da Câmara Completo, ver lá o
    # comentário completo. Câmara Simples nunca teve potência de iluminação manual antes (usava só
    # os 3 configs globais, agora aposentados) — não precisa de campo de fallback legado.
    qtd_luminarias = Column(Integer, default=0)
    tipo_ambiente_lumino_id = Column(Integer, ForeignKey("lookup_ambiente_luminotecnico.id"), nullable=True, index=True)
    # modelo_luminaria_id: LEGADO, coluna mantida sem uso — ver comentário completo na CamaraCompleto.
    modelo_luminaria_id = Column(Integer, ForeignKey("lookup_lampada.id"), nullable=True, index=True)
    potencia_luminaria_texto = Column(String)
    modelo_luminaria_texto = Column(String)
    horas_iluminacao_carga = Column(Float, default=24)

    # Válvula Reguladora de Pressão — mesma regra/efeito da CamaraCompleto (ver lá o comentário
    # completo); isolado por câmara, nunca afeta outras câmaras do Sistema.
    utilizar_valv_reg_pressao = Column(String)  # "Sim" | "Não" | None
    dt_evaporacao_desejado = Column(Float)

    fator_seguranca = Column(Float, default=10)
    tempo_func_compressores = Column(Float, default=18)
    # qtd_evaporadores removido (2026-07-03) — cada linha de forçador (ForcadorSelecaoCompleto/
    # Simples.quantidade) já controla quantas unidades daquele modelo, sem multiplicador
    # duplicado no nível da câmara.

    # Vão de porta — só para gerar a carga elétrica de Res. Portas na Tela 5 (Compilação); NÃO
    # entra na carga térmica do cálculo simplificado (infiltração não faz parte dessa fórmula).
    num_portas = Column(Integer, default=0)
    porta_largura = Column(Float)
    porta_altura = Column(Float)

    # Snapshot do último cálculo — ver comentário completo em CamaraCompleto.
    calculo_snapshot_json = Column(Text)
    calculo_desatualizado = Column(Boolean, default=True)
    fechada = Column(Boolean, default=False)

    sistema = relationship("SistemaRefrigeracao", back_populates="camaras_simples")
    tabela02 = relationship("TabelaTipo02")
    tipo_ambiente_lumino = relationship("LookupAmbienteLuminotecnico")
    modelo_luminaria = relationship("LookupLampada")
    forcadores = relationship("ForcadorSelecaoSimples", cascade="all, delete-orphan", order_by="ForcadorSelecaoSimples.id")


class ForcadorSelecaoSimples(Base):
    __tablename__ = "camara_simples_forcadores"
    id = Column(Integer, primary_key=True)
    camara_id = Column(Integer, ForeignKey("camaras_simples.id"), nullable=False, index=True)
    fabricante_id = Column(Integer, ForeignKey("cat_fabricantes.id"), nullable=False, index=True)
    linha_id = Column(Integer, ForeignKey("forcador_linhas.id"), nullable=False, index=True)
    folga_desejada = Column(Float, default=10)
    considerado = Column(Boolean, default=False)
    quantidade = Column(Integer, default=1)  # nº de unidades do modelo escolhido nessa linha
    tipo_degelo = Column(String)  # Natural | Elétrico | Gás quente — escolhido pelo usuário
    nomenclatura_selecionada = Column(Text)  # JSON {nome_campo: valor_escolhido} — código comercial
    codigo_curto = Column(String)

    fabricante = relationship("Fabricante")
    linha = relationship("LinhaForcador")
    valvulas = relationship("ValvulaSelecaoSimples", back_populates="forcador_selecao",
                             cascade="all, delete-orphan", order_by="ValvulaSelecaoSimples.id")


class ValvulaSelecaoSimples(Base):
    __tablename__ = "camara_simples_valvulas"
    id = Column(Integer, primary_key=True)
    forcador_selecao_id = Column(Integer, ForeignKey("camara_simples_forcadores.id"), nullable=False, index=True)
    fabricante = Column(String, nullable=False)
    tipo_expansao = Column(String, nullable=False)
    modelo_selecao = Column(String)
    carga_abertura_pct = Column(Float)
    conexao_entrada = Column(String)
    conexao_saida = Column(String)
    folga_desejada = Column(Float, default=10)
    considerado = Column(Boolean, default=False)
    # Mesmos campos novos da ValvulaSelecaoCompleto (ver comentário lá) — manter os dois em sincronia.
    capacidade_unit_kcal_h = Column(Float)
    orificio = Column(String)
    tensao = Column(String)
    tipo_motor = Column(String)
    controlador = Column(String)

    forcador_selecao = relationship("ForcadorSelecaoSimples", back_populates="valvulas")


# ===================== EXPOSITOR =====================

class Expositor(Base):
    __tablename__ = "expositores"
    id = Column(Integer, primary_key=True)
    sistema_id = Column(Integer, ForeignKey("sistemas_refrigeracao.id"), nullable=False, index=True)
    nome = Column(String)  # opcional, default = nome do modelo
    linha_succao = Column(String)
    linha_eletrica = Column(String)
    setor_id = Column(Integer, ForeignKey("cat_setores_expositor.id"), nullable=True, index=True)
    modelo_expositor_id = Column(Integer, ForeignKey("cat_modelos_expositor.id"), nullable=True, index=True)
    fechada = Column(Boolean, default=False)
    calculo_snapshot_json = Column(Text)

    sistema = relationship("SistemaRefrigeracao", back_populates="expositores")
    setor = relationship("SetorExpositor")
    modelo_expositor = relationship("ModeloExpositor")
    modulos = relationship("ModuloExpositor", cascade="all, delete-orphan")


class ModuloExpositor(Base):
    __tablename__ = "expositor_modulos"
    id = Column(Integer, primary_key=True)
    expositor_id = Column(Integer, ForeignKey("expositores.id"), nullable=False, index=True)
    comprimento_modulo = Column(Float, nullable=False)
    qtd = Column(Integer, default=1)


# ===================== TELA B — UNIDADES CONDENSADORAS COMERCIAIS =====================

class CatalogoUC(Base):
    """Catálogo de Unidades Condensadoras (mesmo papel do LinhaForcador pros forçadores): agrupa
    as unidades de um documento/versão de catálogo do fabricante, com nome PRÓPRIO editável — a
    dupla (Fabricante, Versão) sozinha não diferencia catálogos distintos publicados na mesma data
    (ex.: Elgin publica vários catálogos "02/2025" pra faixas de HP diferentes)."""
    __tablename__ = "uc_catalogos"
    id = Column(Integer, primary_key=True)
    fabricante_uc = Column(String, nullable=False)       # Elgin, Danfoss, Tecumseh, Bitzer...
    nome = Column(String, nullable=False)                # ex.: "US 10 a 66HP - 2 e 3 Compressores"
    versao_catalogo = Column(String)
    descricao_comercial = Column(Text)                   # texto único do catálogo inteiro, não por modelo
    imagem_path = Column(Text)                             # foto do equipamento, uma por catálogo (base64 data URI)
    ativo_comercial = Column(Boolean, default=True)  # False = obsoleto (só uso técnico/reformas), mesmo padrão de LinhaForcador
    # Id comercial auto-gerado na criação (categoria 2.1 = Unidade Condensadora Comercial),
    # formato "2.1.<fabricante>.<catalogo>" — ver id_comercial.py. Fixo, não recalcula depois.
    id_comercial = Column(String)

    unidades = relationship("UnidadeCondensadora", back_populates="catalogo", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("fabricante_uc", "nome", "versao_catalogo", name="uq_catalogo_uc"),)


class UnidadeCondensadora(Base):
    """Catálogo de Unidade Condensadora Comercial (uma linha por modelo × gás — orientação #11:
    equipamento que atende vários gases é duplicado, um cadastro por gás, pra evitar conflito).
    Capacidade depende de temp. ambiente E temp. de evaporação (ver CapacidadeUC)."""
    __tablename__ = "uc_unidades"
    id = Column(Integer, primary_key=True)
    catalogo_id = Column(Integer, ForeignKey("uc_catalogos.id"), nullable=False, index=True)
    modelo = Column(String, nullable=False)              # código base, ex.: U*HMB4250
    sistema = Column(String)                             # Alta | Média | Baixa | Média e Baixa
    gas = Column(String)                                 # R-404a, R-507c, R-134a...
    tipo_compressor = Column(String)                     # Hermético | Semi-Hermético | Scroll | Duplo-Estágio | Parafuso
    fabricante_compressor = Column(String)               # Bitzer | Dorin | Copeland | Danfoss | Elgin | Lunite
    numero_compressores = Column(Integer)                # qtd de compressores da unidade — usado no cálculo de consumo (Tela D)
    hp = Column(Float)

    # ---- Elétrica: NÃO fica aqui — varia por Tensão E por Modelo de Compressor (catálogo real
    # mostra o mesmo Modelo+Tensão com mais de uma opção de compressor, cada uma com corrente
    # própria). Ver EletricaUC. ----

    vent_qtd = Column(Integer)                            # qtd de ventiladores — não varia por tensão, fica aqui

    # ---- Conexões ----
    conexao_liquido = Column(String)
    conexao_succao = Column(String)

    tanque_liquido_l = Column(Float)
    nivel_ruido_db = Column(Float)                        # 5m
    ventilador_diametro_mm = Column(Float)

    # ---- Dimensões e peso ----
    comprimento_mm = Column(Float)
    largura_mm = Column(Float)
    altura_mm = Column(Float)
    peso_liquido_kg = Column(Float)
    peso_bruto_kg = Column(Float)

    nomenclatura_compra = Column(Text)

    catalogo = relationship("CatalogoUC", back_populates="unidades")
    capacidades = relationship("CapacidadeUC", back_populates="unidade", cascade="all, delete-orphan")
    eletricas = relationship("EletricaUC", back_populates="unidade", cascade="all, delete-orphan")


class EletricaUC(Base):
    """Elétrica da UC — varia por Tensão E por Modelo de Compressor (confirmado no catálogo real:
    o mesmo Modelo+Tensão pode ter mais de uma opção de compressor, cada uma com MCC/RLA/LRA
    própria — ex.: U*HMB4120J*D2 com H5O5CC ou H7O5CC). Físico/Dimensional NÃO entra aqui: não
    varia por tensão nem por compressor no catálogo real, fica escalar em UnidadeCondensadora."""
    __tablename__ = "uc_eletricas"
    id = Column(Integer, primary_key=True)
    unidade_id = Column(Integer, ForeignKey("uc_unidades.id"), nullable=False, index=True)
    tensao = Column(String)
    fases = Column(Integer)
    frequencia = Column(String)
    modelo_compressor = Column(String)                   # ex.: 4HE-25Y-35P — varia por tensão
    mcc_a = Column(Float)                                 # Corrente Máx. de Operação (IEC) — usada em cálculos
    rla_a = Column(Float)                                 # Corrente nominal — usada em cálculos
    lra_a = Column(Float)                                 # Corrente de rotor bloqueado
    vent_tensao = Column(String)
    vent_fases = Column(Integer)
    vent_frequencia = Column(String)
    vent_corrente_a = Column(Float)

    unidade = relationship("UnidadeCondensadora", back_populates="eletricas")


class CapacidadeUC(Base):
    """Capacidade (Q, kcal/h) e potência consumida (P, kW) da UC para cada combinação
    temp. ambiente × temp. evaporação tabelada no catálogo. Orientação #6: na seleção, busca
    sempre a linha Q dentro da temp. ambiente da instalação."""
    __tablename__ = "uc_capacidades"
    id = Column(Integer, primary_key=True)
    unidade_id = Column(Integer, ForeignKey("uc_unidades.id"), nullable=False, index=True)
    temp_ambiente_c = Column(Float, nullable=False)
    temp_evaporacao_c = Column(Float, nullable=False)
    capacidade_kcal_h = Column(Float)                    # Q
    potencia_kw = Column(Float)                          # P

    unidade = relationship("UnidadeCondensadora", back_populates="capacidades")


class CampoCatalogo(Base):
    """Estrutura configurável do código comercial de um catálogo — único mecanismo de nomenclatura
    vigente no sistema (a antiga NomenclaturaUC/categoria foi removida por não ter consumidor real).
    Cada catálogo (UC ou Forçador) define sua PRÓPRIA lista ordenada de Campos, porque fabricantes
    diferentes usam estruturas de código completamente diferentes (orientação repetida do usuário:
    "cada fabricante tem seu padrão" — não dá pra fixar uma ordem só, tipo Elgin, pra todo mundo).

    tipo_catalogo + catalogo_id: aponta pra uc_catalogos.id (tipo_catalogo="UC") ou
    forcador_linhas.id (tipo_catalogo="Forcador") — não é FK de verdade porque são 2 tabelas-alvo
    diferentes; a leitura sempre filtra por tipo_catalogo primeiro.

    modo:
      automatico -> pega o valor do campo_busca_sistema (ex.: "tensao", "gas") já resolvido em outro
                    lugar do app, compara com as CampoCatalogoOpcao deste Campo e usa o código achado.
      fixo       -> usa direto codigo_fixo, sempre, sem comparar nada.
      manual     -> mostra uma caixa de seleção na tela de cadastro/seleção com as CampoCatalogoOpcao
                    deste Campo, pro usuário escolher.
      ignorar    -> aparece no meio da nomenclatura (Tela 2/3/1), não editável, e não entra no
                    código comercial — não concatena nada, pula pro próximo campo.
      modelo_pesquisa -> card especial (no máximo 1 por catálogo): valor = o próprio código do
                    modelo técnico selecionado (ex.: "0062", "FL*017"), NÃO editável pelo usuário —
                    só a posição dele na nomenclatura é livre (arrasta como qualquer outro card).
                    Se esse valor tiver um coringa '*', o Campo marcado substitui_coringa_modelo
                    entra nessa posição; sem coringa, cada card simplesmente concatena na ordem
                    cadastrada (padrão único do sistema, ver montar_codigo em campo_catalogo.py —
                    nunca resolver isso por fabricante/linha, sempre pelo motor genérico).
    """
    __tablename__ = "campo_catalogo"
    id = Column(Integer, primary_key=True)
    tipo_catalogo = Column(String, nullable=False)   # "UC" | "Forcador" | "CondensadorRemoto"
    catalogo_id = Column(Integer, nullable=False)
    ordem = Column(Integer, nullable=False, default=0)
    nome_campo = Column(String, nullable=False)             # ex.: "Tensão", "Opcional Elétrico"
    modo = Column(String, nullable=False, default="manual")  # "automatico"|"fixo"|"manual"|"ignorar"|"modelo_pesquisa"
    campo_busca_sistema = Column(String)   # só se modo=automatico — ex.: "tensao","gas","fabricante_compressor"
    codigo_fixo = Column(String)           # só se modo=fixo
    # Alguns fabricantes (ex.: Elgin) usam um coringa "*" dentro do próprio código do modelo (ex.:
    # "U*HMB4660") que é substituído pelo código deste Campo, em vez de ser concatenado no final —
    # normalmente o campo de Fluxo de Ar. Só um Campo por catálogo deve marcar isso.
    substitui_coringa_modelo = Column(Boolean, default=False)

    opcoes = relationship("CampoCatalogoOpcao", back_populates="campo", cascade="all, delete-orphan",
                           order_by="CampoCatalogoOpcao.ordem")


class CampoCatalogoOpcao(Base):
    """Valor -> Código de um CampoCatalogo — usado tanto no modo Manual (lista pro usuário escolher)
    quanto no modo Automático (comparação contra o valor resolvido do campo_busca_sistema)."""
    __tablename__ = "campo_catalogo_opcao"
    id = Column(Integer, primary_key=True)
    campo_id = Column(Integer, ForeignKey("campo_catalogo.id"), nullable=False, index=True)
    valor = Column(String, nullable=False)
    codigo = Column(String, nullable=False)
    ordem = Column(Integer, default=0)

    campo = relationship("CampoCatalogo", back_populates="opcoes")


class UnidadeSelecaoSistema(Base):
    """Seleção de UC por Sistema (não por câmara). Até 5 opções, regula por % de folga, igual ao
    forçador. A capacidade é comparada contra o total agrupado do sistema (Tela 5).

    Campos flutuantes (Fluxo de Ar, Linha de Líquido, Versão, Opcionais) não vêm do catálogo — são
    escolha do usuário só neste momento de seleção/compra, e compõem o código comercial completo
    (diferente do código técnico de busca, que carrega '*' nesses campos)."""
    __tablename__ = "uc_selecao_sistema"
    id = Column(Integer, primary_key=True)
    sistema_id = Column(Integer, ForeignKey("sistemas_refrigeracao.id"), nullable=False, index=True)
    fabricante_uc = Column(String)
    # Linha/catálogo do fabricante (UnidadeCondensadora.catalogo_id) — 2º filtro da cadeia
    # Fabricante UC > Linha > Tipo Compressor > Fabricante Compressor > Nº Compressores > Faixa.
    catalogo_id = Column(Integer, ForeignKey("uc_catalogos.id"), index=True)
    tipo_compressor = Column(String)
    fabricante_compressor = Column(String)
    # Número de compressores da unidade (UnidadeCondensadora.numero_compressores) — filtro entre
    # Fabricante Compressor e Faixa de Operação na cadeia acima.
    numero_compressores = Column(Integer)
    # Faixa de operação do catálogo (UnidadeCondensadora.sistema — ex.: "Baixa", "Média e Baixa").
    # Algumas unidades atendem mais de uma faixa; este filtro permite forçar uma unidade EXCLUSIVA
    # de Baixa mesmo quando existe opção compatível com Média e Baixa também.
    faixa_operacao = Column(String)
    folga_desejada = Column(Float, default=10)
    considerado = Column(Boolean, default=False)
    # Nº de unidades IDÊNTICAS em paralelo dividindo a demanda do sistema (aprovado 2026-08-13).
    # Default 1 = comportamento anterior (1 equipamento). Seleção/folga são calculadas sobre
    # carga_total ÷ quantidade_paralelo; totais (potência, disjuntor, BOM) multiplicam por N.
    quantidade_paralelo = Column(Integer, default=1)

    # ---- campos flutuantes (seleção do usuário, não fazem parte do catálogo importado) ----
    # Colunas fixas legadas — mantidas só pra não perder dado já gravado; o motor genérico de
    # código (ver campo_catalogo.py) não lê mais daqui, lê de campos_selecionados.
    fluxo_ar = Column(String)             # ex.: "Horizontal" | "Vertical"
    linha_liquido = Column(String)        # opcional comercial
    versao = Column(String)               # opcional comercial
    opcional_mecanico = Column(String)    # opcional comercial
    opcional_eletrico = Column(String)    # opcional comercial
    # JSON {nome_campo: valor_escolhido} — genérico, quantos campos manuais o catálogo tiver
    # (ver models.CampoCatalogo). Substitui as 5 colunas fixas acima pra permitir catálogos com
    # estrutura de código diferente da Elgin.
    campos_selecionados = Column(Text)
    fechada = Column(Boolean, default=False)
    calculo_snapshot_json = Column(Text)


# ===================== TELA E — PAINÉIS TÉRMICOS E PORTAS =====================

class LookupPainelPorta(Base):
    """Listas editáveis de Painéis/Portas (categoria/valor), tudo numa aba única de Configurações.
    'grupo' só é usado nas categorias Modelo Porta e Sentido
    Porta — indica a qual Função esse valor pertence, pra filtrar a caixa de seleção conforme a
    Função escolhida (nunca mostrar Modelo/Sentido de outra Função)."""
    __tablename__ = "paineis_portas_lookup"
    id = Column(Integer, primary_key=True)
    categoria = Column(String, nullable=False)
    # categorias: "Tipo Painel" | "Espessura Parede/Teto" | "Espessura Piso" | "Função Porta" |
    # "Modelo Porta" | "Sentido Porta" | "Fixação Porta" | "Tensão Porta"
    valor = Column(String, nullable=False)
    grupo = Column(String)   # Função Porta a que esse Modelo/Sentido pertence (quando aplicável)
    ordem = Column(Integer, default=0)
    descricao_inicial = Column(String)  # só Modelo Porta: texto inicial da descrição composta (Tela 7)
    prefixo_id = Column(String)         # só Modelo Porta: prefixo do Id da porta (PRC/PFE/... definido pelo usuário)
    # só Tipo Painel/Modelo Porta: código da árvore de Ids Comerciais (ver id_comercial.py, categoria
    # "8 Painéis") — escolhido pelo usuário na tela, liga esse valor à ficha comercial (CatalogoComercial)
    # correspondente, pra montar_memorial_projeto() conseguir puxar Painéis/Portas automaticamente.
    id_comercial = Column(String)


class CatalogoComercial(Base):
    """Ficha comercial (texto + foto), unificada por categoria — Painel Térmico, Porta
    Frigorífica, Válvula de Expansão, Supervisório e outras que surgirem. Cadastro direto na
    tela, sem importação — insumo para os relatórios de memorial/proposta gerados depois."""
    __tablename__ = "catalogo_comercial"
    id = Column(Integer, primary_key=True)
    categoria = Column(String, nullable=False)
    fabricante = Column(String)
    modelo = Column(String)
    nome = Column(String, nullable=False)
    descricao_comercial = Column(Text)
    imagem_path = Column(Text)
    # Código hierárquico (ver id_comercial.py) que liga esse item a um campo/opção específica do
    # app (ex.: "1.1.2" = Elétrica > Tipo de Comando > Quadro de Linhas) — usado pra montar
    # memorial/proposta automaticamente a partir das seleções do projeto. Não é FK de verdade
    # porque IdComercial é só a definição da árvore, não um cadastro obrigatório 1:1.
    id_comercial = Column(String)
    # "{id_comercial}-{sequencial}" — sequencial exclusivo daquele id_comercial, nunca reaproveitado
    # (maior já usado +1, mesmo se algum cadastro daquele id_comercial for excluído). Regenerado
    # toda vez que o Id Comercial salvo muda pra um valor diferente do que gerou o id_cadastro
    # atual (ver routers/catalogo_comercial.py atualizar — corrige cadastro feito com Id Comercial
    # errado, aprovado 2026-08-06); não é usado como chave de busca em nenhuma outra tabela.
    id_cadastro = Column(String)


class IdComercial(Base):
    """Árvore de Ids de organização dos textos comerciais (ver "Instruções de Id para
    Organização dos textos comerciais.docx") — cada linha é um nó (categoria OU item final),
    identificado pelo próprio código hierárquico (ex.: "2.2.1.1"), sem FK de pai — a hierarquia
    é lida direto do código (separado por ".").  Editável em Configurações."""
    __tablename__ = "id_comercial"
    id = Column(Integer, primary_key=True)
    codigo = Column(String, nullable=False, unique=True)
    nome = Column(String, nullable=False)
    ordem = Column(Integer, default=0)
    # Só usados em nós FOLHA (item final, sem filho) — categorias ficam com esses 3 em branco.
    campo_id = Column(String, nullable=True)  # referência ao CampoSistema.campo_id (ex.: "T13") — de onde o valor deste item vem
    centro_custo_padrao_codigo = Column(String, nullable=True)  # código de Centro de Custo (casa por código no projeto, mesmo padrão de ItemComposicaoMestre)
    fator_venda_padrao_id = Column(Integer, ForeignKey("fator_venda.id"), nullable=True, index=True)
    # True = nó criado automaticamente por um catálogo próprio (Forçador/UC/Condensador — ver
    # id_comercial.gerar_proximo_id_catalogo — ou Modelo do Catálogo Comercial — ver
    # resolver_no_modelo), nunca digitado à mão. Campo (Id) não faz sentido nesses nós (o valor vem
    # de escolher aquele produto específico noutra tela, não de um campo de formulário simples) —
    # usado só pra desabilitar essa coluna na tela de Configurações (aprovado 2026-08-06).
    origem_automatica = Column(Boolean, default=False)

    fator_venda_padrao = relationship("FatorVenda")


class CampoSistema(Base):
    """Registro único (fonte da verdade) de todo campo de preenchimento/inserção de dados das
    Telas 1 a 7 — Id estável no formato T(tela)(sequencial), ex. "T23" = Tela 2, campo 3. Nunca
    editável pela tela (Configurações Sistema é só consulta) — gerado por
    backend/scripts/migrar_campos_sistema.py. Campo novo criado no meio de uma tela já mapeada
    entra com o próximo sequencial livre daquela tela, nunca reordena os existentes."""
    __tablename__ = "campo_sistema"
    id = Column(Integer, primary_key=True)
    campo_id = Column(String, nullable=False, unique=True)  # "T23"
    tela = Column(Integer, nullable=False)
    rotulo = Column(String, nullable=False)
    seletor_html = Column(String, nullable=True)  # id/data-campo do elemento na tela (referência, não funcional)
    ordem = Column(Integer, default=0)


class PainelTermico(Base):
    """Lançamento de painel térmico (Parede/Teto/Isolamento Piso) — Tela E, uma linha por trecho.
    Área/qtd. de placas/Id. (P01/T01...) são calculados na leitura (ver calc_paineis_portas.py),
    não armazenados — largura de placa e medidas de placa de piso vêm do Projeto (únicas por
    projeto, nunca variam entre painéis do mesmo projeto)."""
    __tablename__ = "paineis_termicos"
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False, index=True)
    camara_completo_id = Column(Integer, ForeignKey("camaras_completo.id"), nullable=True, index=True)
    camara_simples_id = Column(Integer, ForeignKey("camaras_simples.id"), nullable=True, index=True)
    tipo = Column(String, nullable=False)   # Parede | Teto | Isolamento Piso
    espessura = Column(String)
    dimensao_1 = Column(Float)   # perímetro (parede) / comprimento (teto) / largura (piso), m
    dimensao_2 = Column(Float)   # altura (parede) / largura (teto) / comprimento (piso), m
    ordem = Column(Integer, default=0)   # ordem de lançamento — base pra numerar o Id. P01/T01
    ambiente_nao_climatizado_nome = Column(String, nullable=True)   # alternativa a câmara_completo/simples —
    # ambiente sem climatização (sem Id. Planta); cada nome distinto vira um "bloco" próprio nos resumos.
    fechada = Column(Boolean, default=False)
    calculo_snapshot_json = Column(Text)

    projeto = relationship("Projeto")
    camara_completo = relationship("CamaraCompleto")
    camara_simples = relationship("CamaraSimples")


class PortaFrigorifica(Base):
    """Lançamento de porta — Tela E, uma linha por porta. Id. (PRC-01-01 etc.) é calculado na
    leitura (ver calc_paineis_portas.py), não armazenado."""
    __tablename__ = "portas_frigorificas"
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False, index=True)
    camara_completo_id = Column(Integer, ForeignKey("camaras_completo.id"), nullable=True, index=True)
    camara_simples_id = Column(Integer, ForeignKey("camaras_simples.id"), nullable=True, index=True)
    funcao = Column(String)           # Resfriados | Congelados | Preparos | Docas | Não Climatizado
    modelo = Column(String)           # Correr | Embutir | Isoplana | Vai-Vem | Seccional | Portal Selamento
    sentido = Column(String)
    vao_largura_mm = Column(Float)
    vao_altura_mm = Column(Float)
    fixacao = Column(String)
    espessura_fixacao_mm = Column(Float)
    tensao = Column(String)           # só p/ porta com resistência
    observacoes = Column(Text)
    quantidade = Column(Integer, default=1)
    ordem = Column(Integer, default=0)   # ordem de lançamento — base pro sequencial do Id.
    ambiente_nao_climatizado_nome = Column(String, nullable=True)   # alternativa a câmara_completo/simples —
    # ambiente sem climatização (sem Id. Planta); cada nome distinto vira um "bloco" próprio nos resumos.
    fechada = Column(Boolean, default=False)
    calculo_snapshot_json = Column(Text)

    projeto = relationship("Projeto")
    camara_completo = relationship("CamaraCompleto")
    camara_simples = relationship("CamaraSimples")


# ===================== TELA 6 — RACK PARALELO =====================

class PolinomioCompressor(Base):
    """Coeficientes EN12900 (c1..c10) por fabricante/linha/modelo/gás/tensão/grandeza -- extraídos
    do software/site do fabricante (ver Documentos de Criação/C - Polinômios Compressores). Cálculo
    em tempo real: y = c1 + c2*to + c3*tc + c4*to^2 + c5*to*tc + c6*tc^2 + c7*to^3 + c8*tc*to^2 +
    c9*to*tc^2 + c10*tc^3 -- nunca se gera tabela, só se avalia a fórmula pro ponto de operação
    pedido. Fabricante/Linha NÃO são lista fixa no código -- os selects da Tela 6 usam SELECT
    DISTINCT nesta tabela, então só aparece o que já foi cadastrado/automatizado de verdade."""
    __tablename__ = "polinomio_compressor"
    id = Column(Integer, primary_key=True)
    fabricante = Column(String, nullable=False)
    linha = Column(String, nullable=False)      # ex.: "Semi-Hermético", "Duplo Estágio", "Parafuso"
    modelo = Column(String, nullable=False)      # código já resolvido (ex.: "2CES-3-20D")
    gas = Column(String, nullable=False)
    tensao = Column(String, nullable=False)      # ex.: "230V-3-60Hz"
    frequencia_hz = Column(Float)
    grandeza = Column(String, nullable=False)    # "Capacidade" | "Potência" | "Corrente" | "Vazão Mássica"
    unidade = Column(String)
    c1 = Column(Float); c2 = Column(Float); c3 = Column(Float); c4 = Column(Float); c5 = Column(Float)
    c6 = Column(Float); c7 = Column(Float); c8 = Column(Float); c9 = Column(Float); c10 = Column(Float)
    te_min = Column(Float)
    te_max = Column(Float)
    tc_min = Column(Float)
    tc_max = Column(Float)


class ValorNominalCompressor(Base):
    """Valor de placa (fixo, NÃO depende de Te/Tc) usado como alternativa quando o fabricante não
    fornece polinômio pra uma grandeza (ex.: Dorin tem Capacidade/Potência/Vazão Mássica mas não
    Corrente). Sempre marcado na tela como valor nominal, não calculado -- ver PolinomioCompressor
    para o caso normal (polinomial)."""
    __tablename__ = "valor_nominal_compressor"
    id = Column(Integer, primary_key=True)
    fabricante = Column(String, nullable=False)
    linha = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    tensao = Column(String, nullable=False)
    frequencia_hz = Column(Float)
    grandeza = Column(String, nullable=False)
    unidade = Column(String)
    valor = Column(Float, nullable=False)


class FaixaOperacaoCompressor(Base):
    """Faixa de operação recomendada (Alta/Média/Baixa/Universal) por modelo -- mesmo conceito já
    usado em UnidadeCondensadora.sistema/uc_selecao_sistema.faixa_operacao. Preenchimento manual,
    futuro (não vem do polinômio) -- os 4 limites numéricos de envelope (Te/Tc mín/máx) já existem
    em PolinomioCompressor (faixa de validade matemática do próprio polinômio), não precisam ser
    duplicados aqui. Uma linha por modelo real (não por gás/tensão/grandeza)."""
    __tablename__ = "faixa_operacao_compressor"
    id = Column(Integer, primary_key=True)
    fabricante = Column(String, nullable=False)
    linha = Column(String, nullable=False)
    modelo = Column(String, nullable=False)
    faixa_operacao = Column(String)   # Alta | Média | Baixa | Universal


class RackParalelo(Base):
    """Um registro por sistema com tipo_compressao = "Rack Paralelo" — Tela 6. Campos que já
    existem no Sistema (Estrutura do Equipamento, Gás Refrigerante, Temp. Linha de Líquido, Tipo
    de Partida) NÃO são repetidos aqui, são lidos direto do sistema. Folga técnica (real) não é
    campo salvo — é calculada (carga_total_fornecida / carga requerida do sistema), igual à folga
    real já usada em Forçadores."""
    __tablename__ = "rack_paralelo"
    id = Column(Integer, primary_key=True)
    sistema_id = Column(Integer, ForeignKey("sistemas_refrigeracao.id"), nullable=False, index=True)  # N racks por sistema
    considerado = Column(Boolean, default=False)  # a opção que entra em cálculo/compilação/consumo

    quantidade_compressores = Column(Integer)
    # Nº de racks IDÊNTICOS em paralelo dividindo a demanda do sistema (aprovado 2026-08-13).
    # Default 1 = comportamento anterior. Cada rack é dimensionado por carga ÷ quantidade_paralelo;
    # o total de condensadores do sistema = quantidade_condensadores × quantidade_paralelo.
    quantidade_paralelo = Column(Integer, default=1)
    # Mesmo conceito de folga já usado em Forçadores/UC -- percentual de margem sobre a carga
    # requerida do sistema (câmaras + expositores) antes de dividir entre as N posições do rack.
    folga_tecnica_pct = Column(Float)
    # None = Automático (segue a tabela "Classificação de Sistemas e Envelope Compressores" normal,
    # união de todas as faixas de motor). 1/2/3 = trava a seleção nesse motor específico — usado
    # quando o cadastro da tabela não reflete bem a Temp. Evaporação real (override manual do usuário).
    filtro_motor_compressor = Column(Integer)
    # "Modelo técnico" = código real de catálogo (usado no memorial descritivo). "Modelo Comercial"
    # = nome genérico próprio (texto livre, sem geração automática — usado só em proposta comercial
    # futura, pra não expor o fabricante/modelo real ao cliente).
    modelo_tecnico = Column(String)
    modelo_comercial = Column(String)
    tensao = Column(String)
    linha_compressor = Column(String)
    fabricante_compressor = Column(String)
    modelo_compressor = Column(String)
    cop_compressor = Column(Float)
    capacidade_compressor_kcal_h = Column(Float)      # unitária
    carga_total_fornecida_kcal_h = Column(Float)       # total do rack (Evaporator/Cooling capacity)
    calor_total_rejeitado_kcal_h = Column(Float)       # total do rack (Condenser capacity)
    potencia_total_w = Column(Float)
    corrente_nominal_a = Column(Float)
    corrente_maxima_trabalho_a = Column(Float)
    vazao_massica_kg_h = Column(Float)
    carga_oleo_l = Column(Float)
    conexao_descarga = Column(String)
    conexao_succao = Column(String)
    hp_total = Column(Float)                            # sempre preenchimento manual
    tanque_liquido_l = Column(Float)
    carga_gas_estimada_kg = Column(Float)
    # Sem campo de tipo de condensador: Rack Paralelo sempre tem condensador remoto por definição do
    # app (só Unidade Condensadora tem condensador onboard — ver _bloco_condensador). CR na nomenclatura
    # comercial é constante, não precisa de dado próprio.
    # ---- Seleção de Condensador Remoto (Fase 2, catálogo da Tela C) ----
    # Só a escolha é persistida (fabricante/linha + filtros + folga); o modelo escolhido e a
    # capacidade corrigida são calculados na leitura (ver /condensador), igual à seleção de compressor.
    fabricante_condensador = Column(String)
    linha_condensador = Column(String)
    # Estrutura do condensador (Plano (Fluxo Vertical) | Plano Onboard | V (Fluxo Horizontal) |
    # Onboard) — editável aqui na Tela 6 (antes vinha só-leitura do Sistema/Tela 1); casa em
    # comparação EXATA com LinhaCondensadorRemoto.tipo_estrutura.
    tipo_condensador = Column(String)
    filtro_fpi_condensador = Column(Integer)      # None = "Qualquer"
    filtro_polos_rpm_condensador = Column(String)  # None = "Qualquer" (nº polos p/ AC, RPM p/ EC)
    folga_condensador_pct = Column(Float)
    protecao_aletas_condensador = Column(Boolean, default=False)  # False=Padrão, True=Protegida
    # Quantidade de condensadores idênticos que dividem o calor rejeitado do rack — cada unidade é
    # dimensionada pela capacidade necessária / quantidade, igual ao conceito de N posições de
    # compressor. Resumo mostra "Nx Modelo", mesmo padrão do Modelo Compressor.
    quantidade_condensadores = Column(Integer, default=1)
    nomenclatura_condensador_selecionada = Column(Text)  # JSON {nome_campo: valor_escolhido} — mesmo
    # padrão do Forçador (nomenclatura_selecionada), pros Campos em modo Manual do código comercial.
    notas_condensador = Column(Text)  # campo livre "Notas" da Seleção de Condensador Remoto (Tela 6)
    fechada = Column(Boolean, default=False)
    calculo_snapshot_json = Column(Text)

    sistema = relationship("SistemaRefrigeracao", back_populates="racks")
    materiais = relationship("MaterialRack", back_populates="rack", cascade="all, delete-orphan", order_by="MaterialRack.ordem")
    compressores = relationship("CompressorRack", back_populates="rack", cascade="all, delete-orphan", order_by="CompressorRack.posicao")
    # N opções de condensador por rack; a marcada `considerado` é espelhada nas colunas *_condensador
    # acima (denormalização proposital: compilação/consumo/Tela 6 continuam lendo do rack sem mudança).
    condensadores = relationship("RackCondensadorSelecao", back_populates="rack",
                                 cascade="all, delete-orphan", order_by="RackCondensadorSelecao.id")


class RackCondensadorSelecao(Base):
    """Uma opção de condensador do rack (permite dimensionar mais de um fabricante por rack). Os 9
    campos espelham as colunas *_condensador de RackParalelo; a opção com `considerado=True` é copiada
    pra lá pelo backend, então todo o cálculo/exportação continua lendo do rack sem alteração."""
    __tablename__ = "rack_condensador_selecao"
    id = Column(Integer, primary_key=True)
    rack_id = Column(Integer, ForeignKey("rack_paralelo.id"), nullable=False, index=True)
    considerado = Column(Boolean, default=False)
    fabricante_condensador = Column(String)
    linha_condensador = Column(String)
    tipo_condensador = Column(String)
    filtro_fpi_condensador = Column(Integer)
    filtro_polos_rpm_condensador = Column(String)
    folga_condensador_pct = Column(Float)
    protecao_aletas_condensador = Column(Boolean, default=False)
    quantidade_condensadores = Column(Integer, default=1)
    nomenclatura_condensador_selecionada = Column(Text)
    notas_condensador = Column(Text)

    rack = relationship("RackParalelo", back_populates="condensadores")


# Campos de condensador espelhados entre RackParalelo e RackCondensadorSelecao (fonte única).
CAMPOS_CONDENSADOR = [
    "fabricante_condensador", "linha_condensador", "tipo_condensador", "filtro_fpi_condensador",
    "filtro_polos_rpm_condensador", "folga_condensador_pct", "protecao_aletas_condensador",
    "quantidade_condensadores", "nomenclatura_condensador_selecionada", "notas_condensador",
]


class CompressorRack(Base):
    """Uma linha por posição de compressor dentro do Rack Paralelo (1 a 5) -- Tela 6. Cada posição
    escolhe fabricante/linha/modelo/gás/tensão independente (podem ser todos diferentes entre si,
    somando capacidade pra atender a carga total). Resultado (Q/P/I/vazão) calculado em tempo real
    pelo polinômio (ver PolinomioCompressor), não armazenado -- só a seleção é persistida.

    percentual_sistema: só editável na posição 1 (master) -- percentual da demanda total que essa
    posição deve atender. O saldo (100% - percentual do master) é dividido em partes iguais entre
    as demais posições (2..N), calculado na hora, não armazenado nelas."""
    __tablename__ = "compressor_rack"
    id = Column(Integer, primary_key=True)
    rack_id = Column(Integer, ForeignKey("rack_paralelo.id"), nullable=False, index=True)
    posicao = Column(Integer, nullable=False)   # 1..5
    percentual_sistema = Column(Float)          # só usado na posicao 1 (master)
    fabricante = Column(String)
    linha = Column(String)
    modelo = Column(String)
    gas = Column(String)
    tensao = Column(String)

    rack = relationship("RackParalelo", back_populates="compressores")


class MaterialRack(Base):
    """Lista de Materiais do Rack — Tela 6, uma linha por peça. Pré-cadastrada (seed) na criação
    do RackParalelo com a lista padrão (~40 itens); quantidade fica em 0 até o usuário preencher."""
    __tablename__ = "material_rack"
    id = Column(Integer, primary_key=True)
    rack_id = Column(Integer, ForeignKey("rack_paralelo.id"), nullable=False, index=True)
    categoria = Column(String)     # Descarga | Líquido | Sucção | Sistema de Óleo | Diversos
    descricao = Column(String, nullable=False)
    modelo = Column(String)        # ex.: "COBRE (kg)", "AÇO" — especificação/material da peça
    quantidade = Column(Float, default=0)
    ordem = Column(Integer, default=0)

    rack = relationship("RackParalelo", back_populates="materiais")


class ClassificacaoSistemaCompressor(Base):
    """Tela 6 — Classificação de Sistemas e Envelope Compressores: tabela de referência fixa (não
    por projeto), 3 linhas (Alta/Média/Baixa). Pra cada faixa de Temp. Evap. do SISTEMA, define qual
    faixa de Temp. Evap. cada família de compressor Bitzer (Semi-Hermético / Duplo Estágio) atende —
    ex.: abaixo de -25°C só Duplo Estágio é candidato, razão de compressão fica alta demais pra um
    único estágio. Fonte: "Tabela Classificação de Sistema e Limite Compressores.xlsx"."""
    __tablename__ = "classificacao_sistema_compressor"
    id = Column(Integer, primary_key=True)
    tipo = Column(String, nullable=False)                    # "Sistema de Alta/Média/Baixa"
    temp_evap_sistema_min = Column(Float)
    temp_evap_sistema_max = Column(Float)
    motor_compressor = Column(Integer)                       # código 1/2/3 da planilha
    semi_hermetico_te_min = Column(Float)
    semi_hermetico_te_max = Column(Float)
    duplo_estagio_te_min = Column(Float)                     # None = Não Aplicável
    duplo_estagio_te_max = Column(Float)                     # None = Não Aplicável


class LubrificanteCompressor(Base):
    """Tela 6 — Lubrificante Compressores: tabela de referência fixa (não por projeto), mapeia
    Gás Refrigerante -> Tipo de Óleo recomendado pelo fabricante do compressor. Fonte: "Lubrificantes
    Compressores.xlsx". Uma linha por (fabricante, gás) — o mesmo gás pode ter óleo diferente
    conforme o fabricante do compressor."""
    __tablename__ = "lubrificante_compressor"
    id = Column(Integer, primary_key=True)
    fabricante = Column(String, nullable=False)   # ex.: "Bitzer"
    gas = Column(String, nullable=False)
    tipo_oleo = Column(String, nullable=False)


class DadosFisicosCompressorBitzer(Base):
    """Tela 6 — Dados Físicos Compressores Bitzer: tabela de referência fixa (não por projeto), uma
    linha por modelo Bitzer (Semi-Hermético/Duplo Estágio). Fonte: "Modelos_Bitzer_Cadastrados_R01a.
    xlsx". Semeada só com Linha/Modelo — o resto fica em branco pra preenchimento manual depois."""
    __tablename__ = "dados_fisicos_compressor_bitzer"
    id = Column(Integer, primary_key=True)
    linha = Column(String, nullable=False)        # "Semi-Hermético" / "Duplo Estágio"
    modelo = Column(String, nullable=False)
    vazao = Column(String)
    numero_cilindros_diametro_curso = Column(String)
    peso = Column(String)
    sobrepressao_maxima = Column(String)
    conexao_succao = Column(String)
    conexao_pressao = Column(String)
    protetor_motor = Column(String)
    classe_protecao = Column(String)
    qtd_enchimento_oleo = Column(String)
    regulacao_desempenho = Column(String)
    aquecimento_carter_oleo = Column(String)
    monitoramento_pressao_oleo = Column(String)
    versao_motor = Column(String)
    corrente_maxima_operacao = Column(String)
    corrente_partida = Column(String)
    potencia_sonora_10_45 = Column(String)
    potencia_sonora_35_40 = Column(String)
    pressao_sonora_1m_10_45 = Column(String)


class TabelaDisjuntorTermomagnetico(Base):
    """Tela 5 — Tabela de Disjuntores (Termomagnético): tabela de referência fixa (não por
    projeto), mesma disposição de linhas/colunas da planilha original "Tabela de Disjuntores.xlsx"
    (aba única, bloco superior). Uma linha por Corrente Nominal; 4 blocos de tensão/fase, cada um
    com Descrição de Projeto + Descrição Comercial. Curva (C/D) já vem embutida no texto da
    Descrição Comercial, não é coluna própria."""
    __tablename__ = "tabela_disjuntor_termomagnetico"
    id = Column(Integer, primary_key=True)
    utilizacao = Column(String)  # só a 1ª linha de cada bloco tinha rótulo na planilha original
    corrente_nominal_a = Column(Float, nullable=False)
    desc_proj_127v_1p = Column(String)
    desc_comercial_127v_1p = Column(String)
    desc_proj_220v_1p = Column(String)
    desc_comercial_220v_1p = Column(String)
    desc_proj_220v_3p = Column(String)
    desc_comercial_220v_3p = Column(String)
    desc_proj_380v_3p = Column(String)
    desc_comercial_380v_3p = Column(String)


class TabelaDisjuntorDDR(Base):
    """Tela 5 — Tabela de Disjuntores (DDR — Diferencial Residual): mesma estrutura da tabela
    Termomagnético, bloco inferior da planilha original (30mA fixo, embutido no texto da Descrição
    Comercial)."""
    __tablename__ = "tabela_disjuntor_ddr"
    id = Column(Integer, primary_key=True)
    utilizacao = Column(String)
    corrente_nominal_a = Column(Float, nullable=False)
    desc_proj_127v_1p = Column(String)
    desc_comercial_127v_1p = Column(String)
    desc_proj_220v_1p = Column(String)
    desc_comercial_220v_1p = Column(String)
    desc_proj_220v_3p = Column(String)
    desc_comercial_220v_3p = Column(String)
    desc_proj_380v_3p = Column(String)
    desc_comercial_380v_3p = Column(String)


class CentroCusto(Base):
    """Mestre (global, editado na Tela D) — mesma lista de Centros de Custo pra todos os projetos,
    igual FatorVenda/ItemComposicaoMestre (ver comentário lá)."""
    __tablename__ = "centro_custo"
    id = Column(Integer, primary_key=True)
    codigo = Column(String, nullable=False)
    referencia_id = Column(String)
    etapa = Column(String)
    descricao = Column(String)
    ordem = Column(Integer, default=0)
    # Bloco da Composição de Preço a que esse Centro de Custo pertence (ver composicao_preco.py,
    # BLOCOS_COMPOSICAO) — usado só pelo Resumo por bloco; None/vazio = não aparece no Resumo.
    bloco_composicao = Column(String, nullable=True)


class MaterialTela10(Base):
    __tablename__ = "material_tela10"
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False, index=True)
    categoria = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    fabricante = Column(String)
    centro_custo_id = Column(Integer, ForeignKey("centro_custo.id"), nullable=True, index=True)
    unidade = Column(String)
    quantidade = Column(Float, default=0)
    valor_unitario = Column(Float, nullable=True)
    observacao = Column(String, nullable=True)
    ordem = Column(Integer, default=0)

    projeto = relationship("Projeto")
    centro_custo = relationship("CentroCusto")


class EquipamentoValorTela10(Base):
    __tablename__ = "equipamento_valor_tela10"
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False, index=True)
    chave_equipamento = Column(String, nullable=False)
    centro_custo_id = Column(Integer, ForeignKey("centro_custo.id"), nullable=True, index=True)
    valor_unitario = Column(Float, nullable=True)
    observacao = Column(String, nullable=True)

    projeto = relationship("Projeto")
    centro_custo = relationship("CentroCusto")


# ===================== COMPOSIÇÃO DE PREÇO =====================
# Ver "Documentos de Criação/Tabela Composição Preço.xlsx" (planilha-exemplo). Blocos fixos no
# código (não em tabela): Equipamentos | Materiais Mecânicos | Materiais Elétricos | Painéis
# Térmicos | Outros Serviços | Fretes e Transporte Vertical (ver BLOCOS_COMPOSICAO em
# composicao_preco.py). Fórmula de preço = markup divisor (literatura de formação de preço de
# venda): Preço = Custo / (1 - %Impostos - %Comissão - %Margem) — ver composicao_preco.py.

class FatorVenda(Base):
    """Mestre (global, editado na Tela D) — % Impostos/Comissão/Margem de Contribuição por
    código de fator (FT1, FT2...), usado pra calcular o Fator de Venda de cada item da
    Composição de Preço."""
    __tablename__ = "fator_venda"
    id = Column(Integer, primary_key=True)
    codigo = Column(String, nullable=False, unique=True)   # "FT1", "FT2"...
    # "Revenda" | "Direto" (livre, só rótulo) | "Comissão" (repasse a preço de fábrica — o item
    # não leva markup nenhum, a comissão do fabricante é lançada à parte agregada por fabricante,
    # ver composicao_preco.calcular_item/sincronizar_comissoes_indicacao) — "Comissão" É lido
    # pelo motor de cálculo, os outros valores são só rótulo livre.
    tipo = Column(String)
    descricao = Column(String, nullable=False)
    pct_impostos = Column(Float, default=0)
    pct_comissao = Column(Float, default=0)
    pct_margem = Column(Float, default=0)
    ordem = Column(Integer, default=0)


class ItemComposicaoMestre(Base):
    """Mestre (global, editado na Tela D) — itens "Default" que devem sempre aparecer na
    Composição de Preço de qualquer projeto (mão de obra, frete, etc. — sem vínculo com dado do
    sistema). Copiado pro projeto (ComposicaoPrecoItem, origem="default") ao montar a
    composição; "Restaurar Padrões" reaplica os que estiverem faltando no projeto atual."""
    __tablename__ = "item_composicao_mestre"
    id = Column(Integer, primary_key=True)
    bloco = Column(String, nullable=False)
    centro_custo_codigo = Column(String)
    centro_custo_id = Column(Integer, ForeignKey("centro_custo.id"), nullable=True, index=True)
    descricao = Column(String, nullable=False)
    fator_id = Column(Integer, ForeignKey("fator_venda.id"), nullable=True, index=True)
    custo_unitario_padrao = Column(Float, default=0)
    ordem = Column(Integer, default=0)

    centro_custo = relationship("CentroCusto")
    fator = relationship("FatorVenda")


class Vendedor(Base):
    """Mestre (global, editado na Tela D) — nome + % de comissão padrão; "default" marca os
    vendedores que entram automaticamente na tabela de comissionamento de todo projeto novo."""
    __tablename__ = "vendedor"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False)
    pct_comissao_padrao = Column(Float, default=0)
    default = Column(Boolean, default=False)
    ordem = Column(Integer, default=0)


class ComposicaoPrecoItem(Base):
    """Item (linha) da Composição de Preço de um projeto — um registro por linha de qualquer
    dos 6 blocos. origem: "sistema" (sincronizado automaticamente da Tela 10/Tela 7, não editável
    manualmente na descrição/quantidade — só custo_unitario), "default" (copiado do mestre ao
    montar a composição, pode ser excluído da linha do projeto sem afetar o mestre) ou "manual"
    (inserido à mão pelo usuário nesse projeto)."""
    __tablename__ = "composicao_preco_item"
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False, index=True)
    bloco = Column(String, nullable=False)
    centro_custo_id = Column(Integer, ForeignKey("centro_custo.id"), nullable=True, index=True)
    fator_id = Column(Integer, ForeignKey("fator_venda.id"), nullable=True, index=True)
    descricao = Column(String, nullable=False)
    fabricante = Column(String, nullable=True)
    unidade = Column(String, nullable=True)
    observacao = Column(String, nullable=True)
    quantidade = Column(Float, default=1)
    custo_unitario = Column(Float, default=0)
    origem = Column(String, nullable=False, default="manual")   # sistema | default | manual
    # chave estável do item "sistema" (ex.: descrição do equipamento na Tela 10) — usada pra
    # sincronizar sem duplicar quando o usuário reabre a composição.
    chave_sistema = Column(String, nullable=True)
    ordem = Column(Integer, default=0)
    # Checkbox "considerar no orçamento" (Tela 10, aprovado 2026-08-12): item continua existindo
    # e calculado normalmente no bloco, só sai do Resumo por Bloco/Tabela de Orçamento/DRE/
    # Comissionamento quando desmarcado — reversível, nunca apaga o item.
    incluir_orcamento = Column(Boolean, default=True, nullable=False)
    fechada = Column(Boolean, default=False)
    calculo_snapshot_json = Column(Text)

    projeto = relationship("Projeto")
    centro_custo = relationship("CentroCusto")
    fator = relationship("FatorVenda")


class CondicaoPagamentoProjeto(Base):
    """Configuração de Condições de Pagamento de um projeto (Tela 10) — 1 registro por projeto.
    Usada só pra gerar a agenda de parcelas (CondicaoPagamentoParcela); reordenar/regerar
    substitui a agenda anterior."""
    __tablename__ = "condicao_pagamento_projeto"
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False, unique=True)
    percentual_sinal = Column(Float, default=0)
    data_sinal = Column(String)
    quantidade_parcelas = Column(Integer, default=0)
    periodicidade_dias = Column(Integer, default=30)
    fechada = Column(Boolean, default=False)
    calculo_snapshot_json = Column(Text)


class CondicaoPagamentoParcela(Base):
    """Linha da agenda de pagamento gerada (Sinal de Negócio + parcelas), sobre o Valor Total da
    Proposta (Tabela de Orçamento). Data/valor ficam editáveis manualmente após a geração — editar
    aqui não recalcula as demais linhas."""
    __tablename__ = "condicao_pagamento_parcela"
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False, index=True)
    ordem = Column(Integer, nullable=False)   # 0 = Sinal de Negócio, 1..N = parcelas
    descricao = Column(String, nullable=False)
    data = Column(String, nullable=False)
    valor = Column(Float, nullable=False)


class ComissaoVendedorProjeto(Base):
    """Vendedor(es) vinculados a um projeto, com o % de comissão daquele projeto (parte do %
    padrão do mestre Vendedor, editável por projeto)."""
    __tablename__ = "comissao_vendedor_projeto"
    id = Column(Integer, primary_key=True)
    projeto_id = Column(Integer, ForeignKey("projetos.id"), nullable=False, index=True)
    vendedor_id = Column(Integer, ForeignKey("vendedor.id"), nullable=False, index=True)
    percentual = Column(Float, default=0)
    fechada = Column(Boolean, default=False)
    calculo_snapshot_json = Column(Text)

    projeto = relationship("Projeto")
    vendedor = relationship("Vendedor")


class MargemNegociacaoProjeto(Base):
    """Fator de margem de negociação (N114 da planilha-exemplo) por projeto — % aplicado sobre
    o valor de venda total pra dar folga de negociação comercial."""
    __tablename__ = "margem_negociacao_projeto"
    projeto_id = Column(Integer, ForeignKey("projetos.id"), primary_key=True)
    percentual = Column(Float, default=0.05)
    fechada = Column(Boolean, default=False)
    calculo_snapshot_json = Column(Text)


# ===================== ESTUDO LUMINOTÉCNICO (Tela 11) — aprovado 2026-08-08 =====================

class LookupAmbienteLuminotecnico(Base):
    """"Tela 11 - Ambientes para Estudo Luminotécnico" (Configurações) — mestre global de
    Tipo Ambiente x Lux Recomendado, usado no cálculo de Lux Requerido de cada câmara."""
    __tablename__ = "lookup_ambiente_luminotecnico"
    id = Column(Integer, primary_key=True)
    nome = Column(String, nullable=False, unique=True)
    lux_recomendado = Column(Float, nullable=False)
    ordem = Column(Integer, default=0)


class LookupLampada(Base):
    """"Tela 11 - Cadastro Lâmpadas" (Configurações) — mestre global de Modelo de Luminária.
    Potência/Fluxo/IP entram no cálculo luminotécnico; Temperatura de Cor e Tensão são só
    informativos (aparecem na Tela 11), sem uso em fórmula. `id_comercial` é preenchido
    automaticamente (cascata da árvore de Ids Comerciais, nó "1.4.1 — Lâmpadas LED genéricas"),
    igual ao campo Modelo do Catálogo Comercial."""
    __tablename__ = "lookup_lampada"
    id = Column(Integer, primary_key=True)
    modelo = Column(String, nullable=False, unique=True)
    fabricante = Column(String)  # opcional -- puxado pra Composição de Preço; vazio = usuário preenche lá manual
    potencia_w = Column(Float, nullable=False)
    fluxo_lumens = Column(Float, nullable=False)
    ip = Column(String)
    temperatura_cor_k = Column(Float)
    tensao = Column(String)
    id_comercial = Column(String)
    ordem = Column(Integer, default=0)


class CatalogoVersao(Base):
    __tablename__ = "catalogo_versoes"
    tabela = Column(String, primary_key=True)
    versao = Column(Integer, nullable=False, default=1)
    atualizado_em = Column(String)
