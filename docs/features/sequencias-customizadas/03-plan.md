# Plano — Sequências de Acordes Customizadas

## Passos

1. [x] **Capturar o baseline de `/similares` antes de tocar no código.**
   - Criar `scripts/capturar_baseline_similares.py` (só biblioteca padrão): para
     cada chave legada (`BmGDA`, `CGAmF`, `EmG`, `CA7DmG7`, `GmF`, `CC7FFm`),
     pedir `GET /similares?sequencia=<chave>&pagina=N` a partir de `N=1` até
     vir uma página vazia (limite de segurança de 10 páginas).
   - Salvar em `docs/features/sequencias-customizadas/baseline/`:
     `similares_<chave>.json` com as páginas cruas (mantendo a ordem) e um
     `resumo.json` com total por sequência, quantidade de páginas, `sha256` de
     cada arquivo e `sha256` de `data/top/dataset_final.csv`.
   - Criar `scripts/comparar_baseline_similares.py`: refaz as mesmas requisições
     e compara página a página, item a item, na mesma ordem; sai com código
     diferente de zero e imprime a primeira divergência.
   - Rodar a captura e a comparação de controle contra o código atual, antes de
     qualquer edição. Aceitar como baseline somente se os totais forem
     `199, 296, 4, 5, 7, 3` e as páginas forem `2, 3, 1, 1, 1, 1`.
   - Se os números divergirem da pesquisa, parar e conferir porta, imagem,
     dataset e hash do CSV — não ajustar o baseline para “fazer passar”.
   - **Nota de reprodução:** a ordem de `generos` vem de `list(set(...))`
     (`main.py:92`) e varia com `PYTHONHASHSEED`. Captura e comparação usam o
     servidor com `PYTHONHASHSEED=0`. O baseline foi capturado primeiro com o
     código original; depois o comparador acusou apenas diferença de ordem, e
     o baseline foi refeito a partir do commit `5c70e4a` (código anterior a
     qualquer mudança) no mesmo seed. Conjunto de IDs e totais não mudaram.
   - **Verificação:** `comparar_baseline_similares.py` retorna sucesso contra o
     próprio baseline recém-capturado. Commitar os artefatos antes do passo 2.

2. [x] **Criar o matcher puro em `matching.py`.**
   - Implementar `corresponde(cifra_musica, acordes_sequencia)` com a regra E:
     normalizar os dois lados para minúsculas, exigir bloco contíguo alinhado a
     tokens e exigir que todo token da música pertença ao vocabulário da
     sequência. Sequência vazia ou maior que a música retorna `False`.
   - Não adicionar enarmonia, sufixos, baixo invertido, remoção de repetições ou
     qualquer normalização além de `lower()`.
   - Criar `tests/test_matching.py` (stdlib `unittest`) cobrindo: bloco exato,
     repetições em volta do bloco, ordem invertida que não casa, acorde extra que
     desqualifica, diferença de caixa, sequência vazia/maior, limite de token
     (`['Bm','G']` não casa com `['m','g']`), `C#` ≠ `Db` e `Am` ≠ `Am7`.
   - **Verificação:** `python3 -m unittest tests.test_matching -v` passa. Nada em
     `main.py` importa o módulo ainda.

3. [x] **Criar o banco SQLite e o catálogo em `db.py`.**
   - Implementar caminho configurável por `SEQUENCES_DB`, com default
     `instance/sequences.db`; criar o diretório se não existir; abrir conexão por
     operação com `busy_timeout`.
   - Criar a tabela do catálogo com `id`, `name`, `chords`, `chords_norm`
     (`UNIQUE`), `source` (`legacy`/`user`), `legacy_key` (`UNIQUE`, `NULL` para
     novas), `created_at`.
   - `init_db()` deve ser idempotente e semear as 6 sequências na ordem de
     `main.py:40-45`, com os nomes de
     `data/mapeamento_sequencias_famosas.txt` e `chords_norm` em minúsculas.
   - Expor leitura por `id` e por `legacy_key`, listagem ordenada por `id` e
     criação que devolve a linha existente quando `chords_norm` já existe.
   - Criar `tests/test_db.py` usando diretório temporário: duas chamadas a
     `init_db()`, contagem 6, ordem/nomes, busca por `legacy_key`, criação nova e
     duplicata sem linha extra.
   - **Verificação:** `python3 -m unittest tests.test_db -v` passa; o banco de
     teste é temporário e não cria `instance/` no repositório.

4. [x] **Trocar a tag pelo matcher no caminho por sequência, mantendo a URL antiga.**
   - Em `musica.py`, remover o parâmetro e o atributo `seqs_famosas`.
   - Em `main.py`, parar de dividir a coluna 7 e de passá-la ao construtor;
     remover a constante `SEQ_FAMOSA` se ficar sem uso. A coluna do CSV e
     `scripts/generate_data_set.py` não mudam.
   - Chamar `init_db()` no carregamento do módulo e substituir o dicionário
     `sequencias` por consulta ao catálogo por `legacy_key`.
   - Fazer `get_similares_por_sequencia` receber a lista de acordes da sequência
     e filtrar `musicas.values()` com `matching.corresponde(musica.cifra, ...)`,
     sem `sorted` novo e mantendo `get_pagina`/100.
   - Preservar `sequencia=<legacy_key>` e o comportamento atual de remover
     vírgulas, para que `Bm,G,D,A` continue virando `BmGDA`; chave desconhecida
     continua devolvendo `[]` com HTTP 200.
   - **Verificação:** rodar `scripts/comparar_baseline_similares.py` contra as 6
     chaves antigas com o servidor novo em `PYTHONHASHSEED=0`; zero diferenças
     de itens e de ordem. Testar também
     `/similares?sequencia=XXYY` → `[]` e `Content-Type: text/html`.

5. [x] **Adicionar `GET /sequencias`, `POST /sequencias` e `sequencia_id`.**
   - `GET /sequencias`: listar o catálogo por `id` no formato
     `{"id", "nome", "acordes", "origem"}`, com `acordes` separados por `;`.
   - `POST /sequencias`: exigir JSON com `acordes` não vazio, no máximo 32 itens
     de 1 a 20 caracteres após `strip`, sem `;`; nome opcional com até 80
     caracteres e derivado de `A - B - C` quando ausente. Canonicalizar somente
     com `strip` + `lower`.
   - Duplicata por `chords_norm` devolve a linha existente com HTTP 201, sem
     criar outra e sem usar o nome enviado. Entrada inválida devolve HTTP 400
     com `{"erro": "..."}`. Tudo continua saindo por `json.dumps`, não
     `jsonify`.
   - Em `GET /similares`, aceitar `sequencia_id=<int>`: id inválido ou
     inexistente devolve `[]` com HTTP 200; id válido usa o mesmo caminho de
     busca por sequência. Manter `pagina` e `generos`.
   - Criar `tests/test_api.py` com `Flask.test_client()` e `SEQUENCES_DB`
     temporário: catálogo inicial com 6; criação de `C;G` → 201 e
     `/similares?sequencia_id=<novo>` → 20 itens; duplicata `C;G;Am;F` → 201 com
     `id=2`; casos 400; id desconhecido/não numérico → `[]` 200; paginação
     `id=1&pagina=2` → 99 e `id=2&pagina=3` → 96.
   - **Verificação:** `python3 -m unittest tests.test_api -v` passa e a resposta
     mantém `Content-Type` textual e CORS `*`.

6. [x] **Ligar o frontend ao catálogo real e buscar por `sequencia_id`.**
   - Remover os 4 presets hardcoded de `sequencia.js` e carregar
     `GET /sequencias` no `init` do controller, exibindo as 6 originais e as
     novas com nome.
   - Trocar `similares?sequencia=<acordes concatenados>` por
     `similares?sequencia_id=<id>`, mantendo o filtro de gênero.
   - Extrair a paleta de acordes de `acordes.js` para uma constante/serviço
     compartilhado em `app.js` (sem mudar o visual da página por acordes) e
     reutilizá-la no construtor de sequência, com cor padrão `#2E1C74`.
   - **Verificação no browser:** `#/porsequencia` mostra 6 sequências; clicar na
     sequência 1 busca por `id=1`; clicar na sequência 2 busca por `id=2`;
     filtro de gênero continua funcionando.

7. [ ] **Adicionar construtor, paginação, gêneros do backend e estado vazio.**
   - No construtor, clicar em um acorde da paleta adiciona ao fim da lista;
     clicar em um acorde já adicionado o remove; “Salvar” faz `POST /sequencias`,
     e com o `id` devolvido dispara a busca. Nome é opcional.
   - Enviar `pagina` em `sequencia.js` e oferecer “carregar mais”, acumulando
     resultados sem duplicar; a primeira página continua com 100.
   - Alimentar o `<select>` de gêneros com `GET /generos` (52 itens, incluindo
     `R&B;`) em vez da constante `GENEROS`.
   - Remover `ng-hide="music.diferenca.length"` de `sequencia.html`, pois
     `diferenca` não existe no caminho por sequência.
   - Mostrar um estado vazio explicando bloco contíguo + vocabulário fechado
     quando a sequência não retorna músicas.
   - **Verificação no browser:** sequência 1 mostra 199 após “carregar mais”;
     sequência 2 mostra 296 em três páginas; cadastrar `C;G` como “Dois acordes”
     retorna 20; recarregar a página mantém a sequência no catálogo; uma
     sequência impossível mostra o texto de estado vazio.

8. [ ] **Persistir o banco no Docker e documentar o volume.**
   - Adicionar `VOLUME /app/instance` ao `Dockerfile` e ignorar `instance/` (e
     arquivos `*.db`) em `.gitignore`.
   - Atualizar `README.md` e `AGENTS.md` para
     `docker run -p 8080:8080 -v ciframe-data:/app/instance ciframe`, explicando
     que sem o volume o catálogo se perde ao recriar o container.
   - **Verificação:** buildar a imagem, rodar com o volume nomeado, cadastrar
     uma sequência, fazer `docker restart` e confirmar que ela continua; depois
     `docker rm` + novo `docker run` com o mesmo volume e confirmar de novo.

9. [ ] **Fechar a regressão e documentar os testes.**
   - Acrescentar ao `scripts/validar_matching.py` uma seção que compara o
     `matching.corresponde` de runtime com a tag `SEQ_FAMOSA` para as 6
     sequências, por conjunto de `id_unico_musica`, sem importar Flask.
   - Rodar a suíte completa, o comparador de baseline e o validador; exigir
     `[199, 296, 4, 5, 7, 3]`, zero extras, zero faltantes e zero diferenças de
     ordem contra o baseline.
   - Confirmar por `grep` que `seqs_famosas` não é mais usado em runtime e que
     `data/top/dataset_final.csv` não foi alterado.
   - Preencher `04-test-report.md` com cobertura, comandos, resultado do teste
     de regressão e o que ficou de fora.
   - **Verificação:** todos os comandos passam em uma execução limpa, e o
     vídeo/gif mostra cadastro, busca, paginação e persistência após reinício.

## Arquivos afetados

| Arquivo | Mudança |
|---|---|
| `scripts/capturar_baseline_similares.py` (novo) | Captura paginada das 6 sequências antes da mudança |
| `scripts/comparar_baseline_similares.py` (novo) | Comparação exata, página a página, contra o baseline |
| `docs/features/sequencias-customizadas/baseline/*.json` (novo) | Artefatos congelados do comportamento atual |
| `matching.py` (novo) | Regra E: bloco contíguo alinhado a tokens + vocabulário fechado |
| `db.py` (novo) | SQLite, esquema, seed idempotente e CRUD do catálogo |
| `musica.py` | Remove `seqs_famosas` do construtor e do objeto |
| `main.py` | Remove tag do runtime; usa catálogo/matcher; novos endpoints e `sequencia_id` |
| `tests/test_matching.py` (novo) | Casos unitários do matcher |
| `tests/test_db.py` (novo) | Seed, idempotência e deduplicação do banco |
| `tests/test_api.py` (novo) | Contrato de `/sequencias`, `/similares` e validações |
| `scripts/validar_matching.py` | Seção de regressão contra o matcher de runtime |
| `static/assets/js/controllers/sequencia.js` | Catálogo, busca por id, construtor e paginação |
| `static/templates/sequencia.html` | Catálogo, construtor, “carregar mais”, estado vazio, remove `ng-hide` |
| `static/assets/js/app.js` | Paleta de acordes compartilhada |
| `static/assets/js/controllers/acordes.js` | Passa a consumir a paleta compartilhada |
| `Dockerfile` | `VOLUME /app/instance` |
| `.gitignore` | Ignora `instance/` e `*.db` |
| `README.md` | Comando com `-v ciframe-data:/app/instance` e nota de persistência |
| `AGENTS.md` | Mesmo comando/nota no “Run locally” |

Sem mudança: `requirements.txt` (SQLite é da biblioteca padrão),
`data/top/dataset_final.csv`, `scripts/generate_data_set.py` e o schema do CSV.

## Riscos e mitigação

| Risco | Como perceber | O que fazer |
|---|---|---|
| Baseline capturado com dataset, porta ou imagem diferente | Totais diferentes de `199, 296, 4, 5, 7, 3` ou hash do CSV diferente | Parar antes de codar; conferir `docker build`, `GET /generos`, caminho do CSV e hash; recapturar |
| Ordem dos resultados mudar no refactor | Comparador acusa divergência apenas de ordem | Não ordenar para “consertar”; revisar iteração de `musicas.values()`, `apply_filtro` e `get_pagina`. Confirmar que os dois lados rodam com o mesmo `PYTHONHASHSEED` (`0`), pois a ordem de `generos` vem de `list(set(...))` |
| Remoção da tag quebrar o caminho legado | Comparador falha logo após o passo 4 | Fazer seed + lookup por `legacy_key` + matcher no mesmo passo; manter o `replace(',', '')` |
| SQLite bloqueado ou perdido | `database is locked` ou catálogo vazio após recriar o container | `busy_timeout`, conexão por operação, 1 worker e teste real com volume nomeado |
| Validação divergir do contrato (duplicata, limites) | Testes de API falham no 201/400 | Seguir a proposta: normalizar só `strip`+`lower`, duplicata devolve a linha existente |
| Frontend antigo em cache ou erro silencioso no AngularJS | Browser não lista o catálogo ou mostra 4 sequências | Hard reload, console do browser e conferir inclusão de scripts em `index.html` |
| Cadastro anônimo virar depósito de spam | Catálogo com entradas inúteis | Risco aceito nesta iteração; não implementar login/rate limit/moderação sem nova decisão |
| Escopo crescer para músicas/gêneros no banco ou normalização de acordes | Diff toca `data/`, `generate_data_set.py` ou regras além de `lower()` | Reverter; essas mudanças estão explicitamente fora do escopo |

## Definição de pronto

- [ ] Baseline das 6 sequências capturado antes da mudança e comparador de
      controle passando contra o código antigo.
- [ ] `GET /similares?sequencia=<legacy_key>` devolve exatamente os mesmos
      `id_unico_musica`, na mesma ordem, que o baseline: `199, 296, 4, 5, 7, 3`.
- [ ] `GET /similares?sequencia_id=<id>` funciona para as 6 originais e para
      sequências novas, com paginação de 100 e filtro de gênero.
- [ ] `GET /sequencias` lista as 6 originais primeiro e todas as novas.
- [ ] `POST /sequencias` cria (`201`), deduplica (`201` com a linha existente) e
      rejeita entrada inválida (`400`); uma sequência nova cadastrada é
      encontrável pela busca.
- [ ] Sequência nova persiste após `docker restart` e após `docker rm` + novo
      `docker run` com o mesmo volume nomeado.
- [ ] `#/porsequencia` mostra as 6 + novas, cadastra sequência ordenada, busca
      por `id`, pagina com “carregar mais”, usa os 52 gêneros do backend e
      explica o estado vazio.
- [ ] `seqs_famosas` não é mais usado em runtime; a coluna `SEQ_FAMOSA` e o CSV
      continuam intactos apenas como oráculo de teste.
- [ ] `scripts/validar_matching.py` continua mostrando a regra E idêntica à tag
      nas 6 sequências, e a suíte `unittest` passa.
- [ ] Endpoints continuam devolvendo `json.dumps` como `text/html` e mantendo
      CORS `*`; nenhum endpoint fora do escopo mudou.
- [ ] `04-test-report.md` preenchido com cobertura, comandos e resultado da
      regressão.
