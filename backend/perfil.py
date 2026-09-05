# -*- coding: utf-8 -*-
"""Gancho de PERFIL DE USUÁRIO (master × comum).

Localmente (`is_master()`) continua retornando True — mantém comportamento idêntico ao anterior.

No servidor remoto, a verificação real é feita pelo dependency `_exigir_master` em
`backend/routers/admin.py`, que consulta a tabela `usuarios` no Postgres diretamente.
"""


def is_master() -> bool:
    return True
