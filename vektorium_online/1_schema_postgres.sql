-- ===============================================================
-- VEKTORIUM — Schema Postgres (CATÁLOGO) para Supabase
-- Gerado em 2026-08-21T00:11:45
-- Executar no SQL Editor do Supabase (organização Vektorium Sistemas).
-- ===============================================================

-- Tabela: cat_produtos
CREATE TABLE IF NOT EXISTS "cat_produtos" (
  "id" SERIAL PRIMARY KEY,
  "nome" TEXT NOT NULL UNIQUE,
  "temp_conservacao" TEXT,
  "umidade_relativa" TEXT,
  "tempo_conservacao" TEXT,
  "pct_agua" DOUBLE PRECISION,
  "ponto_congelamento" DOUBLE PRECISION,
  "calor_esp_antes" DOUBLE PRECISION,
  "calor_esp_depois" DOUBLE PRECISION,
  "calor_latente" DOUBLE PRECISION,
  "calor_respiracao" DOUBLE PRECISION,
  "classe" INTEGER,
  "fonte_status" TEXT
);

-- Tabela: cat_tipos_embalagem
CREATE TABLE IF NOT EXISTS "cat_tipos_embalagem" (
  "id" SERIAL PRIMARY KEY,
  "nome" TEXT NOT NULL UNIQUE,
  "calor_especifico" DOUBLE PRECISION
);

-- Tabela: cat_isolamento_parede_teto
CREATE TABLE IF NOT EXISTS "cat_isolamento_parede_teto" (
  "id" SERIAL PRIMARY KEY,
  "material" TEXT NOT NULL,
  "espessura_mm" INTEGER NOT NULL,
  "u_valor" DOUBLE PRECISION NOT NULL,
  "vao_maximo_apoios_mm" INTEGER
);

-- Tabela: cat_isolamento_piso
CREATE TABLE IF NOT EXISTS "cat_isolamento_piso" (
  "id" SERIAL PRIMARY KEY,
  "material" TEXT NOT NULL,
  "espessura_mm" INTEGER,
  "u_valor" DOUBLE PRECISION NOT NULL,
  "valido_apenas_acima_zero" BOOLEAN DEFAULT FALSE
);

-- Tabela: cat_tipos_equipamento
CREATE TABLE IF NOT EXISTS "cat_tipos_equipamento" (
  "id" SERIAL PRIMARY KEY,
  "nome" TEXT NOT NULL UNIQUE,
  "potencia_tipica_w" DOUBLE PRECISION,
  "fator_calor_rejeitado" DOUBLE PRECISION,
  "fator_simultaneidade" DOUBLE PRECISION
);

-- Tabela: cat_condicoes_climaticas
CREATE TABLE IF NOT EXISTS "cat_condicoes_climaticas" (
  "id" SERIAL PRIMARY KEY,
  "cidade" TEXT NOT NULL UNIQUE,
  "uf" TEXT,
  "codigo_estacao" INTEGER,
  "tbs_pico_sazonal" DOUBLE PRECISION,
  "tbu_pico_sazonal" DOUBLE PRECISION,
  "ur_pico_sazonal" DOUBLE PRECISION,
  "tbs_media_anual" DOUBLE PRECISION,
  "tbu_media_anual" DOUBLE PRECISION,
  "ur_media_anual" DOUBLE PRECISION,
  "tbs_maxima_absoluta" DOUBLE PRECISION
);

-- Tabela: estado_brasileiro
CREATE TABLE IF NOT EXISTS "estado_brasileiro" (
  "id" SERIAL PRIMARY KEY,
  "estado" TEXT NOT NULL,
  "sigla" TEXT NOT NULL UNIQUE,
  "capital" TEXT,
  "regiao" TEXT
);

-- Tabela: dados_climatologicos_inmet
CREATE TABLE IF NOT EXISTS "dados_climatologicos_inmet" (
  "id" SERIAL PRIMARY KEY,
  "codigo" TEXT NOT NULL,
  "nome_estacao" TEXT NOT NULL,
  "uf" TEXT NOT NULL,
  "temp_maxima_historica" DOUBLE PRECISION,
  "ur_media_historica" DOUBLE PRECISION
);

-- Tabela: cat_tabela_tipo02
CREATE TABLE IF NOT EXISTS "cat_tabela_tipo02" (
  "id" SERIAL PRIMARY KEY,
  "tipo" TEXT NOT NULL UNIQUE,
  "temp_interna_default" DOUBLE PRECISION
);

-- Tabela: cat_fator_altura
CREATE TABLE IF NOT EXISTS "cat_fator_altura" (
  "id" SERIAL PRIMARY KEY,
  "pe_direito_ate_m" DOUBLE PRECISION NOT NULL,
  "fator" DOUBLE PRECISION NOT NULL
);

-- Tabela: cat_fator_insolacao
CREATE TABLE IF NOT EXISTS "cat_fator_insolacao" (
  "id" SERIAL PRIMARY KEY,
  "orientacao" TEXT NOT NULL UNIQUE,
  "fator" DOUBLE PRECISION NOT NULL
);

-- Tabela: configuracao_global
CREATE TABLE IF NOT EXISTS "configuracao_global" (
  "id" SERIAL PRIMARY KEY,
  "chave" TEXT NOT NULL UNIQUE,
  "valor" DOUBLE PRECISION NOT NULL,
  "descricao" TEXT,
  "pendente_confirmacao" BOOLEAN DEFAULT FALSE
);

-- Tabela: cat_faixas_trocas_ar
CREATE TABLE IF NOT EXISTS "cat_faixas_trocas_ar" (
  "id" SERIAL PRIMARY KEY,
  "tipo_aplicacao" TEXT NOT NULL UNIQUE,
  "minimo" DOUBLE PRECISION NOT NULL,
  "maximo" DOUBLE PRECISION NOT NULL
);

-- Tabela: cat_classes_produto
CREATE TABLE IF NOT EXISTS "cat_classes_produto" (
  "id" SERIAL PRIMARY KEY,
  "classe" INTEGER NOT NULL UNIQUE,
  "dt_evap_min" DOUBLE PRECISION,
  "dt_evap_max" DOUBLE PRECISION,
  "ur_min" DOUBLE PRECISION,
  "ur_max" DOUBLE PRECISION,
  "aplicacao" TEXT
);

-- Tabela: cat_setores_expositor
CREATE TABLE IF NOT EXISTS "cat_setores_expositor" (
  "id" SERIAL PRIMARY KEY,
  "nome" TEXT NOT NULL UNIQUE
);

-- Tabela: cat_bancos_expositor
CREATE TABLE IF NOT EXISTS "cat_bancos_expositor" (
  "id" SERIAL PRIMARY KEY,
  "nome" TEXT NOT NULL UNIQUE
);

-- Tabela: cat_fabricantes
CREATE TABLE IF NOT EXISTS "cat_fabricantes" (
  "id" SERIAL PRIMARY KEY,
  "nome" TEXT NOT NULL UNIQUE
);

-- Tabela: tabela_valvula_expansao
CREATE TABLE IF NOT EXISTS "tabela_valvula_expansao" (
  "id" SERIAL PRIMARY KEY,
  "fabricante" TEXT NOT NULL,
  "tipo_expansao" TEXT NOT NULL,
  "modelo" TEXT NOT NULL,
  "conexao_entrada" TEXT,
  "conexao_saida" TEXT,
  "tensao" TEXT,
  "tipo_motor" TEXT,
  "equalizacao" TEXT,
  "gas_compativel" TEXT
);

-- Tabela: tabela_controlador_valvula
CREATE TABLE IF NOT EXISTS "tabela_controlador_valvula" (
  "id" SERIAL PRIMARY KEY,
  "fabricante" TEXT NOT NULL,
  "modelo" TEXT NOT NULL,
  "tipo_expansao" TEXT NOT NULL,
  "classificacao" TEXT,
  "observacao" TEXT
);

-- Tabela: tabela_compatibilidade_valvula
CREATE TABLE IF NOT EXISTS "tabela_compatibilidade_valvula" (
  "id" SERIAL PRIMARY KEY,
  "valvula_modelo" TEXT NOT NULL,
  "controlador_modelo" TEXT NOT NULL
);

-- Tabela: uc_catalogos
CREATE TABLE IF NOT EXISTS "uc_catalogos" (
  "id" SERIAL PRIMARY KEY,
  "fabricante_uc" TEXT NOT NULL,
  "nome" TEXT NOT NULL,
  "versao_catalogo" TEXT,
  "descricao_comercial" TEXT,
  "imagem_path" TEXT,
  "ativo_comercial" BOOLEAN DEFAULT TRUE,
  "id_comercial" TEXT
);
ALTER TABLE "uc_catalogos" ADD CONSTRAINT "uq_catalogo_uc" UNIQUE ("fabricante_uc", "nome", "versao_catalogo");

-- Tabela: campo_catalogo
CREATE TABLE IF NOT EXISTS "campo_catalogo" (
  "id" SERIAL PRIMARY KEY,
  "tipo_catalogo" TEXT NOT NULL,
  "catalogo_id" INTEGER NOT NULL,
  "ordem" INTEGER NOT NULL DEFAULT 0,
  "nome_campo" TEXT NOT NULL,
  "modo" TEXT NOT NULL DEFAULT 'manual',
  "campo_busca_sistema" TEXT,
  "codigo_fixo" TEXT,
  "substitui_coringa_modelo" BOOLEAN DEFAULT FALSE
);

-- Tabela: paineis_portas_lookup
CREATE TABLE IF NOT EXISTS "paineis_portas_lookup" (
  "id" SERIAL PRIMARY KEY,
  "categoria" TEXT NOT NULL,
  "valor" TEXT NOT NULL,
  "grupo" TEXT,
  "ordem" INTEGER DEFAULT 0,
  "descricao_inicial" TEXT,
  "prefixo_id" TEXT,
  "id_comercial" TEXT
);

-- Tabela: catalogo_comercial
CREATE TABLE IF NOT EXISTS "catalogo_comercial" (
  "id" SERIAL PRIMARY KEY,
  "categoria" TEXT NOT NULL,
  "fabricante" TEXT,
  "modelo" TEXT,
  "nome" TEXT NOT NULL,
  "descricao_comercial" TEXT,
  "imagem_path" TEXT,
  "id_comercial" TEXT,
  "id_cadastro" TEXT
);

-- Tabela: campo_sistema
CREATE TABLE IF NOT EXISTS "campo_sistema" (
  "id" SERIAL PRIMARY KEY,
  "campo_id" TEXT NOT NULL UNIQUE,
  "tela" INTEGER NOT NULL,
  "rotulo" TEXT NOT NULL,
  "seletor_html" TEXT,
  "ordem" INTEGER DEFAULT 0
);

-- Tabela: polinomio_compressor
CREATE TABLE IF NOT EXISTS "polinomio_compressor" (
  "id" SERIAL PRIMARY KEY,
  "fabricante" TEXT NOT NULL,
  "linha" TEXT NOT NULL,
  "modelo" TEXT NOT NULL,
  "gas" TEXT NOT NULL,
  "tensao" TEXT NOT NULL,
  "frequencia_hz" DOUBLE PRECISION,
  "grandeza" TEXT NOT NULL,
  "unidade" TEXT,
  "c1" DOUBLE PRECISION,
  "c2" DOUBLE PRECISION,
  "c3" DOUBLE PRECISION,
  "c4" DOUBLE PRECISION,
  "c5" DOUBLE PRECISION,
  "c6" DOUBLE PRECISION,
  "c7" DOUBLE PRECISION,
  "c8" DOUBLE PRECISION,
  "c9" DOUBLE PRECISION,
  "c10" DOUBLE PRECISION,
  "te_min" DOUBLE PRECISION,
  "te_max" DOUBLE PRECISION,
  "tc_min" DOUBLE PRECISION,
  "tc_max" DOUBLE PRECISION
);

-- Tabela: valor_nominal_compressor
CREATE TABLE IF NOT EXISTS "valor_nominal_compressor" (
  "id" SERIAL PRIMARY KEY,
  "fabricante" TEXT NOT NULL,
  "linha" TEXT NOT NULL,
  "modelo" TEXT NOT NULL,
  "tensao" TEXT NOT NULL,
  "frequencia_hz" DOUBLE PRECISION,
  "grandeza" TEXT NOT NULL,
  "unidade" TEXT,
  "valor" DOUBLE PRECISION NOT NULL
);

-- Tabela: faixa_operacao_compressor
CREATE TABLE IF NOT EXISTS "faixa_operacao_compressor" (
  "id" SERIAL PRIMARY KEY,
  "fabricante" TEXT NOT NULL,
  "linha" TEXT NOT NULL,
  "modelo" TEXT NOT NULL,
  "faixa_operacao" TEXT
);

-- Tabela: classificacao_sistema_compressor
CREATE TABLE IF NOT EXISTS "classificacao_sistema_compressor" (
  "id" SERIAL PRIMARY KEY,
  "tipo" TEXT NOT NULL,
  "temp_evap_sistema_min" DOUBLE PRECISION,
  "temp_evap_sistema_max" DOUBLE PRECISION,
  "motor_compressor" INTEGER,
  "semi_hermetico_te_min" DOUBLE PRECISION,
  "semi_hermetico_te_max" DOUBLE PRECISION,
  "duplo_estagio_te_min" DOUBLE PRECISION,
  "duplo_estagio_te_max" DOUBLE PRECISION
);

-- Tabela: lubrificante_compressor
CREATE TABLE IF NOT EXISTS "lubrificante_compressor" (
  "id" SERIAL PRIMARY KEY,
  "fabricante" TEXT NOT NULL,
  "gas" TEXT NOT NULL,
  "tipo_oleo" TEXT NOT NULL
);

-- Tabela: dados_fisicos_compressor_bitzer
CREATE TABLE IF NOT EXISTS "dados_fisicos_compressor_bitzer" (
  "id" SERIAL PRIMARY KEY,
  "linha" TEXT NOT NULL,
  "modelo" TEXT NOT NULL,
  "vazao" TEXT,
  "numero_cilindros_diametro_curso" TEXT,
  "peso" TEXT,
  "sobrepressao_maxima" TEXT,
  "conexao_succao" TEXT,
  "conexao_pressao" TEXT,
  "protetor_motor" TEXT,
  "classe_protecao" TEXT,
  "qtd_enchimento_oleo" TEXT,
  "regulacao_desempenho" TEXT,
  "aquecimento_carter_oleo" TEXT,
  "monitoramento_pressao_oleo" TEXT,
  "versao_motor" TEXT,
  "corrente_maxima_operacao" TEXT,
  "corrente_partida" TEXT,
  "potencia_sonora_10_45" TEXT,
  "potencia_sonora_35_40" TEXT,
  "pressao_sonora_1m_10_45" TEXT
);

-- Tabela: tabela_disjuntor_termomagnetico
CREATE TABLE IF NOT EXISTS "tabela_disjuntor_termomagnetico" (
  "id" SERIAL PRIMARY KEY,
  "utilizacao" TEXT,
  "corrente_nominal_a" DOUBLE PRECISION NOT NULL,
  "desc_proj_127v_1p" TEXT,
  "desc_comercial_127v_1p" TEXT,
  "desc_proj_220v_1p" TEXT,
  "desc_comercial_220v_1p" TEXT,
  "desc_proj_220v_3p" TEXT,
  "desc_comercial_220v_3p" TEXT,
  "desc_proj_380v_3p" TEXT,
  "desc_comercial_380v_3p" TEXT
);

-- Tabela: tabela_disjuntor_ddr
CREATE TABLE IF NOT EXISTS "tabela_disjuntor_ddr" (
  "id" SERIAL PRIMARY KEY,
  "utilizacao" TEXT,
  "corrente_nominal_a" DOUBLE PRECISION NOT NULL,
  "desc_proj_127v_1p" TEXT,
  "desc_comercial_127v_1p" TEXT,
  "desc_proj_220v_1p" TEXT,
  "desc_comercial_220v_1p" TEXT,
  "desc_proj_220v_3p" TEXT,
  "desc_comercial_220v_3p" TEXT,
  "desc_proj_380v_3p" TEXT,
  "desc_comercial_380v_3p" TEXT
);

-- Tabela: fator_venda
CREATE TABLE IF NOT EXISTS "fator_venda" (
  "id" SERIAL PRIMARY KEY,
  "codigo" TEXT NOT NULL UNIQUE,
  "tipo" TEXT,
  "descricao" TEXT NOT NULL,
  "pct_impostos" DOUBLE PRECISION DEFAULT 0,
  "pct_comissao" DOUBLE PRECISION DEFAULT 0,
  "pct_margem" DOUBLE PRECISION DEFAULT 0,
  "ordem" INTEGER DEFAULT 0
);

-- Tabela: lookup_ambiente_luminotecnico
CREATE TABLE IF NOT EXISTS "lookup_ambiente_luminotecnico" (
  "id" SERIAL PRIMARY KEY,
  "nome" TEXT NOT NULL UNIQUE,
  "lux_recomendado" DOUBLE PRECISION NOT NULL,
  "ordem" INTEGER DEFAULT 0
);

-- Tabela: lookup_lampada
CREATE TABLE IF NOT EXISTS "lookup_lampada" (
  "id" SERIAL PRIMARY KEY,
  "modelo" TEXT NOT NULL UNIQUE,
  "fabricante" TEXT,
  "potencia_w" DOUBLE PRECISION NOT NULL,
  "fluxo_lumens" DOUBLE PRECISION NOT NULL,
  "ip" TEXT,
  "temperatura_cor_k" DOUBLE PRECISION,
  "tensao" TEXT,
  "id_comercial" TEXT,
  "ordem" INTEGER DEFAULT 0
);

-- Tabela: cat_faixa_area_tabela02
CREATE TABLE IF NOT EXISTS "cat_faixa_area_tabela02" (
  "id" SERIAL PRIMARY KEY,
  "tabela02_id" INTEGER NOT NULL,
  "area_de" DOUBLE PRECISION NOT NULL,
  "area_ate" DOUBLE PRECISION NOT NULL,
  "carga_kcal_h" DOUBLE PRECISION NOT NULL,
  FOREIGN KEY ("tabela02_id") REFERENCES "cat_tabela_tipo02"("id") ON DELETE CASCADE
);

-- Tabela: cat_modelos_expositor
CREATE TABLE IF NOT EXISTS "cat_modelos_expositor" (
  "id" SERIAL PRIMARY KEY,
  "banco_id" INTEGER NOT NULL,
  "nome" TEXT NOT NULL,
  "carga_termica_25" DOUBLE PRECISION,
  "carga_termica_28" DOUBLE PRECISION,
  "carga_eletrica_w" DOUBLE PRECISION,
  "vazao_ar_m3h" DOUBLE PRECISION,
  FOREIGN KEY ("banco_id") REFERENCES "cat_bancos_expositor"("id") ON DELETE CASCADE
);

-- Tabela: forcador_linhas
CREATE TABLE IF NOT EXISTS "forcador_linhas" (
  "id" SERIAL PRIMARY KEY,
  "fabricante_id" INTEGER NOT NULL,
  "nome" TEXT NOT NULL,
  "versao_catalogo" TEXT,
  "ativo_comercial" BOOLEAN DEFAULT TRUE,
  "observacao_versao" TEXT,
  "linha_anterior_id" INTEGER,
  "descricao_comercial" TEXT,
  "imagem_path" TEXT,
  "id_comercial" TEXT,
  FOREIGN KEY ("fabricante_id") REFERENCES "cat_fabricantes"("id") ON DELETE CASCADE,
  FOREIGN KEY ("linha_anterior_id") REFERENCES "forcador_linhas"("id") ON DELETE CASCADE
);
ALTER TABLE "forcador_linhas" ADD CONSTRAINT "uq_linha_versao" UNIQUE ("fabricante_id", "nome", "versao_catalogo");

-- Tabela: condensador_linhas
CREATE TABLE IF NOT EXISTS "condensador_linhas" (
  "id" SERIAL PRIMARY KEY,
  "fabricante_id" INTEGER NOT NULL,
  "nome" TEXT NOT NULL,
  "versao_catalogo" TEXT,
  "tipo_estrutura" TEXT,
  "dt_catalogo_c" DOUBLE PRECISION,
  "ativo_comercial" BOOLEAN DEFAULT TRUE,
  "observacao_versao" TEXT,
  "linha_anterior_id" INTEGER,
  "descricao_comercial" TEXT,
  "imagem_path" TEXT,
  "id_comercial" TEXT,
  FOREIGN KEY ("fabricante_id") REFERENCES "cat_fabricantes"("id") ON DELETE CASCADE,
  FOREIGN KEY ("linha_anterior_id") REFERENCES "condensador_linhas"("id") ON DELETE CASCADE
);
ALTER TABLE "condensador_linhas" ADD CONSTRAINT "uq_condensador_linha_versao" UNIQUE ("fabricante_id", "nome", "versao_catalogo", "tipo_estrutura");

-- Tabela: cat_modelos_valvula
CREATE TABLE IF NOT EXISTS "cat_modelos_valvula" (
  "id" SERIAL PRIMARY KEY,
  "fabricante_id" INTEGER NOT NULL,
  "tipo_expansao" TEXT NOT NULL,
  "modelo" TEXT NOT NULL,
  "capacidade_nominal_kcal_h" DOUBLE PRECISION NOT NULL,
  FOREIGN KEY ("fabricante_id") REFERENCES "cat_fabricantes"("id") ON DELETE CASCADE
);

-- Tabela: uc_unidades
CREATE TABLE IF NOT EXISTS "uc_unidades" (
  "id" SERIAL PRIMARY KEY,
  "catalogo_id" INTEGER NOT NULL,
  "modelo" TEXT NOT NULL,
  "sistema" TEXT,
  "gas" TEXT,
  "tipo_compressor" TEXT,
  "fabricante_compressor" TEXT,
  "numero_compressores" INTEGER,
  "hp" DOUBLE PRECISION,
  "vent_qtd" INTEGER,
  "conexao_liquido" TEXT,
  "conexao_succao" TEXT,
  "tanque_liquido_l" DOUBLE PRECISION,
  "nivel_ruido_db" DOUBLE PRECISION,
  "ventilador_diametro_mm" DOUBLE PRECISION,
  "comprimento_mm" DOUBLE PRECISION,
  "largura_mm" DOUBLE PRECISION,
  "altura_mm" DOUBLE PRECISION,
  "peso_liquido_kg" DOUBLE PRECISION,
  "peso_bruto_kg" DOUBLE PRECISION,
  "nomenclatura_compra" TEXT,
  FOREIGN KEY ("catalogo_id") REFERENCES "uc_catalogos"("id") ON DELETE CASCADE
);

-- Tabela: campo_catalogo_opcao
CREATE TABLE IF NOT EXISTS "campo_catalogo_opcao" (
  "id" SERIAL PRIMARY KEY,
  "campo_id" INTEGER NOT NULL,
  "valor" TEXT NOT NULL,
  "codigo" TEXT NOT NULL,
  "ordem" INTEGER DEFAULT 0,
  FOREIGN KEY ("campo_id") REFERENCES "campo_catalogo"("id") ON DELETE CASCADE
);

-- Tabela: id_comercial
CREATE TABLE IF NOT EXISTS "id_comercial" (
  "id" SERIAL PRIMARY KEY,
  "codigo" TEXT NOT NULL UNIQUE,
  "nome" TEXT NOT NULL,
  "ordem" INTEGER DEFAULT 0,
  "campo_id" TEXT,
  "centro_custo_padrao_codigo" TEXT,
  "fator_venda_padrao_id" INTEGER,
  "origem_automatica" BOOLEAN DEFAULT FALSE,
  FOREIGN KEY ("fator_venda_padrao_id") REFERENCES "fator_venda"("id") ON DELETE CASCADE
);

-- Tabela: item_composicao_mestre
CREATE TABLE IF NOT EXISTS "item_composicao_mestre" (
  "id" SERIAL PRIMARY KEY,
  "bloco" TEXT NOT NULL,
  "centro_custo_codigo" TEXT,
  "descricao" TEXT NOT NULL,
  "fator_id" INTEGER,
  "ordem" INTEGER DEFAULT 0,
  FOREIGN KEY ("fator_id") REFERENCES "fator_venda"("id") ON DELETE CASCADE
);

-- Tabela: forcador_modelos
CREATE TABLE IF NOT EXISTS "forcador_modelos" (
  "id" SERIAL PRIMARY KEY,
  "linha_id" INTEGER NOT NULL,
  "modelo" TEXT NOT NULL,
  "fpi" INTEGER,
  "num_ventiladores" INTEGER,
  "diametro_ventilador_mm" DOUBLE PRECISION,
  "tipo_degelo" TEXT,
  "carga_gas_kg" DOUBLE PRECISION,
  "pot_resistencia_degelo_w" DOUBLE PRECISION,
  "vazao_ar_m3h" DOUBLE PRECISION,
  "dt_referencia_c" DOUBLE PRECISION,
  "pdl_referencia_m" DOUBLE PRECISION,
  "flecha_ar_m" DOUBLE PRECISION,
  "altura_max_instalacao_m" DOUBLE PRECISION,
  "coletores_por_forcador" INTEGER DEFAULT 1,
  "nomenclatura_compra" TEXT,
  "descricao_comercial" TEXT,
  "imagem_path" TEXT,
  FOREIGN KEY ("linha_id") REFERENCES "forcador_linhas"("id") ON DELETE CASCADE
);

-- Tabela: forcador_fatores_gas
CREATE TABLE IF NOT EXISTS "forcador_fatores_gas" (
  "id" SERIAL PRIMARY KEY,
  "linha_id" INTEGER NOT NULL,
  "gas" TEXT NOT NULL,
  "fator" DOUBLE PRECISION,
  FOREIGN KEY ("linha_id") REFERENCES "forcador_linhas"("id") ON DELETE CASCADE
);
ALTER TABLE "forcador_fatores_gas" ADD CONSTRAINT "uq_linha_gas" UNIQUE ("linha_id", "gas");

-- Tabela: condensador_modelos
CREATE TABLE IF NOT EXISTS "condensador_modelos" (
  "id" SERIAL PRIMARY KEY,
  "linha_id" INTEGER NOT NULL,
  "modelo" TEXT NOT NULL,
  "fpi" INTEGER,
  "qtd_ventiladores" INTEGER,
  "diametro_ventilador_mm" DOUBLE PRECISION,
  "vazao_ar_m3h" DOUBLE PRECISION,
  "polos_ou_rpm" TEXT,
  "tipo_motor" TEXT,
  "num_fileiras" INTEGER,
  "capacidade_kcal_h" DOUBLE PRECISION,
  "potencia_kw" DOUBLE PRECISION,
  "corrente_220v" DOUBLE PRECISION,
  "corrente_380v" DOUBLE PRECISION,
  "corrente_460v" DOUBLE PRECISION,
  "ruido_db" DOUBLE PRECISION,
  "carga_refrigerante_kg" DOUBLE PRECISION,
  "coletor_entrada_pol" TEXT,
  "coletor_saida_pol" TEXT,
  "peso_liquido_kg" DOUBLE PRECISION,
  "peso_bruto_kg" DOUBLE PRECISION,
  "comprimento_mm" DOUBLE PRECISION,
  "largura_mm" DOUBLE PRECISION,
  "altura_mm" DOUBLE PRECISION,
  "num_fixacoes" INTEGER,
  "nomenclatura_compra" TEXT,
  "descricao_comercial" TEXT,
  "imagem_path" TEXT,
  FOREIGN KEY ("linha_id") REFERENCES "condensador_linhas"("id") ON DELETE CASCADE
);

-- Tabela: condensador_fatores
CREATE TABLE IF NOT EXISTS "condensador_fatores" (
  "id" SERIAL PRIMARY KEY,
  "linha_id" INTEGER NOT NULL,
  "tipo" TEXT NOT NULL,
  "chave" TEXT NOT NULL,
  "fator" DOUBLE PRECISION,
  FOREIGN KEY ("linha_id") REFERENCES "condensador_linhas"("id") ON DELETE CASCADE
);
ALTER TABLE "condensador_fatores" ADD CONSTRAINT "uq_condensador_fator" UNIQUE ("linha_id", "tipo", "chave");

-- Tabela: uc_eletricas
CREATE TABLE IF NOT EXISTS "uc_eletricas" (
  "id" SERIAL PRIMARY KEY,
  "unidade_id" INTEGER NOT NULL,
  "tensao" TEXT,
  "fases" INTEGER,
  "frequencia" TEXT,
  "modelo_compressor" TEXT,
  "mcc_a" DOUBLE PRECISION,
  "rla_a" DOUBLE PRECISION,
  "lra_a" DOUBLE PRECISION,
  "vent_tensao" TEXT,
  "vent_fases" INTEGER,
  "vent_frequencia" TEXT,
  "vent_corrente_a" DOUBLE PRECISION,
  FOREIGN KEY ("unidade_id") REFERENCES "uc_unidades"("id") ON DELETE CASCADE
);

-- Tabela: uc_capacidades
CREATE TABLE IF NOT EXISTS "uc_capacidades" (
  "id" SERIAL PRIMARY KEY,
  "unidade_id" INTEGER NOT NULL,
  "temp_ambiente_c" DOUBLE PRECISION NOT NULL,
  "temp_evaporacao_c" DOUBLE PRECISION NOT NULL,
  "capacidade_kcal_h" DOUBLE PRECISION,
  "potencia_kw" DOUBLE PRECISION,
  FOREIGN KEY ("unidade_id") REFERENCES "uc_unidades"("id") ON DELETE CASCADE
);

-- Tabela: forcador_capacidades
CREATE TABLE IF NOT EXISTS "forcador_capacidades" (
  "id" SERIAL PRIMARY KEY,
  "modelo_id" INTEGER NOT NULL,
  "temp_evaporacao_c" DOUBLE PRECISION NOT NULL,
  "capacidade_kcal_h" DOUBLE PRECISION NOT NULL,
  FOREIGN KEY ("modelo_id") REFERENCES "forcador_modelos"("id") ON DELETE CASCADE
);

-- Tabela: forcador_eletricos
CREATE TABLE IF NOT EXISTS "forcador_eletricos" (
  "id" SERIAL PRIMARY KEY,
  "modelo_id" INTEGER NOT NULL,
  "tensao" TEXT NOT NULL,
  "degelo_w" DOUBLE PRECISION,
  "degelo_a" DOUBLE PRECISION,
  "motores_w" DOUBLE PRECISION,
  "motores_a" DOUBLE PRECISION,
  FOREIGN KEY ("modelo_id") REFERENCES "forcador_modelos"("id") ON DELETE CASCADE
);

-- Tabela: forcador_fisicos
CREATE TABLE IF NOT EXISTS "forcador_fisicos" (
  "id" SERIAL PRIMARY KEY,
  "modelo_id" INTEGER NOT NULL,
  "linha_liquido" TEXT,
  "linha_succao" TEXT,
  "equalizador" TEXT,
  "dreno" TEXT,
  "peso_liquido_kg" DOUBLE PRECISION,
  "carga_refrigerante_kg" DOUBLE PRECISION,
  FOREIGN KEY ("modelo_id") REFERENCES "forcador_modelos"("id") ON DELETE CASCADE
);

-- Tabela: forcador_dimensionais
CREATE TABLE IF NOT EXISTS "forcador_dimensionais" (
  "id" SERIAL PRIMARY KEY,
  "modelo_id" INTEGER NOT NULL,
  "comprimento_mm" DOUBLE PRECISION,
  "largura_mm" DOUBLE PRECISION,
  "altura_mm" DOUBLE PRECISION,
  "num_fixacoes" INTEGER,
  FOREIGN KEY ("modelo_id") REFERENCES "forcador_modelos"("id") ON DELETE CASCADE
);
