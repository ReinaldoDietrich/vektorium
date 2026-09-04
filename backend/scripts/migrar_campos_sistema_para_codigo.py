# -*- coding: utf-8 -*-
"""Migração ÚNICA (aprovado 2026-08-08, "TUDO POR ID SEM EXCEÇÃO"): os 11 campos avulsos do
Sistema (Tipo Equip. Compressão, Válvula de Expansão, Estrutura, Partida, Modo Operação, Seleção
Condensador a Ar, Tipo/Fornecedor/Modelo de Automação de Linhas e de Equipamentos) + Tipo de
Comando (Projeto) passam a gravar o CÓDIGO da árvore de Ids Comerciais em vez do nome. Este script
converte, uma única vez, os valores já salvos (texto/nome) para o código correspondente, casando
com o nome ATUAL de cada nó (normalizado: minúsculo, sem espaços, pra tolerar pequenas variações de
grafia como "SoftStarter" salvo x "Soft starter" na árvore).

Campo sem correspondência encontrada na árvore fica INTOCADO (nunca inventa/apaga dado) — o usuário
precisa reabrir a Tela 1 e reselecionar manualmente esse campo depois.

Idempotente: se um valor já for um código válido da árvore (contém pelo menos um "."), não mexe."""
import sqlite3
from backend.database import DB_PATH


def _normaliza(txt):
    return (txt or "").strip().lower().replace(" ", "")


def _carregar_arvore(cur):
    cur.execute("SELECT id, codigo, nome FROM id_comercial")
    return cur.fetchall()


def _filhos_diretos(arvore, prefixo):
    out = []
    for _id, codigo, nome in arvore:
        if codigo.startswith(prefixo + ".") and "." not in codigo[len(prefixo) + 1:]:
            out.append((codigo, nome))
    return out


def _achar_codigo(arvore, prefixo, valor):
    if not valor:
        return None
    alvo = _normaliza(valor)
    for codigo, nome in _filhos_diretos(arvore, prefixo):
        if _normaliza(nome) == alvo:
            return codigo
    return None


def _ja_e_codigo(valor):
    return bool(valor) and "." in valor and all(p.isdigit() for p in valor.split("."))


def main():
    con = sqlite3.connect(DB_PATH)
    con.text_factory = lambda b: b.decode("utf-8", "replace")
    cur = con.cursor()
    arvore = _carregar_arvore(cur)

    nao_resolvidos = []

    # ---- Projeto.tipo_comando ----
    cur.execute("SELECT id, tipo_comando FROM projetos WHERE tipo_comando IS NOT NULL AND tipo_comando != ''")
    for pid, valor in cur.fetchall():
        if _ja_e_codigo(valor):
            continue
        codigo = None
        if "QD" in valor:
            codigo = "1.1.1"
        elif "QL" in valor:
            codigo = "1.1.2"
        if codigo:
            cur.execute("UPDATE projetos SET tipo_comando=? WHERE id=?", (codigo, pid))
            print(f"projeto {pid}: tipo_comando '{valor}' -> '{codigo}'")
        else:
            nao_resolvidos.append(("projeto", pid, "tipo_comando", valor))

    # ---- Sistemas ----
    cur.execute("""SELECT id, tipo_expansao, tipo_compressao, estrutura_compressao, partida, modo_operacao,
                          automacao, automacao_fabricante, modelo_controlador_equipamentos,
                          tipo_automacao_linhas, automacao_linhas_fabricante, modelo_controlador_linhas,
                          selecao_condensador_ar
                   FROM sistemas_refrigeracao""")
    sistemas = cur.fetchall()

    for row in sistemas:
        (sid, tipo_expansao, tipo_compressao, estrutura, partida, modo_operacao,
         automacao, automacao_fab, modelo_ctrl_equip,
         tipo_auto_linhas, automacao_linhas_fab, modelo_ctrl_linhas, cond_ar) = row

        updates = {}

        def resolver(campo, valor, prefixo):
            if valor is None or _ja_e_codigo(valor):
                return
            codigo = _achar_codigo(arvore, prefixo, valor)
            if codigo:
                updates[campo] = codigo
            else:
                nao_resolvidos.append(("sistema", sid, campo, valor))

        resolver("tipo_expansao", tipo_expansao, "3")
        resolver("tipo_compressao", tipo_compressao, "4.1")
        resolver("estrutura_compressao", estrutura, "4.1.2.1")
        resolver("partida", partida, "4.1.3")
        resolver("modo_operacao", modo_operacao, "4.1.4")
        resolver("selecao_condensador_ar", cond_ar, "4.4.1")
        resolver("automacao", automacao, "1.3")
        resolver("tipo_automacao_linhas", tipo_auto_linhas, "1.2")

        # automacao_fabricante depende do código de automacao já resolvido (ou já era código)
        cod_automacao = updates.get("automacao") or (automacao if _ja_e_codigo(automacao) else None)
        if cod_automacao:
            resolver("automacao_fabricante", automacao_fab, cod_automacao)
            cod_automacao_fab = updates.get("automacao_fabricante") or (automacao_fab if _ja_e_codigo(automacao_fab) else None)
            if cod_automacao_fab:
                resolver("modelo_controlador_equipamentos", modelo_ctrl_equip, cod_automacao_fab)
        elif modelo_ctrl_equip or automacao_fab:
            if automacao_fab and not _ja_e_codigo(automacao_fab):
                nao_resolvidos.append(("sistema", sid, "automacao_fabricante", automacao_fab))
            if modelo_ctrl_equip and not _ja_e_codigo(modelo_ctrl_equip):
                nao_resolvidos.append(("sistema", sid, "modelo_controlador_equipamentos", modelo_ctrl_equip))

        # automacao_linhas_fabricante depende do código de tipo_automacao_linhas já resolvido
        cod_tipo_linhas = updates.get("tipo_automacao_linhas") or (tipo_auto_linhas if _ja_e_codigo(tipo_auto_linhas) else None)
        if cod_tipo_linhas:
            resolver("automacao_linhas_fabricante", automacao_linhas_fab, cod_tipo_linhas)
            cod_linhas_fab = updates.get("automacao_linhas_fabricante") or (automacao_linhas_fab if _ja_e_codigo(automacao_linhas_fab) else None)
            if cod_linhas_fab:
                resolver("modelo_controlador_linhas", modelo_ctrl_linhas, cod_linhas_fab)
        elif modelo_ctrl_linhas or automacao_linhas_fab:
            if automacao_linhas_fab and not _ja_e_codigo(automacao_linhas_fab):
                nao_resolvidos.append(("sistema", sid, "automacao_linhas_fabricante", automacao_linhas_fab))
            if modelo_ctrl_linhas and not _ja_e_codigo(modelo_ctrl_linhas):
                nao_resolvidos.append(("sistema", sid, "modelo_controlador_linhas", modelo_ctrl_linhas))

        if updates:
            set_clause = ", ".join(f"{campo}=?" for campo in updates)
            cur.execute(f"UPDATE sistemas_refrigeracao SET {set_clause} WHERE id=?",
                        (*updates.values(), sid))
            print(f"sistema {sid}: {updates}")

    con.commit()
    con.close()

    if nao_resolvidos:
        print("\nCampos SEM correspondência na árvore (deixados intocados, texto original mantido):")
        for tipo, oid, campo, valor in nao_resolvidos:
            print(f"  {tipo} {oid}.{campo} = '{valor}'")
    else:
        print("\nTodos os campos foram resolvidos.")


if __name__ == "__main__":
    main()
