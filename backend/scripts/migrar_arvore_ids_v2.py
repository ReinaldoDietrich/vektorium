# -*- coding: utf-8 -*-
"""Troca a árvore de Ids Comerciais pra v2 (reestruturação completa, ver backend/id_comercial.py)
e realinha o id_comercial de todo catálogo já cadastrado (Forçador/UC/Condensador Remoto) pra
bater com os novos códigos, usando o mesmo mecanismo de geração (gerar_proximo_id_catalogo),
processando na ORDEM DE CADASTRO (id ascendente) — reproduz o mesmo resultado que teria saído se
os catálogos tivessem sido importados com a árvore v2 desde o início.

Não mexe em CatalogoComercial.id_comercial nem em LookupPainelPorta.id_comercial (vínculos que o
usuário cadastrou manualmente) — esses ficam com os códigos antigos (agora inválidos/órfãos) até
serem revisados manualmente na Tela D / Tela 7, exatamente como combinado.

Backup do estado anterior: ver database/carga_termica.backup_pre_arvore_ids_v2_*.db e os JSONs
database/backup_id_comercial_pre_v2_*.json / backup_codigos_<tabela>_pre_v2_*.json.

Idempotente: pode rodar de novo (limpa e recria a árvore do zero; realinha os catálogos de novo
com o mesmo resultado determinístico, já que segue sempre a mesma ordem de id)."""
from backend.database import SessionLocal
from backend import models as m
from backend import id_comercial as idc


def main():
    db = SessionLocal()

    # 1) Árvore: apaga tudo e recria do ARVORE_ID_COMERCIAL v2.
    db.query(m.IdComercial).delete()
    for ordem, (codigo, nome) in enumerate(idc.ARVORE_ID_COMERCIAL):
        db.add(m.IdComercial(codigo=codigo, nome=nome, ordem=ordem))
    db.commit()
    print(f"Árvore recriada: {len(idc.ARVORE_ID_COMERCIAL)} nós.")

    # 2) Realinha Forçador de Ar (4.2), na ordem de cadastro.
    linhas_forc = db.query(m.LinhaForcador).order_by(m.LinhaForcador.id.asc()).all()
    for linha in linhas_forc:
        fab = db.get(m.Fabricante, linha.fabricante_id)
        linha.id_comercial = idc.gerar_proximo_id_catalogo(
            db, m.LinhaForcador, "fabricante_id", linha.fabricante_id,
            fab.nome if fab else None, idc.ANCORA_FORCADOR, nome_item=linha.nome)
        db.flush()
    db.commit()
    print(f"Forçador de Ar: {len(linhas_forc)} linha(s) realinhada(s).")

    # 3) Realinha Unidade Condensadora Comercial (4.1.1), na ordem de cadastro.
    catalogos_uc = db.query(m.CatalogoUC).order_by(m.CatalogoUC.id.asc()).all()
    for cat in catalogos_uc:
        cat.id_comercial = idc.gerar_proximo_id_catalogo(
            db, m.CatalogoUC, "fabricante_uc", cat.fabricante_uc, cat.fabricante_uc, idc.ANCORA_UC,
            nome_item=cat.nome)
        db.flush()
    db.commit()
    print(f"Unidade Condensadora Comercial: {len(catalogos_uc)} catálogo(s) realinhado(s).")

    # 4) Realinha Condensador Remoto a Ar (4.4.1.x, depende do Tipo Condensador), na ordem de cadastro.
    linhas_cond = db.query(m.LinhaCondensadorRemoto).order_by(m.LinhaCondensadorRemoto.id.asc()).all()
    for linha in linhas_cond:
        fab = db.get(m.Fabricante, linha.fabricante_id)
        ancora = idc.ancora_condensador(linha.tipo_estrutura)
        linha.id_comercial = idc.gerar_proximo_id_catalogo(
            db, m.LinhaCondensadorRemoto, "fabricante_id", linha.fabricante_id,
            fab.nome if fab else None, ancora, nome_item=linha.nome)
        db.flush()
    db.commit()
    print(f"Condensador Remoto a Ar: {len(linhas_cond)} linha(s) realinhada(s).")

    db.close()


if __name__ == "__main__":
    main()
