# coding: utf-8
import os
import shutil
import tempfile
import unittest

import db


class DbTest(unittest.TestCase):

    def setUp(self):
        self.diretorio = tempfile.mkdtemp()
        self.db_path = os.path.join(self.diretorio, 'sub', 'sequences.db')
        self.env_anterior = os.environ.get('SEQUENCES_DB')
        os.environ['SEQUENCES_DB'] = self.db_path

    def tearDown(self):
        if self.env_anterior is None:
            os.environ.pop('SEQUENCES_DB', None)
        else:
            os.environ['SEQUENCES_DB'] = self.env_anterior
        shutil.rmtree(self.diretorio, ignore_errors=True)

    def test_init_idempotente_e_seed_na_ordem(self):
        db.init_db()
        db.init_db()

        sequencias = db.listar()
        self.assertEqual(6, len(sequencias))
        self.assertEqual([1, 2, 3, 4, 5, 6],
                         [s['id'] for s in sequencias])
        self.assertEqual([
            'Sequência de Bm',
            'Sequência de C',
            'Sequência Em',
            'Sequência de C (Samba)',
            'Sequência de Gm',
            'Sequência de C (Samba cont.)',
        ], [s['name'] for s in sequencias])
        self.assertEqual(['legacy'] * 6, [s['source'] for s in sequencias])
        self.assertEqual(
            ['Bm;G;D;A', 'C;G;Am;F', 'Em;G', 'C;A7;Dm;G7', 'Gm;F', 'C;C7;F;Fm'],
            [s['chords'] for s in sequencias])
        self.assertEqual(
            ['bm;g;d;a', 'c;g;am;f', 'em;g', 'c;a7;dm;g7', 'gm;f', 'c;c7;f;fm'],
            [s['chords_norm'] for s in sequencias])

    def test_busca_por_legacy_key(self):
        db.init_db()
        sequencia = db.obter_por_legacy_key('CGAmF')
        self.assertIsNotNone(sequencia)
        self.assertEqual(2, sequencia['id'])
        self.assertEqual('Sequência de C', sequencia['name'])
        self.assertEqual('C;G;Am;F', sequencia['chords'])
        self.assertEqual('legacy', sequencia['source'])
        self.assertIsNone(db.obter_por_legacy_key('XXYY'))

    def test_busca_por_id(self):
        db.init_db()
        sequencia = db.obter_por_id(3)
        self.assertEqual('EmG', sequencia['legacy_key'])
        self.assertEqual('Em;G', sequencia['chords'])
        self.assertIsNone(db.obter_por_id(99))

    def test_cria_e_deduplica_por_chords_norm(self):
        db.init_db()

        nova = db.criar_sequencia(['C', 'G'], 'Dois acordes')
        self.assertEqual(7, nova['id'])
        self.assertEqual('Dois acordes', nova['name'])
        self.assertEqual('C;G', nova['chords'])
        self.assertEqual('c;g', nova['chords_norm'])
        self.assertEqual('user', nova['source'])
        self.assertIsNone(nova['legacy_key'])

        duplicata = db.criar_sequencia([' c ', 'G'], 'Outro nome')
        self.assertEqual(nova['id'], duplicata['id'])
        self.assertEqual('Dois acordes', duplicata['name'])
        self.assertEqual(7, len(db.listar()))

    def test_duplicata_de_sequencia_legada_devolve_a_existente(self):
        db.init_db()
        existente = db.criar_sequencia(['C', 'G', 'Am', 'F'], 'Nome ignorado')
        self.assertEqual(2, existente['id'])
        self.assertEqual('Sequência de C', existente['name'])
        self.assertEqual('legacy', existente['source'])
        self.assertEqual(6, len(db.listar()))

    def test_banco_de_teste_fica_no_diretorio_temporario(self):
        db.init_db()
        self.assertTrue(os.path.exists(self.db_path))
        self.assertEqual(self.db_path, os.path.abspath(db.caminho_db()))


if __name__ == '__main__':
    unittest.main()
