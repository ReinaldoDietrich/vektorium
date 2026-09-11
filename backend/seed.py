"""Popula o banco com:
  (A) dados REAIS já fechados no projeto (Faixas de Trocas de Ar e Classes de Produto, fonte
      Resfriando/Heatcraft; calor específico de embalagem, fonte ASHRAE citada no escopo;
      4 produtos consultados na planilha real Banco_Produtos_Camaras_v1.xlsx; 19 setores de
      expositor já definidos no script);
  (B) um pequeno conjunto de EXEMPLO/TESTE (3-5 linhas) nos catálogos que ainda aguardam a
      tabela de origem real do usuário (Fase 6) — todos marcados "(exemplo/teste)" para não
      serem confundidos com dado validado de mercado.
Idempotente: não duplica se já houver dados.
"""
import json
import os
from .database import SessionLocal, engine, Base
from . import models as m

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(m.FaixaTrocasAr).count() == 0:
            faixas = [
                ("Conservação de congelados", 40, 80),
                ("Conservação de resfriados", 40, 80),
                ("Câmaras de corte", 20, 30),
                ("Câmara de resfriamento de carne", 80, 120),
                ("Maturação de banana", 120, 200),
                ("Armazenagem de frutas/vegetais", 30, 60),
                ("Túneis de congelamento rápido", 150, 300),
                ("Salas de processo", 20, 30),
                ("Armazenagem de carne sem empacotar", 30, 60),
            ]
            for nome, mn, mx in faixas:
                db.add(m.FaixaTrocasAr(tipo_aplicacao=nome, minimo=mn, maximo=mx))

        if db.query(m.ClasseProduto).count() == 0:
            # Classe 1 (fonte Resfriando) + classes 2-5 conforme tabela "Recomendação para DT" do
            # fabricante (imagem fornecida pelo usuário) — usada também como UR interna de
            # infiltração (Q4) por câmara, no lugar de um valor global fixo.
            classes = [
                (1, 4, 5, 90, 90, "Vegetais, flores, gelo sem embalagem"),
                (2, 6, 7, 80, 85, "Armazenamentos de frigorificados em geral refrigeração, alimentos e vegetais embalados, frutas e similares"),
                (3, 7, 9, 65, 80, "Cerveja, vinho, produtos farmacêuticos, batatas, cebolas, frutas de casca dura e produtos embalados"),
                (4, 9, 10, 50, 65, "Sala de preparo, processo e cortes"),
                (5, 11, 14, 50, 65, "Armazém de cerveja, doces e armazenagem de filmes"),
            ]
            for classe, dtmin, dtmax, urmin, urmax, aplic in classes:
                db.add(m.ClasseProduto(classe=classe, dt_evap_min=dtmin, dt_evap_max=dtmax,
                                        ur_min=urmin, ur_max=urmax, aplicacao=aplic))

        if db.query(m.TipoEmbalagem).count() == 0:
            # calor específico convertido de kJ/kg.K para kcal/kg.K (÷4,1868), fonte: Script_Implementacao
            for nome, kcal in [("Nenhuma", 0.0), ("Madeira", 0.406), ("Papelão", 0.3344), ("Plástico", 0.3822)]:
                db.add(m.TipoEmbalagem(nome=nome, calor_especifico=kcal))

        if db.query(m.SetorExpositor).count() == 0:
            setores = ["Açougue", "Bebidas", "Confeitaria", "Congelados", "Doces", "Fatiados",
                       "Fiambreria", "FLV", "Frios", "Laticínios", "Margarinas", "Massas",
                       "Padaria", "Peixaria", "Pizzas", "Queijos", "Rotisseria", "Salsicharia", "Sorvetes"]
            for s in setores:
                db.add(m.SetorExpositor(nome=s))

        if db.query(m.Produto).count() == 0:
            # 4 itens reais consultados em Banco_Produtos_Camaras_v1.xlsx (mesmos do mockup validado).
            # As demais 205 linhas da planilha NÃO foram importadas — aguardando sua confirmação
            # de que a revisão (linhas "tabela antiga"/"estimativa") já está fechada (Fase 6).
            produtos = [
                dict(nome="Carne de vaca", temp_conservacao="0 a -1", umidade_relativa="88-92",
                     tempo_conservacao="1-6 meses", pct_agua=67, ponto_congelamento=-1.95,
                     calor_esp_antes=0.77, calor_esp_depois=0.41, calor_latente=55,
                     calor_respiracao=None, classe=1, fonte_status="Resfriando"),
                dict(nome="Frango fresco", temp_conservacao="0", umidade_relativa="85-90",
                     tempo_conservacao="1 semana", pct_agua=74, ponto_congelamento=-2.8,
                     calor_esp_antes=0.79, calor_esp_depois=0.42, calor_latente=59,
                     calor_respiracao=None, classe=1, fonte_status="Resfriando"),
                dict(nome="Maçã", temp_conservacao="-1 a 4", umidade_relativa="90",
                     tempo_conservacao="3-8 meses", pct_agua=84.1, ponto_congelamento=-1.5,
                     calor_esp_antes=0.87, calor_esp_depois=0.45, calor_latente=59,
                     calor_respiracao=0.25, classe=1, fonte_status="Resfriando + Tabela antiga (respiração)"),
                dict(nome="Peixe magro", temp_conservacao=None, umidade_relativa=None,
                     tempo_conservacao=None, pct_agua=None, ponto_congelamento=-1.7,
                     calor_esp_antes=0.86, calor_esp_depois=0.45, calor_latente=68,
                     calor_respiracao=0, classe=None, fonte_status="Tabela antiga (validar contra literatura)"),
            ]
            for p in produtos:
                db.add(m.Produto(**p))

        # ---------- Painéis Isolantes (Kingspan, fornecedor padrão único — ver Escopo_Tela1_Tela2.docx) ----------
        if db.query(m.IsolamentoParedeTeto).count() == 0:
            for mat, esp, u in [("PIR 50mm", 50, 0.38), ("PIR 70mm", 70, 0.27), ("PIR 100mm", 100, 0.19),
                                 ("PIR 120mm", 120, 0.15), ("PIR 150mm", 150, 0.13), ("PIR 200mm", 200, 0.09),
                                 ("EPS 50mm", 50, 0.60), ("EPS 100mm", 100, 0.30), ("EPS 150mm", 150, 0.20),
                                 ("EPS 200mm", 200, 0.15), ("EPS 250mm", 250, 0.12)]:
                db.add(m.IsolamentoParedeTeto(material=mat, espessura_mm=esp, u_valor=u))

        if db.query(m.IsolamentoPiso).count() == 0:
            for mat, esp, u, so_acima_zero in [
                ("PIR 50mm (placa única)", 50, 0.38, False),
                ("PIR 100mm (50+50)", 100, 0.19, False),
                ("PIR 120mm (60+60)", 120, 0.15, False),
                ("PIR 150mm (75+75)", 150, 0.13, False),
                ("EPS 50mm (placa única)", 50, 0.60, False),
                ("EPS 150mm (75+75)", 150, 0.20, False),
                ("EPS 200mm (100+100)", 200, 0.15, False),
                ("Concreto (sem isolante)", None, 1.03, True),
            ]:
                db.add(m.IsolamentoPiso(material=mat, espessura_mm=esp, u_valor=u,
                                         valido_apenas_acima_zero=so_acima_zero))

        # TipoEquipamento — estimativas de mercado (não normativas, fonte não citável em norma
        # específica) para potência/fator de calor rejeitado/fator de simultaneidade por tipo de
        # equipamento comum em fundo de loja e logística. Editável em Configurações — ajustar
        # conforme dado real do fabricante sempre que disponível. Cenário 1 ASHRAE (motor e carga
        # no mesmo ambiente): calor = potência x fator_calor_rejeitado x fator_simultaneidade.
        if db.query(m.TipoEquipamento).count() == 0:
            equipamentos = [
                ("Moedor de Carne / Máquina de Moagem", 3100, 1.00, 0.50),
                ("Serra Fita", 1650, 1.00, 0.40),
                ("Fatiadora de Frios", 400, 1.00, 0.60),
                ("Amaciador de Bifes", 560, 1.00, 0.25),
                ("Embaladora/Seladora Manual", 1000, 0.85, 0.70),
                ("Seladora Automática (Termoencolhível)", 5000, 0.85, 0.60),
                ("Lavadora de Caixas/Louças", 4500, 0.60, 0.40),
                ("Compactador de Papelão/Plástico", 5600, 1.00, 0.15),
                ("Inversor de Frequência (consumo típico 3kW considerado)", 3000, 0.04, 0.90),
                ("Esteira Transportadora/Sorger", 3500, 1.00, 0.75),
                ("Carregador de Bateria (Empilhadeiras)", 8000, 0.15, 0.65),
                ("Terminal de Computador/Coletor (Fixo)", 200, 1.00, 1.00),
                ("Empilhadeira Elétrica (operação)", 10000, 1.00, 1.00),
                ("Transpaleteira Elétrica", 2000, 1.00, 1.00),
                ("Balança Industrial", 60, 1.00, 1.00),
                ("Paletizadora (Filme)", 3750, 1.00, 1.00),
                # Tanques pasteurizadores e quebradoras de ovos — potência considerada = Calor
                # Sensível dos Motores + Radiação Térmica do Equipamento (ponto médio da faixa).
                ("Tanque Pasteurizador 500L (Lote, Elétrico/Camisa Dupla)", 3450, 1.00, 1.00),
                ("Tanque Pasteurizador 1.000L (Lote, Elétrico/Camisa Dupla)", 5150, 1.00, 1.00),
                ("Tanque Pasteurizador 4.000L/h (Contínuo, SKID Placas/Caldeira Ext.)", 14850, 1.00, 1.00),
                ("Tanque Pasteurizador 10.000L/h (Contínuo, SKID Placas/Caldeira Ext.)", 29750, 1.00, 1.00),
                ("Quebradora de Ovos ~3.000-6.000 ovos/h", 600, 1.00, 1.00),
                ("Quebradora de Ovos ~12.000-20.000 ovos/h", 1850, 1.00, 1.00),
                ("Quebradora de Ovos ~30.000-45.000 ovos/h", 4750, 1.00, 1.00),
            ]
            for nome, pot, fu, fs in equipamentos:
                db.add(m.TipoEquipamento(nome=nome, potencia_tipica_w=pot,
                                          fator_calor_rejeitado=fu, fator_simultaneidade=fs))

        # Condição Climática (INMET, Normal Climatológica 1991-2020) é populada por script próprio
        # (backend/scripts/importar_climatologia.py), não por seed — são ~190 estações reais.

        # Tabela 02 real do usuário ("Tabela Câmaras Simples.xlsx") — a carga não é um fator linear
        # por m², é consultada por faixa de área (ver FaixaAreaTabela02 logo abaixo). A ordem dos
        # 7 tipos aqui precisa bater com a ordem das colunas 1-7 de backend/data/tabela02_faixas.json.
        if db.query(m.TabelaTipo02).count() == 0:
            tipos = [
                ("C. Carnes, peixes ou frangos", -5),
                ("C. Laticínios, salgados, padaria, frios ou pizzas", 2),
                ("C. FLV/horti, lixo, ossos, prep. carnes aberto", 8),
                ("Prep. carnes fechado ou prep. diversos aberto", 10),
                ("Prep. div. fech., ante-câmara ou corredor refrig.", 12),
                ("C. Congelados com ante-câmara", -22),
                ("C. Congelados sem ante-câmara", -25),
            ]
            tabela02_ids = []
            for tipo, ti in tipos:
                obj = m.TabelaTipo02(tipo=tipo, temp_interna_default=ti)
                db.add(obj)
                db.flush()
                tabela02_ids.append(obj.id)

            if db.query(m.FaixaAreaTabela02).count() == 0:
                with open(os.path.join(_DATA_DIR, "tabela02_faixas.json"), encoding="utf-8") as f:
                    faixas_json = json.load(f)
                for faixa in faixas_json:
                    for tabela02_id, valor in zip(tabela02_ids, faixa["valores"]):
                        db.add(m.FaixaAreaTabela02(tabela02_id=tabela02_id, area_de=faixa["area_de"],
                                                    area_ate=faixa["area_ate"], carga_kcal_h=valor))

        if db.query(m.FatorAltura).count() == 0:
            for ate, fator in [(2.49, 0.70), (2.74, 0.80), (2.99, 0.90), (3.24, 1.00), (3.49, 1.05), (4.00, 1.12)]:
                db.add(m.FatorAltura(pe_direito_ate_m=ate, fator=fator))

        if db.query(m.FatorInsolacao).count() == 0:
            for orientacao, fator in [("Leste/Oeste (maior exposição)", 1.10), ("Norte/Sul (menor exposição)", 1.07),
                                       ("Teto/Telhado (maior exposição)", 1.18), ("Sombreado/interno", 1.0)]:
                db.add(m.FatorInsolacao(orientacao=orientacao, fator=fator))

        if db.query(m.ConfiguracaoGlobal).count() == 0:
            # pct_ajuste_simples removido: o cálculo simples é só carga tabelada (Tabela 02, por
            # faixa de área) x fator_altura x (1+fator_seguranca/100) — sem ajuste percentual
            # global extra.
            # fator_majoracao_insolacao removido: o cálculo agora usa a média da tabela
            # FatorInsolacao (por orientação), não um valor global único.
            # ur_interna_infiltracao removido: passa a vir da Classe do Produto da própria câmara.
            # ur_externa_infiltracao removido: passa a vir da estação climatológica do projeto (Tela 1).
            db.add(m.ConfiguracaoGlobal(chave="potencia_dreno_wm", valor=0,
                                         descricao="Potência da resistência de dreno (W/m) — aparece na Compilação (Res. Dreno)",
                                         pendente_confirmacao=True))
            db.add(m.ConfiguracaoGlobal(chave="potencia_portas_wm", valor=0,
                                         descricao="Potência da resistência de portas (W/m) — multiplicado pelo perímetro do vão "
                                                    "(2×altura + 2×largura) de cada câmara. Aparece na Compilação (Res. Portas)",
                                         pendente_confirmacao=True))
            db.add(m.ConfiguracaoGlobal(chave="comprimento_dreno_m", valor=0,
                                         descricao="Comprimento de resistência de dreno considerado por evaporador (m)",
                                         pendente_confirmacao=True))
            db.add(m.ConfiguracaoGlobal(chave="reducao_eev_pct", valor=15,
                                         descricao="Redução de consumo do compressor por Válvula de Expansão Eletrônica (%) — "
                                                    "global, único para todo o app (não varia por sistema)"))
            db.add(m.ConfiguracaoGlobal(chave="reducao_controle_capacidade_pct", valor=18,
                                         descricao="Redução MÁXIMA de consumo do compressor por Controle de Capacidade "
                                                    "(descarregamento mecânico de cilindros — Modo Operação), aplicada quando "
                                                    "o Sistema opera no piso de 35% de carga — decresce linearmente até 0% em "
                                                    "100% de carga. Faixa típica de literatura (descarregamento mecânico vs. "
                                                    "liga-desliga): 15%-20% — ver calculo_consumo.py"))
            db.add(m.ConfiguracaoGlobal(chave="reducao_inversor_pct", valor=40,
                                         descricao="Redução MÁXIMA de consumo do compressor por Inversor de Frequência (VFD — "
                                                    "Modo Operação), aplicada quando o Sistema opera no piso de 20% de carga — "
                                                    "decresce linearmente até 0% em 100% de carga. Faixa típica de literatura "
                                                    "(VFD vs. liga-desliga, ganho de IEER): 30%-50% — ver calculo_consumo.py"))

        db.commit()

        # Fabricantes/Forçadores/Válvulas de exemplo/teste foram removidos deste seed em 2026-06-30:
        # o usuário já importa catálogos reais (Excel/Word) e não quer nenhum dado fake reaparecendo
        # depois de limpar o banco — ver [[projeto-carga-termica]] na memória.

        # FatorCorrecaoForcador (global, por gás/fpi) foi substituído por FatorCorrecaoGasForcador
        # (por linha — cada fabricante publica o seu fator de correção de gás, não é um valor
        # único pro sistema inteiro).

        # BancoExpositor/ModeloExpositor (exemplo/teste) removido do seed em 2026-07-03 — usuário
        # cadastra os bancos/modelos reais manualmente na tela Configuração.

        if db.query(m.CatalogoVersao).count() == 0:
            _TABELAS_CATALOGO = [
                "cat_fabricantes", "id_comercial", "forcador_linhas", "forcador_modelos",
                "forcador_capacidades", "forcador_eletricos", "forcador_fisicos",
                "forcador_dimensionais", "forcador_fatores_gas", "forcador_importacoes",
                "uc_catalogos", "uc_unidades", "uc_eletricas", "uc_capacidades",
                "condensador_linhas", "condensador_modelos", "condensador_fatores",
                "condensador_importacoes", "polinomio_compressor",
                "valor_nominal_compressor", "faixa_operacao_compressor",
                "catalogo_comercial", "cat_modelos_valvula", "campo_catalogo",
                "campo_catalogo_opcao", "lookup_lampada",
            ]
            for tabela in _TABELAS_CATALOGO:
                db.add(m.CatalogoVersao(tabela=tabela, versao=1))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
