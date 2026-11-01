# Proposta — Sequências de Acordes Customizadas

## Abordagem escolhida

A feature segue a **Proposta 1** da fase de ideação: um **único matcher em
runtime**, com a mesma semântica da tag `SEQ_FAMOSA`, e o **catálogo de
sequências em SQLite**. As 6 sequências originais são semeadas no banco como
qualquer outra; nenhuma tem caminho de código privilegiado. O catálogo de
músicas e gêneros continua vindo de `data/top/dataset_final.csv` em memória,
como hoje.

O objetivo é preservar exatamente o comportamento atual das 6 sequências
(research §2.2 e §2.3) ao mesmo tempo em que qualquer visitante pode cadastrar
uma nova lista ordenada de acordes. A decisão de matching é deliberadamente a
mesma da tag, inclusive na sua restritividade (research §5.1).

### Algoritmo de matching

Uma música `M = musica.cifra` (lista ordenada de tokens, com repetições —
`musica.py:16`) casa com uma sequência cadastrada `S = [s1..sk]` se, e somente
se, as duas condições abaixo valerem:

1. **Bloco contíguo alinhado a tokens:** `S` aparece como uma subsequência
   contígua de `M` (comparação token a token, não substring de texto).
2. **Vocabulário fechado:** todo token de `M` pertence ao conjunto de tokens de
   `S`.

Em pseudocódigo:

```python
def corresponde(cifra_musica, acordes_sequencia):
    m = [a.lower() for a in cifra_musica]
    s = [a.lower() for a in acordes_sequencia]
    k = len(s)
    if k == 0 or k > len(m):
        return False
    if not any(m[i:i + k] == s for i in range(len(m) - k + 1)):
        return False
    vocabulario = set(s)
    return all(acorde in vocabulario for acorde in m)
```

Propriedades, todas verificadas na pesquisa:

- **Ordem importa** (condição 1).
- **Repetições não importam** (a condição 2 é teste de pertinência; a condição 1
  aceita qualquer número de repetições em volta do bloco).
- **Um acorde fora da sequência desqualifica a música** (condição 2).
- **Case é normalizado para minúsculas** nos dois lados.
- **Nenhuma outra normalização**: sem equivalência enarmônica (`C#` vs `Db`),
  sem unificação de sufixos (`Am` vs `Am7`), sem tratamento de baixo invertido
  (`C/E`) ou parênteses.

A variante escolhida é a **alinhada a tokens**, não a de substring no texto
unido. A pesquisa (§2.3 e §2.4) mostra que as duas produzem o mesmo conjunto de
`id_unico_musica` nas 6 sequências, nas duas tokenizações; a alinhada a tokens
elimina o caso teórico de casamento no meio de um token (`m;g` dentro de
`bm;g`) sem alterar o comportamento observado.

A regra vale para **todas** as sequências, antigas e novas. Não há modo
"estrito" separado: uma sequência criada pelo usuário pode retornar poucos ou
nenhum resultado, e isso é o comportamento definido, não um bug.

**Ordem dos resultados:** inalterada. O caminho por sequência continua iterando
`musicas.values()` filtrado por `apply_filtro` (`main.py:203-223`,
`main.py:266-272`), sem `sorted` adicional. Como `musicas` é ordenado por
popularidade no carregamento (`main.py:88-89`), o efeito prático é popularidade
decrescente dentro de cada gênero, com a concatenação de gêneros na ordem do
filtro. A paginação continua em 100 (`main.py:226-228`).

**Remoção da tag do runtime:** `Musica` deixa de guardar `seqs_famosas`
(`musica.py:5`, `musica.py:18`) e `main.py` deixa de fazer o split da coluna 7
(`main.py:63`) e de passá-la ao construtor (`main.py:71`). A coluna
`SEQ_FAMOSA` permanece no CSV **apenas** como oráculo do teste de regressão,
lido em `scripts/validar_matching.py:92` e comparado em `:213-225`.

### Banco de dados

**SQLite**, via `sqlite3` da biblioteca padrão. A imagem já traz SQLite 3.46.1
(research §3.2), então não há dependência nova em `requirements.txt`; o banco é
um arquivo único, transacional e portátil, o que mantém a intenção da ADR 0001
de não acoplar a uma plataforma.

- **Caminho:** `/app/instance/sequences.db` no container; `instance/sequences.db`
  no virtualenv local (mesmo diretório relativo ao projeto). O caminho pode ser
  sobrescrito por `SEQUENCES_DB` para testes.
- **Persistência:** `VOLUME /app/instance` no `Dockerfile`. O `README.md` e o
  `AGENTS.md` passam a documentar o comando com volume nomeado:
  `docker run -p 8080:8080 -v ciframe-data:/app/instance ciframe`.
  Sem o `-v`, o arquivo sobrevive a `docker restart` (camada do container), mas
  se perde em `docker rm` + `docker run` — exatamente o cenário que a feature
  precisa evitar.
- **Por que não `/app/data`:** `Dockerfile:8` faz `COPY . .` e embute o CSV de
  15,8 MB na imagem; um bind mount sobre `/app/data` esconderia
  `data/top/dataset_final.csv` (research §3.2).
- **Concorrência:** o gunicorn roda com 1 worker (`Dockerfile:12`), então um
  escritor por vez é suficiente. A conexão é aberta por requisição, com
  `busy_timeout` para evitar `database is locked` caso o número de workers
  aumente no futuro.
- **Escopo do banco:** somente o catálogo de sequências. Músicas, gêneros e
  acordes continuam no CSV em memória.

Alternativas descartadas: `shelve`/`dbm` (formato dependente de `pickle` e da
implementação de `dbm`, sem inspeção SQL), JSON/CSV próprio (reescrita integral,
sem concorrência segura) e banco com serviço separado (contraria a ADR 0001).
Detalhes em "Alternativas consideradas e descartadas".

### Esquema de dados (alto nível)

Uma tabela, sem migração complexa: `init_db()` cria a tabela se não existir e
semeia as 6 sequências de forma idempotente.

| Coluna | Tipo | Papel |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Identificador usado pela API (`sequencia_id`) |
| `name` | `TEXT NOT NULL` | Nome exibido; para as 6, vem de `data/mapeamento_sequencias_famosas.txt` |
| `chords` | `TEXT NOT NULL` | Lista ordenada, na grafia exibida, unida por `;` (ex.: `Bm;G;D;A`) |
| `chords_norm` | `TEXT NOT NULL UNIQUE` | Mesma lista em minúsculas, unida por `;`; chave de deduplicação |
| `source` | `TEXT NOT NULL CHECK (source IN ('legacy','user'))` | Origem da linha |
| `legacy_key` | `TEXT UNIQUE NULL` | Chave antiga (`BmGDA`, `CGAmF`, ...) para compatibilidade de URL; `NULL` para sequências novas |
| `created_at` | `TEXT NOT NULL DEFAULT (datetime('now'))` | Auditoria mínima |

As 6 linhas semeadas, na ordem de `main.py:40-45`, com nomes de
`data/mapeamento_sequencias_famosas.txt`:

| `legacy_key` | `chords` | `name` |
|---|---|---|
| `BmGDA` | `Bm;G;D;A` | Sequência de Bm |
| `CGAmF` | `C;G;Am;F` | Sequência de C |
| `EmG` | `Em;G` | Sequência Em |
| `CA7DmG7` | `C;A7;Dm;G7` | Sequência de C (Samba) |
| `GmF` | `Gm;F` | Sequência de Gm |
| `CC7FFm` | `C;C7;F;Fm` | Sequência de C (Samba cont.) |

Não há tabela de músicas, gêneros ou tags. Não há framework de migração: a
evolução do esquema fica registrada em `PRAGMA user_version`, se necessário.

### API

Todos os endpoints continuam devolvendo `json.dumps(...)` como string, com
`Content-Type: text/html`, conforme `AGENTS.md` e `main.py:197`. O CORS `*` de
`main.py:274-277` permanece.

**`GET /sequencias`** — catálogo completo, ordenado por `id` (as 6 primeiro):

```json
[
  {"id": 1, "nome": "Sequência de Bm", "acordes": ["Bm", "G", "D", "A"], "origem": "legacy"},
  {"id": 2, "nome": "Sequência de C",  "acordes": ["C", "G", "Am", "F"], "origem": "legacy"}
]
```

**`POST /sequencias`** — cadastro anônimo. Corpo JSON:

```json
{"nome": "Pop simples", "acordes": ["C", "G", "Am", "F"]}
```

- `nome` é opcional; se ausente, é derivado dos acordes (`C - G - Am - F`).
- `acordes` é obrigatório, lista não vazia de strings, na ordem em que o usuário
  digitou. Limites: no máximo 32 acordes, cada um com 1 a 20 caracteres após
  `strip`; `;` é rejeitado dentro de um acorde.
- A canonicalização é **somente** `strip` + `lower` (`chords_norm`). Nada de
  enarmonia, sufixos ou baixo invertido.
- **Duplicata:** se `chords_norm` já existe, **devolve a linha existente com
  HTTP 201**, sem criar outra. O `nome` enviado é ignorado nesse caso.
- Sequência nova: `201` com a linha criada (`id`, `nome`, `acordes`, `origem`).
- Entrada inválida: `400` com `{"erro": "..."}`.
- Sem login, sem rate limit e sem moderação nesta iteração (risco aceito).

**`GET /similares`** — alteração mínima, mantendo o contrato atual:

- `sequencia_id=<int>`: novo caminho para qualquer linha do catálogo.
  `id` inexistente ou inválido devolve `[]` com HTTP 200, preservando o
  comportamento atual para sequência desconhecida.
- `sequencia=<legacy_key>`: mantido para as 6 chaves antigas (`BmGDA`,
  `CGAmF`, ...). O frontend atual envia `Bm,G,D,A`, que continua funcionando
  porque `main.py:191` remove as vírgulas antes de consultar. O frontend novo
  passa a usar `sequencia_id`.
- `pagina` (default `1`, 100 por página) e `generos` continuam iguais.
- O formato de cada item da resposta continua idêntico ao de
  `get_similares_por_sequencia` (`main.py:210-220`): `id_unico_musica`,
  `id_artista`, `id_musica`, `nome_artista`, `nome_musica`, `popularidade`,
  `acordes`, `genero`, `url`. **Não** inclui `diferenca`.

`sequencia_id` é o identificador estável para sequências novas; não é necessário
aceitar lista de acordes crua na query string.

### Frontend

`#/porsequencia` passa a refletir o catálogo real e a permitir cadastro:

- **Catálogo:** remover os 4 presets hardcoded (`sequencia.js:2-37`) e carregar
  `GET /sequencias` no `init` do controller. A lista mostra as 6 originais mais
  as novas, com nome; as chaves antigas continuam aceitas por
  `GET /similares?sequencia=`.
- **Busca:** `pesquisarPorSequencia` passa a montar
  `similares?sequencia_id=<id>` em vez de concatenar acordes
  (`sequencia.js:55-77`). O filtro de gênero continua.
- **Cadastro:** construtor de sequência **ordenada** na mesma página. O usuário
  clica em acordes de uma paleta (reaproveitando a lista de `acordes.js:2-44`,
  extraída para uma constante/serviço compartilhado), os acordes entram no fim
  da lista, e clicar em um acorde já adicionado o remove. Um botão "Salvar"
  faz `POST /sequencias`; com o `id` devolvido, a busca é disparada. Não é
  preciso editor de reordenação sofisticado nesta iteração: remover e readicionar
  cobre a ordem.
- **Paginação:** enviar `pagina` (`sequencia.js:73` nunca envia) e oferecer
  "carregar mais" acumulando resultados. Sem isso, as sequências 0 (199) e 1
  (296) continuam truncadas em 100 (`main.py:226-228`).
- **Resultados:** remover `ng-hide="music.diferenca.length"`
  (`sequencia.html:43`), porque `diferenca` não existe no caminho por sequência.
- **Gêneros:** alimentar o `<select>` com `GET /generos` em vez da constante
  `GENEROS` (`app.js:6-58`), que tem 51 entradas contra 52 do backend e não
  inclui `R&B;`.
- **Visual:** manter o directive `df-hex` e o grid atuais; usar a cor padrão
  `#2E1C74` para os acordes.
- **Estado vazio:** explicar que a busca usa bloco contíguo com vocabulário
  fechado, para o usuário entender por que uma sequência nova pode retornar
  zero resultados.

### Sistemas impactados

| Sistema | Arquivo | Mudança |
|---|---|---|
| Persistência | `db.py` (novo), `Dockerfile`, `README.md`, `AGENTS.md`, `.gitignore` | SQLite, `VOLUME`, `-v`, `instance/` ignorado |
| Matching | `matching.py` (novo), `main.py:203-223` | Regra E em runtime |
| Modelo | `musica.py`, `main.py:63,71` | Remove `seqs_famosas` |
| API | `main.py:170-201` | `GET/POST /sequencias`, `sequencia_id` |
| Frontend | `sequencia.js`, `sequencia.html`, `app.js` | Catálogo, construtor, paginação, gêneros |
| Testes | `scripts/validar_matching.py` | Seção de regressão contra o matcher de runtime |

## Alternativas consideradas e descartadas

1. **Definição A (contígua, sem vocabulário fechado) para todas as sequências.**
   Aumentaria muito o recall (972/1.246/3.704/96/1.522/144), mas quebraria a
   regressão obrigatória das 6 (`199/296/4/5/7/3`). Descartada pelo critério
   explícito do enunciado.
2. **Dois modos (tag legada para as 6 + contíguo para as novas).** Preserva a
   regressão sem tocar no caminho antigo e dá resultados úteis para sequências
   novas, mas cria duas semânticas para a mesma busca. Foi a Proposta 2 da
   ideação; descartada porque o requisito é que qualquer sequência funcione "do
   mesmo jeito que hoje".
3. **Manter a tag e só permitir sequências previamente cadastradas.** Não atende
   ao requisito de cadastro aberto.
4. **Deduplicar os acordes da música antes de comparar (Definição B).** Perde
   301 músicas que a tag atual encontra, porque repetições fazem parte de
   progressões reais. Descartada.
5. **Normalizar acordes além de minúsculas** (unificar `7M`/`7+`, reduzir à raiz
   ou usar `NCIFRA`). Unificar sétima maior não muda as 6, mas reduzir à raiz
   leva a sequência 3 de 5 para 140 músicas (research §5.1), quebrando a
   regressão e introduzindo dependência de tom/transposição. Descartada.
6. **`shelve`/`dbm` ou arquivo JSON/CSV.** Viáveis no container, mas com
   formato dependente de `pickle`/`dbm`, sem consulta SQL e com reescrita
   integral a cada cadastro. SQLite já está na imagem e é mais simples de
   evoluir.
7. **Banco em serviço separado (Postgres/Redis).** Contraria a ADR 0001
   (container único, sem serviço externo adicional).
8. **Estado só em memória.** Atenderia ao cadastro, mas viola o requisito de
   persistência entre reinícios.
9. **Índice invertido / pré-cálculo de matches no startup.** Otimização
   prematura: a varredura por requisição já é o padrão atual
   (`main.py:203-223`). Fica como próximo passo se a latência medida piorar.

## Decisões registradas (open questions)

| # | Questão | Decisão |
|---|---|---|
| 1 | Vocabulário fechado para sequências novas? | **Sim**, para manter o comportamento atual idêntico para todas as sequências |
| 2 | Nível de normalização | **Somente minúsculas** (`lower`); nenhuma equivalência de grafia |
| 3 | Sequência duplicada | **Devolver a existente com HTTP 201**, sem criar nova linha |
| 4 | Rate limit / moderação do cadastro anônimo | **Fora de escopo nesta iteração**; risco aceito |
| 5 | Ordem dos resultados | **Manter a ordem atual** (`musicas.values()` filtrado por gênero, sem `sorted`) |
| 6 | Persistência | **`VOLUME /app/instance` na imagem** e `-v ciframe-data:/app/instance` documentado em `README.md` e `AGENTS.md` |
| 7 | `Musica.seqs_famosas` | **Remover do runtime**; a coluna `SEQ_FAMOSA` do CSV fica só para o teste de regressão |

Decisões menores tomadas para permitir implementação e teste:

- Limites de entrada: 32 acordes, 20 caracteres por acorde, 80 no nome.
- Nome opcional, derivado dos acordes quando ausente.
- `sequencia_id` é o identificador da API; `sequencia=<legacy_key>` fica só para
  compatibilidade das 6.
- `GET /sequencias` não calcula contagem de matches por sequência (evita 6
  varreduras no carregamento da página).

## Escopo explícito

**Dentro do escopo:**

- Banco SQLite com o catálogo de sequências, semeado com as 6 originais.
- Matcher em runtime com a semântica da tag (Definição E), aplicado a todas as
  sequências.
- `GET /sequencias`, `POST /sequencias` e `GET /similares?sequencia_id=`.
- Compatibilidade de `GET /similares?sequencia=<legacy_key>` para as 6.
- Remoção de `seqs_famosas` do runtime, mantendo a coluna do CSV para regressão.
- Frontend `#/porsequencia` orientado ao catálogo, com construtor de sequência
  ordenada, paginação e gêneros vindos do backend.
- `VOLUME` na imagem e documentação do `-v` em `README.md`/`AGENTS.md`.
- Teste de regressão por conjunto de `id_unico_musica` contra a tag.

**Fora do escopo (e por quê):**

- Autenticação, moderação, rate limit e edição/exclusão de sequências — o
  requisito é cadastro aberto e anônimo; abuso é risco aceito nesta iteração.
- Migrar músicas/gêneros para o banco — o enunciado fixa o CSV em memória.
- Normalização de acordes além de minúsculas — mudaria os resultados das 6.
- Matching por graus (`NCIFRA`) ou independente de tom — outra feature.
- Alterar a ordem dos resultados do caminho por sequência — comportamento atual
  preservado.
- Reescrever o frontend ou trocar AngularJS — a ADR 0003 apenas libera tocar no
  frontend quando necessário.
- Framework de migração de banco, múltiplos workers ou deploy em nuvem — a ADR
  0001 mantém o alvo indefinido e o container único.
- Alterar `scripts/generate_data_set.py` ou o CSV — a tag continua sendo gerada
  como hoje, só deixa de ser usada em runtime.
