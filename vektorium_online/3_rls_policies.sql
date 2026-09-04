-- ===============================================================
-- VEKTORIUM — RLS (Row Level Security) inicial
-- Gerado em 2026-08-21T00:11:46
-- Executar POR ÚLTIMO. Habilita RLS em todas as tabelas de catálogo
-- e cria policy de LEITURA para qualquer usuário autenticado.
-- (Depois, na Fase 2, refinamos por papel/assinatura.)
-- ===============================================================

ALTER TABLE "cat_produtos" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_produtos" ON "cat_produtos" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_tipos_embalagem" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_tipos_embalagem" ON "cat_tipos_embalagem" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_isolamento_parede_teto" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_isolamento_parede_teto" ON "cat_isolamento_parede_teto" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_isolamento_piso" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_isolamento_piso" ON "cat_isolamento_piso" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_tipos_equipamento" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_tipos_equipamento" ON "cat_tipos_equipamento" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_condicoes_climaticas" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_condicoes_climaticas" ON "cat_condicoes_climaticas" FOR SELECT TO authenticated USING (true);

ALTER TABLE "estado_brasileiro" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_estado_brasileiro" ON "estado_brasileiro" FOR SELECT TO authenticated USING (true);

ALTER TABLE "dados_climatologicos_inmet" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_dados_climatologicos_inmet" ON "dados_climatologicos_inmet" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_tabela_tipo02" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_tabela_tipo02" ON "cat_tabela_tipo02" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_fator_altura" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_fator_altura" ON "cat_fator_altura" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_fator_insolacao" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_fator_insolacao" ON "cat_fator_insolacao" FOR SELECT TO authenticated USING (true);

ALTER TABLE "configuracao_global" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_configuracao_global" ON "configuracao_global" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_faixas_trocas_ar" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_faixas_trocas_ar" ON "cat_faixas_trocas_ar" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_classes_produto" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_classes_produto" ON "cat_classes_produto" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_setores_expositor" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_setores_expositor" ON "cat_setores_expositor" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_bancos_expositor" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_bancos_expositor" ON "cat_bancos_expositor" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_fabricantes" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_fabricantes" ON "cat_fabricantes" FOR SELECT TO authenticated USING (true);

ALTER TABLE "tabela_valvula_expansao" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_tabela_valvula_expansao" ON "tabela_valvula_expansao" FOR SELECT TO authenticated USING (true);

ALTER TABLE "tabela_controlador_valvula" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_tabela_controlador_valvula" ON "tabela_controlador_valvula" FOR SELECT TO authenticated USING (true);

ALTER TABLE "tabela_compatibilidade_valvula" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_tabela_compatibilidade_valvula" ON "tabela_compatibilidade_valvula" FOR SELECT TO authenticated USING (true);

ALTER TABLE "uc_catalogos" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_uc_catalogos" ON "uc_catalogos" FOR SELECT TO authenticated USING (true);

ALTER TABLE "campo_catalogo" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_campo_catalogo" ON "campo_catalogo" FOR SELECT TO authenticated USING (true);

ALTER TABLE "paineis_portas_lookup" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_paineis_portas_lookup" ON "paineis_portas_lookup" FOR SELECT TO authenticated USING (true);

ALTER TABLE "catalogo_comercial" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_catalogo_comercial" ON "catalogo_comercial" FOR SELECT TO authenticated USING (true);

ALTER TABLE "campo_sistema" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_campo_sistema" ON "campo_sistema" FOR SELECT TO authenticated USING (true);

ALTER TABLE "polinomio_compressor" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_polinomio_compressor" ON "polinomio_compressor" FOR SELECT TO authenticated USING (true);

ALTER TABLE "valor_nominal_compressor" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_valor_nominal_compressor" ON "valor_nominal_compressor" FOR SELECT TO authenticated USING (true);

ALTER TABLE "faixa_operacao_compressor" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_faixa_operacao_compressor" ON "faixa_operacao_compressor" FOR SELECT TO authenticated USING (true);

ALTER TABLE "classificacao_sistema_compressor" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_classificacao_sistema_compressor" ON "classificacao_sistema_compressor" FOR SELECT TO authenticated USING (true);

ALTER TABLE "lubrificante_compressor" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_lubrificante_compressor" ON "lubrificante_compressor" FOR SELECT TO authenticated USING (true);

ALTER TABLE "dados_fisicos_compressor_bitzer" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_dados_fisicos_compressor_bitzer" ON "dados_fisicos_compressor_bitzer" FOR SELECT TO authenticated USING (true);

ALTER TABLE "tabela_disjuntor_termomagnetico" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_tabela_disjuntor_termomagnetico" ON "tabela_disjuntor_termomagnetico" FOR SELECT TO authenticated USING (true);

ALTER TABLE "tabela_disjuntor_ddr" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_tabela_disjuntor_ddr" ON "tabela_disjuntor_ddr" FOR SELECT TO authenticated USING (true);

ALTER TABLE "fator_venda" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_fator_venda" ON "fator_venda" FOR SELECT TO authenticated USING (true);

ALTER TABLE "lookup_ambiente_luminotecnico" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_lookup_ambiente_luminotecnico" ON "lookup_ambiente_luminotecnico" FOR SELECT TO authenticated USING (true);

ALTER TABLE "lookup_lampada" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_lookup_lampada" ON "lookup_lampada" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_faixa_area_tabela02" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_faixa_area_tabela02" ON "cat_faixa_area_tabela02" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_modelos_expositor" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_modelos_expositor" ON "cat_modelos_expositor" FOR SELECT TO authenticated USING (true);

ALTER TABLE "forcador_linhas" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_forcador_linhas" ON "forcador_linhas" FOR SELECT TO authenticated USING (true);

ALTER TABLE "condensador_linhas" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_condensador_linhas" ON "condensador_linhas" FOR SELECT TO authenticated USING (true);

ALTER TABLE "cat_modelos_valvula" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_cat_modelos_valvula" ON "cat_modelos_valvula" FOR SELECT TO authenticated USING (true);

ALTER TABLE "uc_unidades" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_uc_unidades" ON "uc_unidades" FOR SELECT TO authenticated USING (true);

ALTER TABLE "campo_catalogo_opcao" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_campo_catalogo_opcao" ON "campo_catalogo_opcao" FOR SELECT TO authenticated USING (true);

ALTER TABLE "id_comercial" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_id_comercial" ON "id_comercial" FOR SELECT TO authenticated USING (true);

ALTER TABLE "item_composicao_mestre" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_item_composicao_mestre" ON "item_composicao_mestre" FOR SELECT TO authenticated USING (true);

ALTER TABLE "forcador_modelos" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_forcador_modelos" ON "forcador_modelos" FOR SELECT TO authenticated USING (true);

ALTER TABLE "forcador_fatores_gas" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_forcador_fatores_gas" ON "forcador_fatores_gas" FOR SELECT TO authenticated USING (true);

ALTER TABLE "condensador_modelos" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_condensador_modelos" ON "condensador_modelos" FOR SELECT TO authenticated USING (true);

ALTER TABLE "condensador_fatores" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_condensador_fatores" ON "condensador_fatores" FOR SELECT TO authenticated USING (true);

ALTER TABLE "uc_eletricas" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_uc_eletricas" ON "uc_eletricas" FOR SELECT TO authenticated USING (true);

ALTER TABLE "uc_capacidades" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_uc_capacidades" ON "uc_capacidades" FOR SELECT TO authenticated USING (true);

ALTER TABLE "forcador_capacidades" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_forcador_capacidades" ON "forcador_capacidades" FOR SELECT TO authenticated USING (true);

ALTER TABLE "forcador_eletricos" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_forcador_eletricos" ON "forcador_eletricos" FOR SELECT TO authenticated USING (true);

ALTER TABLE "forcador_fisicos" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_forcador_fisicos" ON "forcador_fisicos" FOR SELECT TO authenticated USING (true);

ALTER TABLE "forcador_dimensionais" ENABLE ROW LEVEL SECURITY;
CREATE POLICY "auth_read_forcador_dimensionais" ON "forcador_dimensionais" FOR SELECT TO authenticated USING (true);
