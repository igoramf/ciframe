#!/usr/bin/env python3
# coding: utf-8
"""Compara `/similares` com o baseline capturado antes da mudanca.

Refaz exatamente as mesmas requisicoes de
`scripts/capturar_baseline_similares.py` e compara pagina a pagina, item a
item, na mesma ordem. Sai com codigo diferente de zero e imprime a primeira
divergencia encontrada.

Requer apenas a biblioteca padrao (Python 3).

Uso:
    python3 scripts/comparar_baseline_similares.py [--base-url URL] [--dir DIR]
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_PADRAO = os.path.join(
    RAIZ, 'docs', 'features', 'sequencias-customizadas', 'baseline')
BASE_URL_PADRAO = 'http://localhost:8080'
LIMITE_PAGINAS = 10


def carregar_baseline(diretorio):
    resumo_path = os.path.join(diretorio, 'resumo.json')
    with open(resumo_path, encoding='utf-8') as f:
        resumo = json.load(f)

    baselines = []
    for entrada in resumo['sequencias']:
        caminho = os.path.join(diretorio, entrada['arquivo'])
        with open(caminho, encoding='utf-8') as f:
            dados = json.load(f)
        baselines.append({
            'sequencia': entrada['sequencia'],
            'paginas': dados['paginas'],
            'total': entrada['total'],
            'paginas_nao_vazias': entrada['paginas'],
        })
    return resumo, baselines


def buscar_pagina(base_url, chave, pagina, timeout=60):
    query = urllib.parse.urlencode({'sequencia': chave, 'pagina': pagina})
    url = '%s/similares?%s' % (base_url.rstrip('/'), query)
    with urllib.request.urlopen(url, timeout=timeout) as resposta:
        corpo = resposta.read().decode('utf-8')
    return json.loads(corpo)


def comparar_itens(esperado, obtido, chave, pagina, indice):
    e = esperado[indice]
    o = obtido[indice]
    if e == o:
        return None
    campos = sorted(set(e) | set(o))
    for campo in campos:
        if e.get(campo) != o.get(campo):
            return (
                'sequencia=%s pagina=%d item=%d campo=%s: esperado=%r obtido=%r'
                % (chave, pagina, indice, campo, e.get(campo), o.get(campo)))
    return ('sequencia=%s pagina=%d item=%d: objeto diferente'
            % (chave, pagina, indice))


def comparar_sequencia(base_url, baseline):
    chave = baseline['sequencia']
    esperadas = baseline['paginas']
    obtidas = []
    for pagina in range(1, LIMITE_PAGINAS + 1):
        itens = buscar_pagina(base_url, chave, pagina)
        obtidas.append(itens)
        if not itens:
            break

    for indice_pagina, esperada in enumerate(esperadas):
        pagina = indice_pagina + 1
        if indice_pagina >= len(obtidas):
            return ('sequencia=%s pagina=%d: baseline tem %d itens, servidor '
                    'nao devolveu a pagina' % (chave, pagina, len(esperada)))
        obtida = obtidas[indice_pagina]
        if len(esperada) != len(obtida):
            return ('sequencia=%s pagina=%d: esperado %d itens, obtido %d'
                    % (chave, pagina, len(esperada), len(obtida)))
        for indice_item, item in enumerate(esperada):
            divergencia = comparar_itens(esperada, obtida, chave, pagina,
                                         indice_item)
            if divergencia:
                return divergencia

    if len(obtidas) > len(esperadas):
        return ('sequencia=%s: baseline termina na pagina %d, servidor devolveu '
                '%d paginas' % (chave, len(esperadas), len(obtidas)))
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', BASE_URL_PADRAO),
                        help='URL do servidor (default: %s)' % BASE_URL_PADRAO)
    parser.add_argument('--dir', default=DIR_PADRAO,
                        help='diretorio do baseline (default: %s)' % DIR_PADRAO)
    parser.add_argument('--tolerar-csv', action='store_true',
                        help='nao falha se o sha256 do CSV for diferente')
    args = parser.parse_args()

    try:
        resumo, baselines = carregar_baseline(args.dir)
    except (IOError, ValueError, KeyError) as e:
        print('erro ao carregar baseline em %s: %s' % (args.dir, e),
              file=sys.stderr)
        return 2

    if not args.tolerar_csv:
        import hashlib
        caminho_csv = os.path.join(RAIZ, resumo['csv']['caminho'])
        h = hashlib.sha256()
        with open(caminho_csv, 'rb') as f:
            for bloco in iter(lambda: f.read(1024 * 1024), b''):
                h.update(bloco)
        atual = h.hexdigest()
        if atual != resumo['csv']['sha256']:
            print('CSV divergiu do baseline: esperado %s, atual %s'
                  % (resumo['csv']['sha256'], atual), file=sys.stderr)
            return 2

    for baseline in baselines:
        divergencia = comparar_sequencia(args.base_url, baseline)
        if divergencia:
            print('DIVERGENCIA: %s' % divergencia, file=sys.stderr)
            return 1
        print('%-8s ok (total=%d, paginas=%d)' % (
            baseline['sequencia'], baseline['total'],
            baseline['paginas_nao_vazias']))

    print('baseline ok: 6 sequencias identicas item a item, na mesma ordem')
    return 0


if __name__ == '__main__':
    sys.exit(main())
