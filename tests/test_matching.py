# coding: utf-8
import unittest

from matching import corresponde


class CorrespondeTest(unittest.TestCase):

    def test_bloco_exato(self):
        self.assertTrue(corresponde(['Bm', 'G', 'D', 'A'],
                                    ['Bm', 'G', 'D', 'A']))

    def test_repeticao_em_volta_do_bloco(self):
        self.assertTrue(corresponde(
            ['Bm', 'G', 'D', 'A', 'Bm', 'G', 'D', 'A'],
            ['Bm', 'G', 'D', 'A']))
        self.assertTrue(corresponde(
            ['G', 'Bm', 'G', 'D', 'A', 'D'],
            ['Bm', 'G', 'D', 'A']))

    def test_ordem_invertida_nao_casa(self):
        self.assertFalse(corresponde(['A', 'D', 'G', 'Bm'],
                                     ['Bm', 'G', 'D', 'A']))

    def test_acorde_extra_desqualifica(self):
        self.assertFalse(corresponde(['Bm', 'G', 'D', 'A', 'E'],
                                     ['Bm', 'G', 'D', 'A']))

    def test_diferenca_de_caixa(self):
        self.assertTrue(corresponde(['bm', 'g', 'd', 'a'],
                                    ['Bm', 'G', 'D', 'A']))
        self.assertTrue(corresponde(['Bm', 'G', 'D', 'A'],
                                    ['bm', 'g', 'd', 'a']))

    def test_sequencia_vazia(self):
        self.assertFalse(corresponde(['C', 'G'], []))

    def test_sequencia_maior_que_a_musica(self):
        self.assertFalse(corresponde(['C', 'G'], ['C', 'G', 'Am']))

    def test_limite_de_token(self):
        self.assertFalse(corresponde(['Bm', 'G'], ['m', 'g']))

    def test_enarmonia_nao_e_normalizada(self):
        self.assertFalse(corresponde(['C#', 'G'], ['Db', 'G']))

    def test_sufixo_nao_e_normalizado(self):
        self.assertFalse(corresponde(['Am', 'F'], ['Am7', 'F']))


if __name__ == '__main__':
    unittest.main()
