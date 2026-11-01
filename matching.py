# coding: utf-8
"""Matching de sequencias de acordes (regra E).

Uma musica casa com uma sequencia se, e somente se:

1. a sequencia aparece como bloco contiguo alinhado a tokens da cifra; e
2. todo token da cifra pertence ao vocabulario da sequencia.

A comparacao e apenas case-insensitive (`lower()`). Nao ha enarmonia,
unificacao de sufixos, baixo invertido nem remocao de repeticoes.
"""


def corresponde(cifra_musica, acordes_sequencia):
    """Devolve True se `cifra_musica` casa com `acordes_sequencia` (regra E)."""
    musica = [acorde.lower() for acorde in cifra_musica]
    sequencia = [acorde.lower() for acorde in acordes_sequencia]

    tamanho = len(sequencia)
    if tamanho == 0 or tamanho > len(musica):
        return False

    if not any(musica[i:i + tamanho] == sequencia
               for i in range(len(musica) - tamanho + 1)):
        return False

    vocabulario = set(sequencia)
    return all(acorde in vocabulario for acorde in musica)
