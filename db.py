# coding: utf-8
"""Catalogo de sequencias de acordes em SQLite.

Apenas o catalogo vive no banco. Musicas, generos e acordes continuam vindo de
`data/top/dataset_final.csv` em memoria.

O caminho do banco pode ser sobrescrito por `SEQUENCES_DB` (usado pelos
testes); o default e `instance/sequences.db` relativo ao diretorio do projeto.
Uma conexao e aberta por operacao, com `busy_timeout`, para nao depender de
estado global entre requisicoes.
"""

import os
import sqlite3
from contextlib import contextmanager

DB_PADRAO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'instance', 'sequences.db')

# Mesmas 6 sequencias e ordem de main.py:40-45, com os nomes de
# data/mapeamento_sequencias_famosas.txt.
SEQUENCIAS_LEGADAS = [
    {'legacy_key': 'BmGDA', 'chords': ['Bm', 'G', 'D', 'A'],
     'name': 'Sequência de Bm'},
    {'legacy_key': 'CGAmF', 'chords': ['C', 'G', 'Am', 'F'],
     'name': 'Sequência de C'},
    {'legacy_key': 'EmG', 'chords': ['Em', 'G'],
     'name': 'Sequência Em'},
    {'legacy_key': 'CA7DmG7', 'chords': ['C', 'A7', 'Dm', 'G7'],
     'name': 'Sequência de C (Samba)'},
    {'legacy_key': 'GmF', 'chords': ['Gm', 'F'],
     'name': 'Sequência de Gm'},
    {'legacy_key': 'CC7FFm', 'chords': ['C', 'C7', 'F', 'Fm'],
     'name': 'Sequência de C (Samba cont.)'},
]

ESQUEMA = """
CREATE TABLE IF NOT EXISTS sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    chords TEXT NOT NULL,
    chords_norm TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL CHECK (source IN ('legacy', 'user')),
    legacy_key TEXT UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def caminho_db():
    """Caminho efetivo do banco (respeita `SEQUENCES_DB`)."""
    return os.environ.get('SEQUENCES_DB') or DB_PADRAO


@contextmanager
def conectar():
    """Abre uma conexao por operacao, criando o diretorio se necessario."""
    caminho = caminho_db()
    diretorio = os.path.dirname(os.path.abspath(caminho))
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)

    conexao = sqlite3.connect(caminho, timeout=5.0)
    conexao.row_factory = sqlite3.Row
    try:
        conexao.execute('PRAGMA busy_timeout = 5000')
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _como_dict(linha):
    return dict(linha) if linha is not None else None


def _texto_acordes(acordes):
    return ';'.join(acordes)


def _norm_acordes(acordes):
    return ';'.join(acorde.lower() for acorde in acordes)


def init_db():
    """Cria a tabela se preciso e semeia as 6 sequencias de forma idempotente."""
    with conectar() as conexao:
        conexao.execute(ESQUEMA)
        for sequencia in SEQUENCIAS_LEGADAS:
            acordes = sequencia['chords']
            conexao.execute(
                """
                INSERT OR IGNORE INTO sequences
                    (name, chords, chords_norm, source, legacy_key)
                VALUES (?, ?, ?, 'legacy', ?)
                """,
                (sequencia['name'], _texto_acordes(acordes),
                 _norm_acordes(acordes), sequencia['legacy_key']))


def obter_por_id(id_sequencia):
    with conectar() as conexao:
        linha = conexao.execute(
            'SELECT * FROM sequences WHERE id = ?', (id_sequencia,)).fetchone()
    return _como_dict(linha)


def obter_por_legacy_key(legacy_key):
    with conectar() as conexao:
        linha = conexao.execute(
            'SELECT * FROM sequences WHERE legacy_key = ?',
            (legacy_key,)).fetchone()
    return _como_dict(linha)


def listar():
    """Catalogo completo, ordenado por id."""
    with conectar() as conexao:
        linhas = conexao.execute(
            'SELECT * FROM sequences ORDER BY id').fetchall()
    return [dict(linha) for linha in linhas]


def criar_sequencia(acordes, nome=None, source='user', legacy_key=None):
    """Cria uma sequencia ou devolve a existente com mesmo `chords_norm`.

    A canonicalizacao e somente `strip` + `lower`; a grafia exibida preserva a
    caixa enviada (apenas sem espacos nas pontas).
    """
    limpos = [acorde.strip() for acorde in acordes]
    texto = _texto_acordes(limpos)
    normalizado = _norm_acordes(limpos)
    nome = nome or ' - '.join(limpos)

    with conectar() as conexao:
        existente = conexao.execute(
            'SELECT * FROM sequences WHERE chords_norm = ?',
            (normalizado,)).fetchone()
        if existente is not None:
            return dict(existente)

        cursor = conexao.execute(
            """
            INSERT INTO sequences
                (name, chords, chords_norm, source, legacy_key)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nome, texto, normalizado, source, legacy_key))
        linha = conexao.execute(
            'SELECT * FROM sequences WHERE id = ?',
            (cursor.lastrowid,)).fetchone()
        return dict(linha)
