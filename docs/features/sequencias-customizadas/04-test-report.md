# Relatório de testes — Sequências de Acordes Customizadas

## Cobertura

| Arquivo | Testes | O que verifica |
| --- | --- | --- |
| `tests/test_matching.py` | 10 | Regra E: bloco contíguo alinhado a tokens, repetições ao redor, ordem invertida, acorde extra, case-insensitive, sequência vazia/maior, `['Bm','G']` não casa com `['m','g']`, `C#` != `Db`, `Am` != `Am7`. |
| `tests/test_db.py` | 6 | `init_db()` idempotente, seed das 6 sequências na ordem original com nomes do mapeamento, busca por `legacy_key`, criação nova e duplicata por `chords_norm` sem linha extra (banco em diretório temporário). |
| `tests/test_api.py` | 10 | Catálogo com 6 no início; `POST /sequencias` cria `C;G` com 201 e busca por `sequencia_id` retorna 20; duplicata `C;G;Am;F` devolve 201 com `id=2`; validações 400; `id` desconhecido/não numérico retorna `[]` com 200; paginação `id=1&pagina=2` -> 99 e `id=2&pagina=3` -> 96. Mantém `json.dumps`/`text/html` e CORS `*`. |
| `scripts/validar_matching.py` | (verificação de regressão) | Seção 7 compara `matching.corresponde` com a tag `SEQ_FAMOSA` nas 6 sequências: `[199,296,4,5,7,3]` sem extras/faltantes. |
| `scripts/comparar_baseline_similares.py` | (verificação de regressão) | Compara `/similares?sequencia=<legacy_key>` página a página, item a item, contra o baseline congelado em `docs/features/sequencias-customizadas/baseline/` (requer servidor com `PYTHONHASHSEED=0`). |

## Teste de regressão obrigatório

- **Baseline:** artefatos congelados em `docs/features/sequencias-customizadas/baseline/` (capturados a partir do commit `5c70e4a` com `PYTHONHASHSEED=0`). Totais/páginas: `199,296,4,5,7,3` / `2,3,1,1,1,1`. SHA256 do CSV registrado.
- **Comparador:** `python3 scripts/comparar_baseline_similares.py` → todas as 6 sequências ok, `baseline ok: 6 sequencias identicas item a item, na mesma ordem` (exit 0).
- **Validador:** `python3 scripts/validar_matching.py` → seção 7 mostra runtime == tag para todas as 6, contagens `[199,296,4,5,7,3]`, resultado `ok` (exit 0).
- **Grep:** `seqs_famosas` não aparece em código runtime (`main.py`, `musica.py`, `db.py`, `matching.py`, `static/`). A coluna `SEQ_FAMOSA` e `data/top/dataset_final.csv` permanecem intactos (sem diff contra `5c70e4a`).
- **Evidência visual:** `docs/features/sequencias-customizadas/sessoes/evidencia-sequencias.webm` mostra o catálogo, busca por sequência, paginação até 199, cadastro de `C;G` como “Video regressao”, reload e a sequência persistida após `docker restart`.

## Como rodar

```bash
# Suíte completa (unittest)
docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$PWD":/app -w /app ciframe python3 -m unittest discover -v

# Regressão contra baseline legado (servidor com PYTHONHASHSEED=0)
python3 scripts/comparar_baseline_similares.py

# Regressão matcher runtime x tag
python3 scripts/validar_matching.py
```

## O que ficou de fora

- **Autenticação/moderação/rate limit** no cadastro anônimo de sequências (aceito nesta iteração, mencionado nos riscos do plano).
- **Reordenação complexa** no construtor: a proposta usa "clicar para adicionar/remover no fim" e não um editor de drag-and-drop (suficiente para cobrir os testes de validação).
- **Normalização de acordes** (enarmonia, unificação de sufixos, inversões) — explicitamente fora do escopo; o matcher continua restrito a `lower()` apenas.
- **Testes E2E automatizados no browser** nesta suíte `unittest`; a verificação visual foi feita manualmente via `agent-browser` (catálogo, busca por `sequencia_id`, paginação “carregar mais”, gêneros do backend, estado vazio, cadastro + persistência com volume).

## Demonstração

`docs/features/sequencias-customizadas/demo.mp4`: sequência original Bm-G-D-A ainda retornando músicas, cadastro de G-D-Em-C ("Acordes do POP") pelo construtor e busca pela sequência nova.
