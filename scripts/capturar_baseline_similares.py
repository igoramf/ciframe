#!/usr/bin/env python3
# coding: utf-8
"""Captura o comportamento atual de `/similares` para as 6 sequencias legadas.

Este script NAO faz parte da aplicacao: ele congela, em arquivos JSON, as
paginas devolvidas por `GET /similares?sequencia=<chave>&pagina=N` antes de
qualquer mudanca no backend. Os artefatos servem de baseline para
`scripts/comparar_baseline_similares.py`.

Requer apenas a biblioteca padrao (Python 3). Nao importa Flask nem `main.py`.

Uso:
    python3 scripts/capturar_baseline_similares.py [--base-url URL] [--dir DIR]

Nota: a ordem dos resultados de `/similares` depende da ordem de `generos`,
que vem de `list(set(...))` em `main.py` e varia com `PYTHONHASHSEED`. Para o
baseline ser reproduzivel entre processos, o servidor deve rodar com
`PYTHONHASHSEED=0` (ex.: `docker run -e PYTHONHASHSEED=0 ...`).
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHAVES = ['BmGDA', 'CGAmF', 'EmG', 'CA7DmG7', 'GmF', 'CC7FFm']

# Totais e quantidade de paginas nao vazias esperados pela pesquisa
# (`docs/features/sequencias-customizadas/01-research.md` §2.5). Se a captura
# divergir, o script falha: o baseline nao deve ser "ajustado para passar".
TOTAIS_ESPERADOS = [199, 296, 4, 5, 7, 3]
PAGINAS_ESPERADAS = [2, 3, 1, 1, 1, 1]

BASE_URL_PADRAO = 'http://localhost:8080'
DIR_PADRAO = os.path.join(
    RAIZ, 'docs', 'features', 'sequencias-customizadas', 'baseline')
CSV_PADRAO = os.path.join(RAIZ, 'data', 'top', 'dataset_final.csv')

LIMITE_PAGINAS = 10


def sha256_arquivo(caminho):
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b''):
            h.update(bloco)
    return h.hexdigest()


def buscar_pagina(base_url, chave, pagina, timeout=60):
    """Devolve a lista crua de uma pagina de `/similares`."""
    query = urllib.parse.urlencode({'sequencia': chave, 'pagina': pagina})
    url = '%s/similares?%s' % (base_url.rstrip('/'), query)
    with urllib.request.urlopen(url, timeout=timeout) as resposta:
        corpo = resposta.read().decode('utf-8')
    dados = json.loads(corpo)
    if not isinstance(dados, list):
        raise ValueError('%s devolveu %r, esperava uma lista' % (url, type(dados)))
    return dados


def capturar_sequencia(base_url, chave):
    """Pagina de 1 ate a primeira pagina vazia (limite de seguranca)."""
    paginas = []
    for pagina in range(1, LIMITE_PAGINAS + 1):
        itens = buscar_pagina(base_url, chave, pagina)
        paginas.append(itens)
        if not itens:
            break
    else:
        raise RuntimeError(
            'sequencia %s nao devolveu pagina vazia em %d paginas'
            % (chave, LIMITE_PAGINAS))
    return paginas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default=os.environ.get('BASE_URL', BASE_URL_PADRAO),
                        help='URL do servidor (default: %s)' % BASE_URL_PADRAO)
    parser.add_argument('--dir', default=DIR_PADRAO,
                        help='diretorio de saida (default: %s)' % DIR_PADRAO)
    parser.add_argument('--csv', default=CSV_PADRAO,
                        help='dataset para registrar o sha256 (default: %s)' % CSV_PADRAO)
    parser.add_argument('--sem-validar-totais', action='store_true',
                        help='nao falha se os totais divergirem da pesquisa')
    args = parser.parse_args()

    os.makedirs(args.dir, exist_ok=True)

    resumo = {
        'base_url': args.base_url,
        'pythonhashseed': os.environ.get('PYTHONHASHSEED', ''),
        'observacao': (
            'a ordem dos resultados depende do PYTHONHASHSEED do servidor; '
            'capture e compare com o servidor em PYTHONHASHSEED=0'),
        'sequencias': [],
        'csv': {
            'caminho': os.path.relpath(args.csv, RAIZ),
            'sha256': sha256_arquivo(args.csv),
        },
    }

    divergencias = []
    for indice, chave in enumerate(CHAVES):
        paginas = capturar_sequencia(args.base_url, chave)
        arquivo = os.path.join(args.dir, 'similares_%s.json' % chave)
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump({'sequencia': chave, 'paginas': paginas}, f,
                      ensure_ascii=False, indent=2)
            f.write('\n')

        nao_vazias = sum(1 for p in paginas if p)
        total = sum(len(p) for p in paginas)
        resumo['sequencias'].append({
            'sequencia': chave,
            'arquivo': os.path.basename(arquivo),
            'total': total,
            'paginas': nao_vazias,
            'requisicoes': len(paginas),
            'sha256': sha256_arquivo(arquivo),
        })

        esperado_total = TOTAIS_ESPERADOS[indice]
        esperado_paginas = PAGINAS_ESPERADAS[indice]
        if total != esperado_total or nao_vazias != esperado_paginas:
            divergencias.append(
                '%s: total=%d (esperado %d), paginas=%d (esperado %d)'
                % (chave, total, esperado_total, nao_vazias, esperado_paginas))
        print('%-8s total=%3d paginas=%d requisicoes=%d' % (
            chave, total, nao_vazias, len(paginas)))

    resumo_path = os.path.join(args.dir, 'resumo.json')
    with open(resumo_path, 'w', encoding='utf-8') as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')

    print('resumo: %s' % resumo_path)
    print('csv sha256: %s' % resumo['csv']['sha256'])

    if divergencias and not args.sem_validar_totais:
        print('\nERRO: baseline divergiu da pesquisa:', file=sys.stderr)
        for d in divergencias:
            print('  ' + d, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
