#!/usr/bin/env python3
# coding: utf-8
"""Valida definicoes de matching de sequencias contra o dataset atual.

Este script reproduz os numeros da pesquisa em
`docs/features/sequencias-customizadas/01-research.md`. Ele NAO faz parte da
aplicacao: le o CSV do mesmo jeito que `main.py` e compara definicoes
candidatas de "a sequencia X aparece na musica Y" com a tag pre-computada na
coluna SEQ_FAMOSA.

Uso:
    python3 scripts/validar_matching.py [caminho_do_csv]

Requer apenas a biblioteca padrao (Python 3). Nao importa Flask nem `main.py`,
para poder rodar sem as dependencias da aplicacao instaladas.
"""

import argparse
import re
import sys
from collections import Counter

CSV_PADRAO = 'data/top/dataset_final.csv'

# Colunas do CSV, iguais a main.py:26-34.
ARTISTA_ID = 0
MUSICA_ID = 1
ARTISTA = 2
MUSICA = 3
GENERO = 4
POPULARIDADE = 5
TOM = 6
SEQ_FAMOSA = 7
CIFRA = 8

# Sequencias na ordem em que generate_data_set.py:8 as avalia. O indice nesta
# lista e o valor gravado na coluna SEQ_FAMOSA.
SEQUENCIAS = [
    ('BmGDA', ['Bm', 'G', 'D', 'A']),
    ('CGAmF', ['C', 'G', 'Am', 'F']),
    ('EmG', ['Em', 'G']),
    ('CA7DmG7', ['C', 'A7', 'Dm', 'G7']),
    ('GmF', ['Gm', 'F']),
    ('CC7FFm', ['C', 'C7', 'F', 'Fm']),
]


def limpa_cifra(raw_cifra):
    """Copia de main.py:11-23."""
    cifra = []
    for m in raw_cifra:
        if m.strip() != '':
            if '|' in m:
                acorde = m.split('|')[0].split()[0]
                cifra.append(acorde)
            else:
                cifra += [token for token in m.split()]
    return cifra


def carregar(caminho, tokenizar=True):
    """Le o CSV replicando main.py:49-63.

    Devolve uma lista de dicts com os campos usados na validacao. O arquivo nao
    tem cabecalho, e `main.py:50` descarta a primeira linha de dados com
    `f.readline()` — o mesmo e feito aqui.

    Com `tokenizar=False` a cifra e apenas `split(';')` do campo cru, que e como
    `generate_data_set.py:16` enxergava a musica no scraping. Serve para medir
    quanto `limpa_cifra` muda a tokenizacao.
    """
    linhas = []
    with open(caminho, encoding='utf-8', errors='replace') as f:
        f.readline()  # main.py:50 — descarta a 1a linha de dados
        for line in f:
            # main.py:53 — remove aspas e TODAS as ocorrencias de 'NA'
            line = line.replace('"', '').replace('NA', '')[:-1]
            campos = line.split(',')
            if len(campos) < 9:
                continue
            cifra = campos[CIFRA]
            if cifra == '':
                cifra = []
            elif tokenizar:
                cifra = limpa_cifra(cifra.split(';'))
            else:
                cifra = cifra.split(';')
            linhas.append({
                'id': '%s_%s' % (campos[ARTISTA_ID], campos[MUSICA_ID]),
                'artista': campos[ARTISTA],
                'musica': campos[MUSICA],
                'tag': campos[SEQ_FAMOSA].split(';') if campos[SEQ_FAMOSA] else [],
                'cifra': cifra,
            })
    return linhas


# ---------------------------------------------------------------------------
# Definicoes candidatas. Todas recebem (acordes_da_musica, sequencia) e
# devolvem bool. A comparacao de caixa e sempre case-insensitive, como em
# generate_data_set.py:12.
# ---------------------------------------------------------------------------

def _uniao(acordes):
    return ';'.join(acordes).lower()


def a_contigua(acordes, seq):
    """A. Sequencia aparece como bloco contiguo no texto unido por ';'."""
    return _uniao(seq) in _uniao(acordes)


def b_contigua_dedup(acordes, seq):
    """B. Igual a A, mas sobre os acordes da musica sem repeticao."""
    return _uniao(seq) in _uniao(list(dict.fromkeys(acordes)))


def c_conjunto(acordes, seq):
    """C. Todo acorde da sequencia aparece na musica; ordem ignorada."""
    return {a.lower() for a in seq}.issubset({a.lower() for a in acordes})


def d_subsequencia(acordes, seq):
    """D. Sequencia aparece em ordem, mas nao necessariamente contigua."""
    alvo = [a.lower() for a in seq]
    i = 0
    for acorde in acordes:
        if i < len(alvo) and acorde.lower() == alvo[i]:
            i += 1
    return i == len(alvo)


def e_contigua_vocabulario_fechado(acordes, seq):
    """E. Bloco contiguo E todo acorde da musica pertence a sequencia.

    E a semantica de generate_data_set.py:12-20 — o loop de la percorre os
    acordes da MUSICA (`acorde.split(';')`), nao os da sequencia.
    """
    texto = _uniao(acordes)
    if _uniao(seq) not in texto:
        return False
    vocabulario = {a.lower() for a in seq}
    return all(acorde in vocabulario for acorde in texto.split(';'))


def e_alinhada_a_tokens(acordes, seq):
    """Variante de E que exige bloco contiguo alinhado a tokens.

    A checagem por substring de E aceita, em tese, casamento no meio de um
    token ('m;g' e substring de 'bm;g'). Esta variante elimina esse caso.
    """
    tokens = [a.lower() for a in acordes]
    alvo = [a.lower() for a in seq]
    k = len(alvo)
    if not any(tokens[i:i + k] == alvo for i in range(len(tokens) - k + 1)):
        return False
    vocabulario = set(alvo)
    return all(t in vocabulario for t in tokens)


CANDIDATAS = [
    ('A. contigua (substring)', a_contigua),
    ('B. contigua + acordes deduplicados', b_contigua_dedup),
    ('C. conjunto (ordem ignorada)', c_conjunto),
    ('D. subsequencia ordenada', d_subsequencia),
    ('E. contigua + vocabulario fechado', e_contigua_vocabulario_fechado),
]


# ---------------------------------------------------------------------------
# Normalizacao de acordes (usada na secao de trade-offs)
# ---------------------------------------------------------------------------

RAIZ = re.compile(r'^([A-Ga-g][#b]?)(.*)$')


def normaliza_setima_maior(acorde):
    """Unifica grafias de setima maior: C7M / C7+ / Cmaj7 / CM7 -> C7."""
    acorde = re.sub(r'7M', '7', acorde)
    acorde = re.sub(r'7\+', '7', acorde)
    acorde = re.sub(r'maj7', '7', acorde, flags=re.IGNORECASE)
    return re.sub(r'M7', '7', acorde)


def normaliza_raiz(acorde):
    """Mantem so a raiz: C7M -> C, Am7 -> A, D7M/F# -> D."""
    m = RAIZ.match(acorde)
    return m.group(1) if m else acorde


def normaliza_raiz_terca(acorde):
    """Mantem raiz + terca: C7M -> C, Am7 -> Am, D7M/F# -> D."""
    m = RAIZ.match(acorde)
    if not m:
        return acorde
    raiz, resto = m.group(1), m.group(2).split('/')[0]
    menor = resto[:1].lower() == 'm' and resto[:3].lower() not in ('maj', 'min')
    return raiz + ('m' if menor else '')


NORMALIZACOES = [
    ('nenhuma', None),
    ('7M/7+/maj7 -> 7', normaliza_setima_maior),
    ('so raiz (C7M -> C)', normaliza_raiz),
    ('raiz + terca (C7M -> C, Am7 -> Am)', normaliza_raiz_terca),
]


# ---------------------------------------------------------------------------
# Relatorios
# ---------------------------------------------------------------------------

def ids_por_tag(linhas, indice):
    return {l['id'] for l in linhas if str(indice) in l['tag']}


def ids_por_regra(linhas, seq, funcao, normaliza=None):
    if normaliza:
        seq = [normaliza(a) for a in seq]
    selecionadas = set()
    for l in linhas:
        acordes = [normaliza(a) for a in l['cifra']] if normaliza else l['cifra']
        if funcao(acordes, seq):
            selecionadas.add(l['id'])
    return selecionadas


def relatorio_baseline(linhas):
    print('== 1. Coluna SEQ_FAMOSA ==')
    print('linhas carregadas: %d (1a linha descartada, como main.py:50)' % len(linhas))
    tags = Counter(';'.join(l['tag']) if l['tag'] else '' for l in linhas)
    for valor, total in sorted(tags.items(), key=lambda kv: (-kv[1], kv[0])):
        rotulo = repr(valor) if valor else "'' (vazio)"
        print('  %-12s %6d' % (rotulo, total))
    multi = sum(1 for l in linhas if len(l['tag']) > 1)
    print('  linhas com mais de uma tag: %d' % multi)
    duplicados = len(linhas) - len({l['id'] for l in linhas})
    print('  id_unico_musica duplicados: %d' % duplicados)
    print()


def relatorio_candidatas(linhas):
    print('== 2. Definicoes candidatas (comparadas por conjunto de id_unico_musica) ==')
    cabecalho = '%-38s %-34s %6s %8s %5s' % (
        'definicao', 'contagem por sequencia (0..5)', 'extras', 'faltando', 'igual')
    print(cabecalho)
    print('-' * len(cabecalho))
    base = {i: ids_por_tag(linhas, i) for i in range(len(SEQUENCIAS))}
    print('%-38s %-34s %6s %8s %5s' % (
        'tag pre-computada (baseline)',
        '[%s]' % ','.join(str(len(base[i])) for i in range(6)),
        '-', '-', '-'))
    for rotulo, funcao in CANDIDATAS:
        contagens, extras, faltando = [], 0, 0
        for i, (_, seq) in enumerate(SEQUENCIAS):
            obtidos = ids_por_regra(linhas, seq, funcao)
            contagens.append(len(obtidos))
            extras += len(obtidos - base[i])
            faltando += len(base[i] - obtidos)
        print('%-38s %-34s %6d %8d %5s' % (
            rotulo,
            '[%s]' % ','.join(str(c) for c in contagens),
            extras, faltando,
            'sim' if (extras == 0 and faltando == 0) else 'nao'))
    print()


def relatorio_igualdade(linhas):
    print('== 3. Igualdade da definicao E por id_unico_musica ==')
    for i, (nome, seq) in enumerate(SEQUENCIAS):
        obtidos = ids_por_regra(linhas, seq, e_contigua_vocabulario_fechado)
        esperados = ids_por_tag(linhas, i)
        print('  %d %-8s regra=%3d tag=%3d iguais=%-5s so_regra=%d so_tag=%d' % (
            i, nome, len(obtidos), len(esperados), obtidos == esperados,
            len(obtidos - esperados), len(esperados - obtidos)))
    print()


def relatorio_variantes(linhas, crus):
    print('== 4. Variantes de comparacao e de tokenizacao ==')
    for rotulo, funcao in [('E por substring', e_contigua_vocabulario_fechado),
                           ('E alinhada a tokens', e_alinhada_a_tokens)]:
        ok = all(
            ids_por_regra(linhas, seq, funcao) == ids_por_tag(linhas, i)
            for i, (_, seq) in enumerate(SEQUENCIAS))
        print('  %-22s identica a tag nas 6 sequencias: %s' % (rotulo, ok))
    print()


def relatorio_tokenizacao(linhas, crus):
    print('== 5. Tokenizacao: campo cru vs limpa_cifra ==')
    diferentes = sum(1 for a, b in zip(linhas, crus) if a['cifra'] != b['cifra'])
    print('  linhas em que limpa_cifra muda a tokenizacao: %d' % diferentes)
    for rotulo, funcao in [('substring', e_contigua_vocabulario_fechado),
                           ('alinhada a tokens', e_alinhada_a_tokens)]:
        ok = all(
            ids_por_regra(crus, seq, funcao) == ids_por_tag(crus, i)
            for i, (_, seq) in enumerate(SEQUENCIAS))
        print('  E por %-18s com tokens crus identica a tag: %s' % (rotulo, ok))
    print()


def relatorio_normalizacao(linhas):
    print('== 6. Efeito de normalizar acordes (definicao E) ==')
    base = [len(ids_por_tag(linhas, i)) for i in range(6)]
    print('  %-36s %-34s' % ('normalizacao', 'contagem por sequencia (0..5)'))
    print('  ' + '-' * 71)
    print('  %-36s %-34s' % ('nenhuma (baseline da tag)', '[%s]' % ','.join(map(str, base))))
    for rotulo, funcao in NORMALIZACOES[1:]:
        contagens = []
        for _, seq in SEQUENCIAS:
            contagens.append(len(ids_por_regra(
                linhas, seq, e_contigua_vocabulario_fechado, normaliza=funcao)))
        print('  %-36s %-34s' % (rotulo, '[%s]' % ','.join(map(str, contagens))))
    print()

    tokens = {a for l in linhas for a in l['cifra']}
    afetados = {a for a in tokens if normaliza_setima_maior(a) != a}
    linhas_afetadas = sum(
        1 for l in linhas if any(normaliza_setima_maior(a) != a for a in l['cifra']))
    print('  tokens distintos no dataset: %d' % len(tokens))
    print('  tokens alterados por 7M/7+/maj7 -> 7: %d' % len(afetados))
    print('  linhas afetadas por 7M/7+/maj7 -> 7: %d' % linhas_afetadas)
    print()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', nargs='?', default=CSV_PADRAO,
                        help='caminho do dataset (default: %s)' % CSV_PADRAO)
    args = parser.parse_args()

    try:
        linhas = carregar(args.csv)
        crus = carregar(args.csv, tokenizar=False)
    except IOError as e:
        print('erro ao abrir %s: %s' % (args.csv, e), file=sys.stderr)
        return 1

    print('dataset: %s' % args.csv)
    print()
    relatorio_baseline(linhas)
    relatorio_candidatas(linhas)
    relatorio_igualdade(linhas)
    relatorio_variantes(linhas, crus)
    relatorio_tokenizacao(linhas, crus)
    relatorio_normalizacao(linhas)
    return 0


if __name__ == '__main__':
    sys.exit(main())
