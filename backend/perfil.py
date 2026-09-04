# -*- coding: utf-8 -*-
"""Gancho de PERFIL DE USUÁRIO (master × comum).

HOJE o app é LOCAL e mono-usuário → `is_master()` sempre retorna True, então tudo fica liberado e
o comportamento é idêntico ao de antes deste gancho existir. Nada muda no funcionamento atual.

Quando o app for para o ONLINE (multi-usuário / licenciamento), trocar SÓ este ponto por uma
verificação real de autenticação/perfil. Todos os pontos que futuramente serão restritos a master
(card de criação de cadastro comercial, campo "Tipo Cadastro", criação de IDs personalizados etc.)
devem chamar `is_master()` — assim, ao virar online, basta alterar aqui e todos os pontos passam a
respeitar o perfil automaticamente.
"""


def is_master() -> bool:
    # TODO(online): substituir por verificação real de autenticação/perfil do usuário logado.
    return True
