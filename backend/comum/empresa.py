"""Status da empresa que o `comum` precisa conhecer sem importar `plataforma` (ADR 0011).

Os valores são os do enum `plataforma.Empresa.Status`; um teste garante que não divergem.
"""

# Operam normalmente (escrevem). "Plataforma e assinatura" nas regras.
STATUS_OPERANDO = frozenset({"em_teste", "ativa", "inadimplente"})
# Só leitura e exportação.
STATUS_SO_LEITURA = frozenset({"suspensa"})
