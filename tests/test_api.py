# coding: utf-8
import json
import os
import shutil
import tempfile
import unittest

# `main.py` chama db.init_db() no import; o banco de teste precisa ser
# configurado antes de importar o modulo.
_TEMP_DIR = tempfile.mkdtemp(prefix='deciframe-test-api-')
_DB_PATH = os.path.join(_TEMP_DIR, 'sequences.db')
os.environ['SEQUENCES_DB'] = _DB_PATH

import main  # noqa: E402


def _json(response):
    return json.loads(response.get_data(as_text=True))


class ApiTest(unittest.TestCase):

    def setUp(self):
        if os.path.exists(_DB_PATH):
            os.remove(_DB_PATH)
        main.db.init_db()
        self.client = main.app.test_client()

    def _post(self, payload=None, **kwargs):
        return self.client.post('/sequencias', json=payload, **kwargs)

    def test_catalogo_inicial(self):
        resposta = self.client.get('/sequencias')
        self.assertEqual(200, resposta.status_code)
        self.assertEqual('text/html; charset=utf-8', resposta.content_type)
        self.assertEqual('*', resposta.headers['Access-Control-Allow-Origin'])

        catalogo = _json(resposta)
        self.assertEqual(6, len(catalogo))
        self.assertEqual([1, 2, 3, 4, 5, 6], [s['id'] for s in catalogo])
        self.assertEqual({
            'id': 1,
            'nome': 'Sequência de Bm',
            'acordes': 'Bm;G;D;A',
            'origem': 'legacy',
        }, catalogo[0])
        self.assertEqual('C;G;Am;F', catalogo[1]['acordes'])

    def test_cria_sequencia_e_busca_por_id(self):
        resposta = self._post({'nome': 'Dois acordes', 'acordes': ['C', 'G']})
        self.assertEqual(201, resposta.status_code)
        self.assertEqual('text/html; charset=utf-8', resposta.content_type)
        self.assertEqual('*', resposta.headers['Access-Control-Allow-Origin'])

        criada = _json(resposta)
        self.assertEqual(7, criada['id'])
        self.assertEqual('Dois acordes', criada['nome'])
        self.assertEqual('C;G', criada['acordes'])
        self.assertEqual('user', criada['origem'])

        busca = self.client.get('/similares?sequencia_id=7')
        self.assertEqual(200, busca.status_code)
        self.assertEqual('text/html; charset=utf-8', busca.content_type)
        musicas = _json(busca)
        self.assertEqual(20, len(musicas))
        self.assertIn('id_unico_musica', musicas[0])
        self.assertNotIn('diferenca', musicas[0])

        catalogo = _json(self.client.get('/sequencias'))
        self.assertEqual(7, len(catalogo))
        self.assertEqual(criada, catalogo[-1])

    def test_nome_derivado_quando_ausente(self):
        criada = _json(self._post({'acordes': ['C', 'G']}))
        self.assertEqual(7, criada['id'])
        self.assertEqual('C - G', criada['nome'])

        vazia = _json(self._post({'acordes': ['D', 'A'], 'nome': '   '}))
        self.assertEqual(8, vazia['id'])
        self.assertEqual('D - A', vazia['nome'])

    def test_duplicata_devolve_linha_existente(self):
        resposta = self._post({
            'nome': 'Nome ignorado',
            'acordes': ['C', 'G', 'Am', 'F'],
        })
        self.assertEqual(201, resposta.status_code)
        duplicata = _json(resposta)
        self.assertEqual(2, duplicata['id'])
        self.assertEqual('Sequência de C', duplicata['nome'])
        self.assertEqual('C;G;Am;F', duplicata['acordes'])
        self.assertEqual('legacy', duplicata['origem'])
        self.assertEqual(6, len(_json(self.client.get('/sequencias'))))

        # Caixa e espacos sao normalizados so para deduplicar.
        resposta = self._post({'nome': 'Outro', 'acordes': [' c ', 'g ', 'AM', 'F ']})
        self.assertEqual(201, resposta.status_code)
        self.assertEqual(2, _json(resposta)['id'])

    def test_novo_duplicado_nao_cria_linha(self):
        primeira = _json(self._post({'acordes': ['C', 'G']}))
        segunda = _json(self._post({'nome': 'Outro nome', 'acordes': [' c ', 'G']}))
        self.assertEqual(primeira['id'], segunda['id'])
        self.assertEqual(primeira['nome'], segunda['nome'])
        self.assertEqual(7, len(_json(self.client.get('/sequencias'))))

    def test_entradas_invalidas(self):
        invalidos = [
            ('sem corpo', {}),
            ('objeto vazio', {'json': {}}),
            ('acordes vazio', {'json': {'acordes': []}}),
            ('acordes texto', {'json': {'acordes': 'C;G'}}),
            ('acordes demais', {'json': {'acordes': ['C'] * 33}}),
            ('acorde vazio', {'json': {'acordes': ['']}}),
            ('acorde so espaco', {'json': {'acordes': ['   ']}}),
            ('acorde longo', {'json': {'acordes': ['C' * 21]}}),
            ('acorde com ponto e virgula', {'json': {'acordes': ['C;G']}}),
            ('acorde nao texto', {'json': {'acordes': [123]}}),
            ('nome longo', {'json': {'acordes': ['C'], 'nome': 'x' * 81}}),
            ('nome nao texto', {'json': {'acordes': ['C'], 'nome': 123}}),
            ('corpo nao json', {'data': 'nao e json',
                                'content_type': 'text/plain'}),
        ]
        for rotulo, kwargs in invalidos:
            with self.subTest(caso=rotulo):
                resposta = self.client.post('/sequencias', **kwargs)
                self.assertEqual(400, resposta.status_code)
                self.assertEqual('text/html; charset=utf-8', resposta.content_type)
                self.assertEqual('*', resposta.headers['Access-Control-Allow-Origin'])
                corpo = _json(resposta)
                self.assertIn('erro', corpo)
                self.assertTrue(corpo['erro'])

        self.assertEqual(6, len(_json(self.client.get('/sequencias'))))

    def test_sequencia_id_invalido_ou_desconhecido_devolve_lista_vazia(self):
        for valor in ['abc', '1.5', '', '-1', '999']:
            with self.subTest(sequencia_id=valor):
                resposta = self.client.get('/similares?sequencia_id=' + valor)
                self.assertEqual(200, resposta.status_code)
                self.assertEqual('text/html; charset=utf-8', resposta.content_type)
                self.assertEqual([], _json(resposta))

    def test_paginacao_das_sequencias_originais(self):
        self.assertEqual(99, len(_json(self.client.get(
            '/similares?sequencia_id=1&pagina=2'))))
        self.assertEqual(96, len(_json(self.client.get(
            '/similares?sequencia_id=2&pagina=3'))))
        self.assertEqual(0, len(_json(self.client.get(
            '/similares?sequencia_id=1&pagina=3'))))

    def test_genero_continua_filtrando(self):
        musicas = _json(self.client.get(
            '/similares?sequencia_id=1&generos=Rock&pagina=1'))
        self.assertTrue(musicas)
        self.assertLess(len(musicas), 199)
        self.assertEqual({'Rock'}, {m['genero'] for m in musicas})

    def test_rota_legada_continua_funcionando(self):
        self.assertEqual(100, len(_json(self.client.get(
            '/similares?sequencia=BmGDA&pagina=1'))))
        self.assertEqual([], _json(self.client.get('/similares?sequencia=XXYY')))
        self.assertEqual([], _json(self.client.get(
            '/similares?sequencia=bm,g,d,a')))


def tearDownModule():
    shutil.rmtree(_TEMP_DIR, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
