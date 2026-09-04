# -*- coding: utf-8 -*-
"""Migração: separa "Partida" (informativo, Direta/Dividida/SoftStarter) de "Modo Operação"
(Controle de Capacidade/Inversor de Frequência, com fator de redução de consumo).

Contexto (discussão real 2026-07-17): o campo antigo `controle_capacidade` misturava partida
(como o compressor liga) com operação (como ele modula em regime) num único par de campos
inconsistente — `partida` tinha "Inversor de Frequência" como opção, e só "Inversor" combinado
com o campo separado `controle_capacidade` fazia sentido de verdade. Pesquisa de literatura
confirmou que partida (Direta/Dividida/SoftStarter) não afeta consumo em regime — só o pico de
corrente na partida — então vira campo puramente informativo. Controle de Capacidade e Inversor de
Frequência viram um único campo "Modo Operação", cada um com seu próprio fator de redução.

O que faz:
1. Renomeia sistemas_refrigeracao.controle_capacidade -> modo_operacao (RENAME COLUMN).
2. Migra os dados existentes:
   - partida antigo continha "Inversor de Frequência" (puro ou + SoftStarter) -> isso vira
     modo_operacao = "Inversor de Frequência". A parte "SoftStarter" (se houver) é preservada em
     partida; a parte "Inversor de Frequência" é removida de partida (moveu de campo).
   - controle_capacidade antigo = "Controle capac. 35% a 100%" -> modo_operacao = "Controle de
     Capacidade".
   - Se AMBOS os sinais antigos existiam ao mesmo tempo num sistema (partida tinha "Inversor de
     Frequência" E controle_capacidade já era "Controle capac. 35% a 100%") — dado antigo
     inconsistente/ambíguo (dois modos de operação diferentes indicados pro mesmo sistema). Nesse
     caso a migração prioriza o controle_capacidade explícito (sinal mais forte, foi selecionado
     deliberadamente à parte) e marca `precisa_revisar = True` pra o usuário confirmar manualmente.
   - partida sem "Inversor"/"SoftStarter" reconhecível fica em branco (não dá pra inferir com
     segurança se era Direta ou Dividida a partir do dado antigo) — usuário reseleciona.
3. Atualiza os valores dos fatores de redução (reducao_controle_capacidade_pct: 25 -> 18) e insere
   o novo fator reducao_inversor_pct (default 40), só se ainda não existir.
4. Atualiza a árvore id_comercial (2.2.2.x Partida + nova 2.2.4.x Modo Operação) — remove os nós
   antigos de Inversor dentro de Partida (confirmado sem CatalogoComercial anexado) e insere os
   novos nós.

Idempotente. Rodar: python -m backend.scripts.migrar_modo_operacao <caminho_db>
"""
import sys
import sqlite3


def _colunas(cur, tabela):
    cur.execute(f"PRAGMA table_info({tabela})")
    return {row[1] for row in cur.fetchall()}


def migrar(caminho_db):
    con = sqlite3.connect(caminho_db)
    cur = con.cursor()

    colunas = _colunas(cur, "sistemas_refrigeracao")
    if "modo_operacao" not in colunas:
        if "controle_capacidade" in colunas:
            cur.execute("ALTER TABLE sistemas_refrigeracao RENAME COLUMN controle_capacidade TO modo_operacao")
            print("sistemas_refrigeracao.controle_capacidade renomeada para modo_operacao.")
        else:
            cur.execute("ALTER TABLE sistemas_refrigeracao ADD COLUMN modo_operacao TEXT")
            print("sistemas_refrigeracao.modo_operacao criada.")
    else:
        print("sistemas_refrigeracao.modo_operacao já existe — pulando criação/rename.")

    cur.execute("SELECT id, nome, partida, modo_operacao, precisa_revisar FROM sistemas_refrigeracao")
    linhas = cur.fetchall()
    total_migrados = 0
    total_conflito = 0
    for sid, nome, partida_antiga, modo_atual, precisa_revisar in linhas:
        partida_antiga = partida_antiga or ""
        tem_inversor = "Inversor" in partida_antiga
        tem_softstarter = "SoftStarter" in partida_antiga
        ja_era_controle_cap = modo_atual == "Controle capac. 35% a 100%"

        # Só migra sistemas cujo dado antigo ainda está no formato pré-migração (partida com
        # "Inversor", ou modo_operacao ainda com o valor textual antigo do Controle de Capacidade).
        if not tem_inversor and not ja_era_controle_cap:
            continue  # já migrado, ou sistema sem esses campos preenchidos — nada a fazer

        novo_modo = None
        novo_precisa_revisar = precisa_revisar
        if ja_era_controle_cap and tem_inversor:
            novo_modo = "Controle de Capacidade"
            novo_precisa_revisar = 1
            total_conflito += 1
            print(f"  CONFLITO sistema id={sid} nome={nome!r}: tinha Partida com 'Inversor de "
                  f"Frequência' E Modo Operação 'Controle capac. 35% a 100%' ao mesmo tempo — "
                  f"mantido Modo Operação = Controle de Capacidade, marcado precisa_revisar.")
        elif ja_era_controle_cap:
            novo_modo = "Controle de Capacidade"
        elif tem_inversor:
            novo_modo = "Inversor de Frequência"

        nova_partida = "SoftStarter" if tem_softstarter else None

        cur.execute("UPDATE sistemas_refrigeracao SET partida=?, modo_operacao=?, precisa_revisar=? WHERE id=?",
                    (nova_partida, novo_modo, novo_precisa_revisar, sid))
        total_migrados += 1
        print(f"  sistema id={sid} nome={nome!r}: partida {partida_antiga!r} -> {nova_partida!r} | "
              f"modo_operacao -> {novo_modo!r}")

    print(f"{total_migrados} sistema(s) migrado(s) ({total_conflito} com conflito, marcados p/ revisão).")

    # ---- Fatores de redução (Configurações Globais) ----
    cur.execute("SELECT valor FROM configuracao_global WHERE chave = 'reducao_controle_capacidade_pct'")
    row = cur.fetchone()
    if row is not None:
        if row[0] == 25:
            cur.execute("UPDATE configuracao_global SET valor=18, "
                        "descricao='Redução MÁXIMA de consumo do compressor por Controle de Capacidade "
                        "(descarregamento mecânico de cilindros — Modo Operação), aplicada quando o Sistema "
                        "opera no piso de 35% de carga — decresce linearmente até 0% em 100% de carga. Faixa "
                        "típica de literatura (descarregamento mecânico vs. liga-desliga): 15%-20% — ver "
                        "calculo_consumo.py' WHERE chave='reducao_controle_capacidade_pct'")
            print("configuracao_global.reducao_controle_capacidade_pct atualizada de 25 para 18 (valor default "
                  "antigo -> novo valor calibrado por pesquisa; se você já tinha alterado esse valor manualmente, "
                  "ele foi PRESERVADO e não sobrescrito).")
        else:
            print(f"configuracao_global.reducao_controle_capacidade_pct já tem valor customizado ({row[0]}) — não sobrescrita.")
    else:
        cur.execute("INSERT INTO configuracao_global (chave, valor, descricao, pendente_confirmacao) VALUES (?, ?, ?, ?)",
                     ("reducao_controle_capacidade_pct", 18,
                      "Redução MÁXIMA de consumo do compressor por Controle de Capacidade (descarregamento "
                      "mecânico de cilindros — Modo Operação), aplicada quando o Sistema opera no piso de 35% "
                      "de carga — decresce linearmente até 0% em 100% de carga. Faixa típica de literatura "
                      "(descarregamento mecânico vs. liga-desliga): 15%-20% — ver calculo_consumo.py", 0))
        print("configuracao_global.reducao_controle_capacidade_pct criada com valor 18.")

    cur.execute("SELECT id FROM configuracao_global WHERE chave = 'reducao_inversor_pct'")
    if cur.fetchone() is None:
        cur.execute("INSERT INTO configuracao_global (chave, valor, descricao, pendente_confirmacao) VALUES (?, ?, ?, ?)",
                     ("reducao_inversor_pct", 40,
                      "Redução MÁXIMA de consumo do compressor por Inversor de Frequência (VFD — Modo "
                      "Operação), aplicada quando o Sistema opera no piso de 20% de carga — decresce "
                      "linearmente até 0% em 100% de carga. Faixa típica de literatura (VFD vs. liga-desliga, "
                      "ganho de IEER): 30%-50% — ver calculo_consumo.py", 0))
        print("configuracao_global.reducao_inversor_pct criada com valor 40.")
    else:
        print("configuracao_global.reducao_inversor_pct já existia — não sobrescrita.")

    # ---- Árvore id_comercial (2.2.2.x Partida + nova 2.2.4.x Modo Operação) ----
    cur.execute("SELECT id FROM catalogo_comercial WHERE id_comercial IN ('2.2.2.3','2.2.2.4')")
    anexados = cur.fetchall()
    if anexados:
        print(f"AVISO: {len(anexados)} item(ns) de CatalogoComercial ainda ligado(s) aos códigos antigos "
              f"2.2.2.3/2.2.2.4 — NÃO removendo esses nós da árvore pra não perder texto/foto cadastrado. "
              f"Revise manualmente em Configurações -> Ids Comerciais.")
    # Reordenação 2.2.2.x: Direta(.1) fica, SoftStarter sai de .2 pra .3 (abrindo espaço pra
    # "Dividida" nova em .2), Inversor de Frequência (.3 antigo) e Inversor+SoftStarter (.4) somem
    # — sempre em ordem que evita colisão de UNIQUE(codigo). Só remove se nada de CatalogoComercial
    # estiver anexado (checado acima).
    if not anexados:
        cur.execute("DELETE FROM id_comercial WHERE codigo IN ('2.2.2.3','2.2.2.4') AND nome LIKE 'Inversor%'")
        if cur.rowcount:
            print(f"{cur.rowcount} nó(s) antigo(s) de Inversor removido(s) de id_comercial (2.2.2.3/2.2.2.4).")
    cur.execute("UPDATE id_comercial SET codigo='2.2.2.3' WHERE codigo='2.2.2.2' AND nome='SoftStarter'")
    cur.execute("SELECT codigo FROM id_comercial WHERE codigo='2.2.2.2'")
    if cur.fetchone() is None:
        cur.execute("INSERT INTO id_comercial (codigo, nome, ordem) VALUES ('2.2.2.2', 'Dividida', 12)")
        print("id_comercial 2.2.2.2 'Dividida' inserido, SoftStarter movido pra 2.2.2.3.")
    cur.execute("SELECT codigo, nome FROM id_comercial WHERE codigo LIKE '2.2.2%' ORDER BY codigo")
    print("Estado atual 2.2.2.x:", cur.fetchall())

    cur.execute("SELECT codigo FROM id_comercial WHERE codigo = '2.2.4'")
    if cur.fetchone() is None:
        cur.execute("INSERT INTO id_comercial (codigo, nome, ordem) VALUES ('2.2.4', 'Modo Operação', 15)")
        cur.execute("INSERT INTO id_comercial (codigo, nome, ordem) VALUES ('2.2.4.1', 'Controle de Capacidade', 16)")
        cur.execute("INSERT INTO id_comercial (codigo, nome, ordem) VALUES ('2.2.4.2', 'Inversor de Frequência', 17)")
        print("id_comercial 2.2.4.x 'Modo Operação' inserido (Controle de Capacidade / Inversor de Frequência).")
    else:
        print("id_comercial 2.2.4 já existia — não sobrescrita.")

    con.commit()
    con.close()
    print("Migração concluída.")


if __name__ == "__main__":
    caminho = sys.argv[1] if len(sys.argv) > 1 else "database/carga_termica.db"
    migrar(caminho)
