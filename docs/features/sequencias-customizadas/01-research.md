# Pesquisa — Sequências de Acordes Customizadas

## Perguntas que você precisa responder

1. **Algoritmo de matching**: hoje, as 6 sequências hardcoded em `main.py` (linhas
   40-45) são comparadas contra músicas via uma tag pré-computada
   (`SEQ_FAMOSA`/`seqs_famosas`, vinda do CSV). Sequências cadastradas pelo usuário
   não têm essa tag — o matching precisa ser calculado em tempo real a partir da
   lista de acordes de cada música (`musica.acordes`/`musica.cifra`). O que vai
   definir "a sequência X aparece na música Y"? A ordem dos acordes importa?
   Repetições de acorde dentro da música importam? É preciso normalizar (ex.:
   maiúsculas/minúsculas, variações de escrita do mesmo acorde)?
2. **Validação da hipótese**: rode o algoritmo que você está considerando contra os
   dados reais em `data/top/dataset_final.csv`, para as 6 sequências hoje
   hardcoded, e confirme (ou refute) que ele reproduz os mesmos matches que o
   código atual produz via `seqs_famosas`. Esse é o bar mínimo de correção que
   você vai usar na fase de testes.
3. **Banco de dados**: quais bancos embarcados (sem serviço externo adicional) são
   viáveis dentro do container Docker único e local-only já documentado em
   `docs/adr/0001-local-only-docker-deploy.md`? O que cada opção implica para o
   `Dockerfile` atual e para a persistência dos dados entre reinícios do
   container?
4. **Frontend existente**: o que a página `#/porsequencia`
   (`static/templates/sequencia.html` +
   `static/assets/js/controllers/sequencia.js`) já faz? Repare que ela tem hoje uma
   lista *hardcoded no JavaScript* de 4 sequências (`sequencia1`..`sequencia4`),
   diferente das 6 que existem no backend — um detalhe real e pré-existente do
   código, não um erro seu, que vale entender antes de decidir o que precisa
   mudar.

---

## Registro das descobertas

### 1. Algoritmo de matching

#### 1.1 O que o código faz hoje

O matching das 6 sequências **não é calculado em tempo de requisição**. Ele é
lido de uma coluna do CSV:

- `main.py:33` — `SEQ_FAMOSA = 7` (índice da coluna).
- `main.py:63` — `musica[SEQ_FAMOSA] = musica[SEQ_FAMOSA].split(";")`.
- `main.py:71` — o valor vai para o construtor de `Musica`.
- `musica.py:18` — `self.seqs_famosas = seqs_famosas`.
- `main.py:209` — o teste é `if str(id_seq) in musica.seqs_famosas`.

Ou seja: o "algoritmo" em runtime é uma **consulta a uma tag pré-computada**, um
`in` de string em lista. Não há nenhum caminho no código que compare a lista de
acordes de uma música com uma sequência fornecida pelo usuário.

O único matching por acordes calculado em runtime é o de `/similares?acordes=`
(`main.py:240-245`), que usa interseção de conjuntos
(`set(acordes) & set(musica.acordes)`) e **ignora ordem e repetição por
construção**, porque `musica.acordes` já é `list(set(cifra))` (`musica.py:17`).
Esse endpoint não é "sequência": ele ranqueia por `len(diferenca)` e
`-len(intersecao)` (`main.py:263`).

O caminho de sequência também não ordena nada: os resultados saem na ordem de
`musicas.values()` (popularidade decrescente, `main.py:88-89`) filtrada por
`apply_filtro` (`main.py:266-272`), sem `sorted` — diferente do caminho por
acordes.

#### 1.2 De onde vem a tag `SEQ_FAMOSA`

Gerada no scraping, em `scripts/generate_data_set.py`:

- `scripts/generate_data_set.py:7-24` — `get_famosas(acorde)`.
- `scripts/generate_data_set.py:8` — lista fixa de 6 sequências, na mesma ordem
  do `dict` de `main.py:40-45`:
  `['bm;g;d;a', 'c;g;am;f', 'em;g', 'c;a7;dm;g7', 'gm;f', 'c;c7;f;fm']`.
  O índice na lista é o número que vira tag.
- `scripts/generate_data_set.py:69-76` — `str_notas` é montado concatenando com
  `;` o texto de todas as tags `<b>` dentro do elemento pai de `#cifra_tom`
  (a sequência de acordes exibida na cifra). Se não houver nenhuma, vira `'NA'`.
- `scripts/generate_data_set.py:84-88` — `famosas = ''.join(get_famosas(str_notas))`
  e a linha é impressa com `famosas` na 8ª coluna.
- `scripts/generate_data_set.py:89` — o CSV é impresso **sem cabeçalho**, na
  ordem `artista, musica, nome_artista, nome_musica, nome_estilo, popularidade,
  tom, famosas, str_notas` — exatamente a ordem das constantes de
  `main.py:26-34`.

O repositório também guarda a nomenclatura dessas sequências em
`data/mapeamento_sequencias_famosas.txt`:

```
0,Sequência de Bm,Bm - G - D - A
1,Sequência de C,C - G - Am - F
2,Sequência Em,Em - G
3,Sequência de C (Samba),C - A7 - Dm - G7
4,Sequência de Gm,Gm - F
5,Sequência de C (Samba cont.),C - C7 - F - Fm
```

Isso explica por que as sequências 3 e 5 existem separadas: são o mesmo centro
tonal (C) com duas progressões distintas de samba.

#### 1.3 Semântica exata da tag (definição validada)

Para uma música com sequência de acordes `C = [c1..cn]` e uma sequência famosa
`S = [s1..sk]` (ambas em minúsculas), `get_famosas` marca a música com o índice
de `S` quando **as duas condições valem**:

1. **Substring contígua no texto unido por `;`** —
   `scripts/generate_data_set.py:13`: `if s in acorde`, onde `s` é
   `'bm;g;d;a'` e `acorde` é `';'.join(C)` em minúsculas. Como os tokens são
   separados por `;`, isso equivale a `S` aparecer como bloco contíguo de tokens
   em `C`.
2. **Vocabulário inteiro da música contido no conjunto da sequência** —
   `scripts/generate_data_set.py:16-20`: o loop percorre `acorde.split(';')`,
   isto é, **os acordes da música** (não os da sequência), e exige que cada um
   esteja em `s.split(';')`.

Consequências diretas, verificáveis nos dados:

- **Ordem importa** (condição 1).
- **Repetição não importa** (condição 2 é teste de pertinência; repetições não
  criam exigência nova, e a condição 1 aceita qualquer número de repetições em
  volta do bloco).
- **Um acorde extra desqualifica a música** (condição 2 exige que *todo* o
  vocabulário da música esteja na sequência). É por isso que os totais são
  pequenos: 199, 296, 4, 5, 7 e 3 músicas.
- **Case é normalizado para minúsculas** (`scripts/generate_data_set.py:12`),
  então `Bm` e `bm` são o mesmo token.
- **Nenhuma outra normalização existe**: não há equivalência enarmônica
  (`C#` vs `Db`), nem unificação de sufixos (`Am` vs `Am7`), nem tratamento de
  baixo invertido (`C/E`), nem de parênteses. Os tokens são comparados como
  strings cruas.

Detalhes factuais do código gerador:

- `acorde = acorde.lower()` está **dentro** do loop das sequências
  (`scripts/generate_data_set.py:12`); é idempotente, então não muda o
  resultado.
- `tem_seqs` é recriada a cada iteração e recebe no máximo um elemento
  (`scripts/generate_data_set.py:15`, `:22`), e `out.append("-".join(tem_seqs))`
  (`:23`) produz só `"0"`, `"1"`, etc. O `"-"` nunca aparece no CSV final.
- `''.join(...)` em `scripts/generate_data_set.py:88` concatenaria tags sem
  separador se duas sequências casassem na mesma música (ex.: `"01"`), e
  `main.py:63` faria `split(";")` → `["01"]`, que não casa com `"0"` nem `"1"`.
  Nos dados atuais isso não ocorre (ver §2.1).
- `str_notas` é o texto exibido na página raspada, não uma sequência
  "musical" deduplicada: repetições aparecem, e acordes com baixo invertido
  aparecem como escritos (`C/E`).

#### 1.4 O que o código atual não faz

- Não recebe sequência do usuário: `main.py:194` só aceita chaves presentes no
  `dict` de `main.py:40-45`. Qualquer outra coisa cai em `similares = []` e
  retorna `[]` (`main.py:192-197`).
- A comparação de chave é **sensível a maiúsculas**: `?sequencia=BmGDA` → 100
  resultados na página 1; `?sequencia=bm,g,d,a` → `[]` (medido, §2.5).
- O backend remove vírgulas por concatenação (`main.py:191`,
  `sequencia_tag.replace(',','')`), então `"Bm,G,D,A"` e uma hipotética
  `"BmG,DA"` produzem a mesma chave `"BmGDA"`. Não há parsing de lista.
- Não há validação de entrada: `?sequencia=` ausente nem chega a esse ramo
  (`main.py:185-190`), e uma sequência desconhecida retorna `[]` com HTTP 200.

#### 1.5 Como os dados de acordes se apresentam

Medido em `data/top/dataset_final.csv`:

| Métrica | Valor |
|---|---|
| Linhas de dados no arquivo | 67.586 |
| Linhas efetivamente carregadas | 67.585 |
| Tokens de acorde distintos | 6.653 |
| Tokens que contêm alguma minúscula | 4.015 |
| Tokens com `/` (baixo invertido) | 3.808 |
| Tokens com `(` | 2.278 |
| Linhas com `CIFRA == 'NA'` no arquivo cru | 8.141 |
| Linhas em que `limpa_cifra` muda a tokenização | 83 |
| Tokens com `7M` ou `7+` | 683 |
| Tokens com `9` | 2.168 |
| Tokens com `sus` | 359 |

Os tokens mais frequentes são `G` (346.972 ocorrências), `D` (284.572), `C`
(267.143), `A` (244.312), `E` (201.723), `F` (164.123), `Am` (128.104), `Em`
(118.810), `B` (87.329), `Bm` (87.271).

Qualquer matching em runtime lida, portanto, com um vocabulário heterogêneo:
baixo invertido, parênteses, sufixos variados e grafias com minúscula (menor) e
maiúscula (maior).

### 2. Validação da hipótese

#### 2.1 Como o CSV é lido (e o que isso muda)

`main.py:49-63`:

- `main.py:50` — `f.readline()` descarta a **primeira linha de dados**, porque o
  arquivo não tem cabeçalho. A linha descartada é
  `14-bis,a-qualquer-tempo,14 Bis,A Qualquer Tempo,MPB,70115,B,NA,E;F#;E;F#;C#m7;F#`.
  Restam 67.585 músicas.
- `main.py:53` — `line.replace('"','').replace('NA','')` remove **todas** as
  ocorrências da substring `NA`, não só campos ausentes. Efeitos medidos:
  - 8.141 linhas tinham `CIFRA == 'NA'` e passam a ter `CIFRA == ''`
    (`main.py:58-61` as transforma em `[]`);
  - 7 títulos ficam corrompidos: `ROTINA DE POBRE` → `ROTI DE POBRE`,
    `DNA` → `D`, `CABANA` → `CABA`, `JULIANA` → `JULIA`,
    `BESTA RUANA` → `BESTA RUA`, e dois títulos com `(Versão ORIGINAL)` →
    `(Versão ORIGIL)`.
- `main.py:59` — `limpa_cifra` separa por `;`, descarta tokens vazios, corta
  tablaturas no `|` e separa acordes por espaço.
- `musica.py:17` — `self.acordes = list(set(cifra))` **perde ordem e
  repetição**; `self.cifra` preserva as duas (`musica.py:16`).

Distribuição da coluna 7 nas 67.585 linhas carregadas: `''` 67.071, `'1'` 296,
`'0'` 199, `'4'` 7, `'3'` 5, `'2'` 4, `'5'` 3. **Nenhuma linha tem mais de uma
tag** e não há `id_unico_musica` duplicado.

#### 2.2 As 5 definições candidatas testadas

Cada candidata foi aplicada a todas as 67.585 músicas carregadas, para as 6
sequências, e comparada com o conjunto de músicas que hoje têm a tag
correspondente na coluna 7.

| Definição | Contagem por sequência (0..5) | Extras vs. tag | Faltando vs. tag | Idêntica à tag? |
|---|---|---|---|---|
| A. Substring contígua no texto unido, case-insensitive | 972, 1246, 3704, 96, 1522, 144 | 7.170 | 0 | Não |
| B. Substring contígua sobre acordes deduplicados (`dict.fromkeys`) | 238, 385, 1650, 22, 799, 26 | 2.907 | 301 | Não |
| C. Conjunto da sequência ⊆ conjunto da música (ordem ignorada) | 5768, 6894, 14160, 582, 3847, 365 | 31.102 | 0 | Não |
| D. Subsequência ordenada (ordem sim, contiguidade não) | 4763, 5887, 13643, 427, 3641, 280 | 28.127 | 0 | Não |
| **E. Substring contígua + todo acorde da música ∈ conjunto da sequência** | **199, 296, 4, 5, 7, 3** | **0** | **0** | **Sim** |

Baseline (tag pré-computada): `[199, 296, 4, 5, 7, 3]`.

**Resultado:** apenas a definição **E** reproduz exatamente os matches atuais,
para as 6 sequências, nos 67.585 registros. A definição E é exatamente a
semântica descrita em §1.3, o que confirma que a leitura do gerador está correta.

Observações sobre as demais:

- A, C e D são **superconjuntos estritos** da tag: não perdem nenhuma música,
  mas trazem de 91 a 14.156 músicas a mais por sequência.
- B perde 301 músicas porque deduplicar a música antes de procurar o bloco
  contíguo quebra progressões que só aparecem com repetição.

#### 2.3 Como a igualdade foi verificada (conjuntos de IDs, não contagens)

A comparação não foi feita por contagem. Para cada sequência foram montados dois
**conjuntos de identificadores** — um com as músicas que a candidata seleciona,
outro com as músicas cuja coluna 7 contém a tag — e comparados com `==`; as
colunas "Extras" e "Faltando" da tabela são `|regra − tag|` e `|tag − regra|`.
Extras = 0 e faltando = 0, nas 6 sequências, equivale a igualdade de conjuntos,
não a coincidência de totais.

Reexecutado com o identificador real (`id_unico_musica`, ou seja
`artista_id + "_" + musica_id`, `musica.py:20`):

```
0 BmGDA    regra=199 tag=199 iguais=True  so_regra=0 so_tag=0
1 CGAmF    regra=296 tag=296 iguais=True  so_regra=0 so_tag=0
2 EmG      regra=  4 tag=  4 iguais=True  so_regra=0 so_tag=0
3 CA7DmG7  regra=  5 tag=  5 iguais=True  so_regra=0 so_tag=0
4 GmF      regra=  7 tag=  7 iguais=True  so_regra=0 so_tag=0
5 CC7FFm   regra=  3 tag=  3 iguais=True  so_regra=0 so_tag=0
```

Também foi testada a variante **alinhada a tokens** (bloco contíguo comparado
token a token, em vez de substring no texto unido), porque a checagem por
substring aceita, em tese, casamento no meio de um token (`'m;g'` é substring de
`'bm;g'`). Nas 6 sequências os dois conjuntos são **idênticos**, então esse caso
não ocorre neste dataset.

#### 2.4 O que está e o que não está garantido

A tag foi calculada no scraping sobre `str_notas` (texto das tags `<b>`,
`scripts/generate_data_set.py:70-76`), enquanto o teste em runtime usa a
tokenização de `limpa_cifra` (`main.py:11-23`). Para isolar esse fator, a
definição E foi rodada nas **duas** tokenizações (campo cru do CSV dividido por
`;` e tokens de `limpa_cifra`) e nas **duas** variantes de comparação
(substring e alinhada a tokens). As 4 combinações dão conjunto de IDs idêntico
ao da tag nas 6 sequências.

- **Garante**, para as 67.585 linhas deste `data/top/dataset_final.csv`, que a
  regra E seleciona exatamente o mesmo conjunto de `id_unico_musica` que a
  coluna 7 para as 6 sequências. É igualdade empírica de conjuntos, não
  coincidência de totais.
- **Não garante** que a regra seja equivalente à tag para uma sequência
  arbitrária ou para outro dataset. A equivalência é uma propriedade observada
  nos dados atuais; as 83 linhas em que a tokenização muda simplesmente não
  alteram o resultado destas 6 sequências.
- **Não diz nada** sobre sequências cadastradas por usuário: para elas não
  existe tag, logo não há baseline para comparar. A única referência de
  "correção" disponível hoje é a reprodução do comportamento das 6 existentes.

#### 2.5 Verificação pelo endpoint real

Dentro da imagem Docker (`ciframe-research:latest`, base `python:3.9-slim`), com
`Flask.test_client()`:

| Requisição | Resultado |
|---|---|
| `/similares?sequencia=BmGDA` | 100 itens (página 1 de 199) |
| `/similares?sequencia=BmGDA&pagina=2` | 99 itens (páginas 1+2 = 199) |
| `/similares?sequencia=CGAmF` | 100 itens (página 1 de 296) |
| `/similares?sequencia=CGAmF&pagina=2` e `=3` | 100 e 96 itens (páginas 1+2+3 = 296) |
| `/similares?sequencia=EmG` | 4 itens |
| `/similares?sequencia=CA7DmG7` | 5 itens |
| `/similares?sequencia=GmF` | 7 itens |
| `/similares?sequencia=CC7FFm` | 3 itens |
| `/similares?sequencia=bm,g,d,a` | `[]` |
| `/similares?sequencia=XXYY` | `[]` |

`Content-Type` de todas as respostas: `text/html; charset=utf-8` — coerente com
`json.dumps` sem `jsonify` (`main.py:197`, `main.py:201`; registrado em
`AGENTS.md`).

### 3. Banco de dados

#### 3.1 Estado atual

Não há banco. Todo o estado é:

- `musicas_dict` / `musicas` — `main.py:47`, `main.py:88-89`.
- `generos`, `genero_musicas`, `acordes` — `main.py:37-39`, `main.py:82-85`.
- `sequencias` — `dict` literal em `main.py:40-45`.

Tudo é reconstruído no import do módulo a partir de
`data/top/dataset_final.csv` (`main.py:49`). `AGENTS.md` reforça: editar o CSV
"requires a restart: it's read once at import time, not per-request".

Dependências de terceiros: apenas `Flask==3.1.3` e `gunicorn==23.0.0`
(`requirements.txt:4-5`).

#### 3.2 Fatos medidos sobre o container

Inspeção de `ciframe-research:latest` (build local do `Dockerfile` do repo):

| Propriedade | Valor medido |
|---|---|
| Base | `python:3.9-slim` (`Dockerfile:1`) |
| Python | 3.9.25 |
| `sqlite3` (stdlib) | 3.46.1, importável |
| `dbm` / `shelve` (stdlib) | importáveis |
| `USER` | vazio → processo roda como **root** (uid 0) |
| `VOLUME` | `null` — nenhum volume declarado |
| `WORKDIR` | `/app` (`Dockerfile:3`) |
| `CMD` | `gunicorn --bind 0.0.0.0:8080 main:app` (`Dockerfile:12`) — sem `--workers`, portanto 1 worker |
| `/app` gravável | sim (`echo > /app/persist.txt` funciona) |

Teste de persistência executado:

1. `docker run -d` + `echo teste > /app/persist.txt` → arquivo criado.
2. `docker restart` → `cat /app/persist.txt` devolve `teste`.
3. `docker rm -f` + novo `docker run` → `ls /app/persist.txt` →
   `No such file or directory`.

Ou seja: o que se grava em `/app` vive na **camada gravável do container**,
sobrevive a `restart` e desaparece quando o container é recriado.

Detalhe relevante: `Dockerfile:8` faz `COPY . .`, então
`data/top/dataset_final.csv` (15,8 MB) está **dentro da imagem**. Um bind mount
sobre `/app/data` esconderia esse arquivo. `.dockerignore` só exclui `.git`,
`.venv`, `__pycache__` e `*.pyc`.

#### 3.3 Opções embarcadas viáveis (sem serviço externo)

| Opção | Disponível na imagem | Onde o dado vive | Persistência entre `docker run` | Implicação para o `Dockerfile` atual | Observações |
|---|---|---|---|---|---|
| **SQLite** (`sqlite3`, stdlib) | Sim, 3.46.1 | Arquivo único (ex.: `/app/data/app.db`) | Não, sem volume/bind mount; sim, com volume nomeado ou bind mount | Nenhuma mudança obrigatória para funcionar; declarar `VOLUME` ou documentar `-v` para persistir | Um escritor por vez; com 1 worker do gunicorn não há contenção entre processos. `sqlite3` já está na imagem, não entra em `requirements.txt` |
| **`shelve`/`dbm`** (stdlib) | Sim | Um ou mais arquivos no filesystem | Mesma regra do SQLite (camada vs. volume) | Idem | Chave-valor Python; serializa com `pickle`; não é consultável por SQL; formato dependente da implementação de `dbm` |
| **Arquivo JSON/CSV próprio** | Sim (stdlib `json`/`csv`) | Arquivo no filesystem | Mesma regra | Idem | Reescrita do arquivo inteiro a cada mudança; sem concorrência segura; legível e diffável |
| **Só memória (estado no processo)** | Sim | RAM do worker | Não (perde em `restart` e em recriação) | Nenhuma | Some também se o número de workers mudar; não há `--workers` hoje, logo 1 processo |
| **Banco com serviço separado** (Postgres etc.) | Não | Container/serviço à parte | Depende do serviço | Exigiria `docker-compose`, segundo serviço e rede | Fora do recorte "embarcado, sem serviço externo adicional" da pergunta |

### 4. Frontend existente (`#/porsequencia`)

#### 4.1 Fluxo atual

1. `routes.js:17-21` mapeia `#/porsequencia` para `templates/sequencia.html`
   com `SequenciaController` e `controllerAs: "Sequencia"`.
2. `sequencia.js:2-31` define **4 objetos** literais (`sequencia1`..
   `sequencia4`), cada um com `index: 1` (não usado em nenhum ponto) e uma lista
   `acordes` de `{acorde, cor}`; todas as cores são `#2E1C74`.
3. `sequencia.js:33-37` empilha os 4 em `vm.sequenciasFamosas`.
4. `sequencia.html:6-8` renderiza a lista com `ng-repeat` e um directive
   `df-hex` por acorde (`df-hex.js:1-12`, template
   `templates/directives/df-hex.html`); o `ng-click` da div chama
   `Sequencia.pesquisarPorSequencia(sequencia)`.
5. `sequencia.js:63-90` — `pesquisarPorSequencia`:
   - `:64-66` guarda a sequência clicada em `vm.minhaSequencia`;
   - `:73` monta `"similares?sequencia=" + createChordsString(...)`;
   - `createChordsString` (`:55-61`) concatena os acordes **separados por
     vírgula**;
   - `:74-76` acrescenta `&generos=` se `vm.meuGenero` estiver preenchido;
   - `:77` faz `$http.get` com `apiUrl = ""` (relativo);
   - `:83` joga a resposta direto em `vm.musics`.
6. `sequencia.html:24-30` — `<select>` de gênero alimentado por
   `Sequencia.generos`, que vem da constante `GENEROS` (`sequencia.js:43`),
   definida em `app.js:6-58`. `ng-change` (`sequencia.html:28`) redispara a
   busca.
7. `sequencia.html:40-59` — grid de resultados, `orderBy:'-popularidade'`
   (`:42`), `ng-hide="music.diferenca.length"` (`:43`), clique abre a URL da
   cifra no CifraClub (`sequencia.js:97-99`).
8. `sequencia.js:92-95` — `limparPesquisa` zera `vm.minhaSequencia` e
   `vm.musics`.

O backend correspondente: `main.py:190-197` recebe `sequencia`, remove as
vírgulas (`:191`), consulta o `dict` (`:194`) e pagina (`:196`).

#### 4.2 As 4 do JavaScript vs. as 6 do backend

| # no JS | Acordes no JS (`sequencia.js`) | String enviada | Chave após `replace(',','')` | Existe no `dict`? | Id no backend | Total no backend |
|---|---|---|---|---|---|---|
| `sequencia1` | Bm, G, D, A (`:2-9`) | `Bm,G,D,A` | `BmGDA` | Sim (`main.py:40`) | 0 | 199 |
| `sequencia2` | C, G, Am, F (`:10-17`) | `C,G,Am,F` | `CGAmF` | Sim (`main.py:41`) | 1 | 296 |
| `sequencia3` | Gm, F (`:18-23`) | `Gm,F` | `GmF` | Sim (`main.py:44`) | 4 | 7 |
| `sequencia4` | C, C7, F, Fm (`:24-31`) | `C,C7,F,Fm` | `CC7FFm` | Sim (`main.py:45`) | 5 | 3 |
| — | — | — | `EmG` | Sim (`main.py:42`) | 2 | 4 |
| — | — | — | `CA7DmG7` | Sim (`main.py:43`) | 3 | 5 |

Portanto: **a UI expõe 4 das 6 sequências**; as de id 2 (`EmG`) e 3
(`CA7DmG7`) existem no backend e são acessíveis por URL, mas não têm botão na
página. A ordem também difere: no JS a 3ª é `GmF` (id 4) e a 4ª é `CC7FFm`
(id 5); no backend a 3ª é `EmG` e a 4ª é `CA7DmG7`.

#### 4.3 Divergências e acoplamentos pré-existentes

| Item | Evidência | Efeito |
|---|---|---|
| Paginação | `sequencia.js:73` não envia `pagina`; `main.py:176` usa default `1`; `main.py:226-228` corta em 100 | A UI mostra no máximo 100 músicas. Para a sequência 0 (199) e a 1 (296), metade ou mais dos resultados fica invisível |
| Lista de gêneros | `app.js:6-58` tem 51 entradas; `/generos` retorna 52 | O gênero `R&B;` (303 músicas no CSV) existe no backend e não aparece no `<select>`. Os nomes são usados como chave literal em `apply_filtro` (`main.py:269-271`), então precisam bater exatamente |
| Campo `diferenca` | `sequencia.html:43` usa `music.diferenca.length`; `main.py:210-220` não devolve `diferenca` | O campo é `undefined` na resposta de sequência (só existe no caminho por acordes, `main.py:256`) |
| `RESTAPI` | `app.js:3-5` define `RESTAPI.url = 'http://localhost:5003'`; nenhum controller o injeta — todos usam `apiUrl = ""` (`sequencia.js:72`, `acordes.js:91`) | Constante morta; as chamadas são relativas à origem |
| `index` dos presets | `sequencia.js:3`, `:11`, `:19`, `:25` — todos `1` | Não é lido em nenhum template ou função |
| Vírgula como separador | `sequencia.js:58` junta com `,`; `main.py:191` remove com `replace(',','')` | O backend não recebe lista: recebe uma string concatenada. Sequências diferentes que concatenem igual viram a mesma chave |
| Case | `main.py:194` compara com as chaves capitalizadas | Enviar `bm,g,d,a` retorna `[]` (medido) |
| Seleção de acordes | `acordes.js:2-44` tem 33 acordes fixos (C, C#, Cm, ..., B7), com `addAcorde`/`temAcorde` (`:63-74`) | A página `#/poracordes` tem um seletor de acordes em memória; `sequencia.js` só tem presets e não tem seletor |
| Sem criação | `sequencia.js:38` inicializa `vm.minhaSequencia = {}` e só é preenchido por preset (`:65`) ou limpo (`:93`) | Não existe hoje nenhuma forma de o usuário montar uma sequência própria na UI |

---

## Trade-offs identificados

### 5.1 Algoritmo de matching

#### A regra que reproduz o comportamento atual é muito restritiva

A definição E é o único candidato que casa exatamente com a tag, mas ela exige
que a música **não tenha nenhum acorde fora da sequência**. O efeito medido:

| Sequência | Músicas que contêm o bloco contíguo (A) | Músicas que passam em E | Fração |
|---|---|---|---|
| 0 `Bm-G-D-A` | 972 | 199 | 20,5% |
| 1 `C-G-Am-F` | 1.246 | 296 | 23,8% |
| 2 `Em-G` | 3.704 | 4 | 0,11% |
| 3 `C-A7-Dm-G7` | 96 | 5 | 5,2% |
| 4 `Gm-F` | 1.522 | 7 | 0,46% |
| 5 `C-C7-F-Fm` | 144 | 3 | 2,1% |
| **Total** | **7.684** | **514** | **6,7%** |

A condição de vocabulário fechado descarta **7.170 pares música×sequência** que
contêm a progressão contígua. Para as 6 sequências atuais isso é o
comportamento correto (é o que a tag faz), mas para uma sequência cadastrada por
um usuário significa que **um único acorde de passagem elimina a música**. Uma
música que faz `C G Am F` e depois `Dm G` não aparece na busca por `C G Am F`.

Opções e implicações:

| Opção | O que muda em relação à tag atual | Implicação observada |
|---|---|---|
| Manter a tag pré-computada e só permitir sequências que já existam | Nada no runtime | Só funciona para as 6; não atende sequência do usuário |
| Calcular em runtime a mesma definição da tag (E) | Reproduz exatamente 199/296/4/5/7/3 | Consistência total com o histórico, ao custo da restritividade acima; exige varrer 67.585 músicas por requisição |
| Contígua, sem exigir vocabulário fechado (A) | 972/1246/3704/96/1522/144 | 4 a 900× mais resultados; deixa de reproduzir o comportamento atual, o que conflita com o critério de regressão das 6 |
| Conjunto, ordem ignorada (C) | 5.768 a 14.160 | Ignora o que caracteriza "sequência"; fica equivalente ao `/similares?acordes=` que já existe |
| Subsequência ordenada, não contígua (D) | 4.763 a 13.643 | Aceita progressões espalhadas pela música; grande aumento de resultados |
| Deduplicar a música antes de comparar (B) | 238/385/1650/22/799/26 | Perde 301 músicas que a tag atual encontra |
| Manter a tag para as 6 e usar outra regra para as novas | Duas semânticas convivendo | Preserva a regressão, mas a mesma busca responde de formas diferentes conforme a sequência ser antiga ou nova |

Sobre custo: o backend já percorre `musicas.values()` por requisição em
`get_similares` (`main.py:236`) e em `get_similares_por_sequencia`
(`main.py:208`), então varrer o dataset por requisição é o padrão atual; a
diferença é que hoje o teste é `in` em lista de tags (`main.py:209`) e passaria
a comparar listas de acordes.

#### Normalizar acordes: qual normalização, e o que ela muda

"Normalizar" não é uma escolha binária. Medi três níveis, aplicando a mesma
função aos acordes da música e aos da sequência, e rodando a definição E:

| Normalização | Contagem por sequência (0..5) | Mudou as 6? |
|---|---|---|
| Nenhuma (baseline da tag) | 199, 296, 4, 5, 7, 3 | — |
| Unificar 7ª maior: `C7M` / `C7+` / `Cmaj7` / `CM7` → `C7` | 199, 296, 4, 5, 7, 3 | **Não** |
| Reduzir à raiz: `C7M` → `C`, `Am7` → `A`, `D7M/F#` → `D` | 309, 452, 8, 140, 20, 10 | Sim, muito |
| Manter raiz + terça: `C7M` → `C`, `Am7` → `Am` | 286, 418, 4, 9, 9, 3 | Sim |

O primeiro nível altera **838 tokens distintos e 10.137 linhas**, mas não move
nenhuma das 6 contagens: unificar a grafia de sétima maior não cria nenhuma
música que satisfaça o bloco contíguo com vocabulário fechado. Já reduzir o
acorde à raiz ou a raiz+terça muda tudo — a sequência 3 (`C-A7-Dm-G7`) salta de
5 para 140 músicas quando `A7` e `G7` viram `A` e `G`.

Ou seja: o efeito de normalizar depende de **o quanto** se normaliza. Manter a
qualidade (maior/menor) e descartar extensões já muda os resultados; unificar só
grafias equivalentes, não.

O repositório já tem uma terceira representação, gerada fora da aplicação:

- `scripts/normalize_chords.R` e `scripts/simplify_chords.R` reduzem cada acorde
  à **raiz + acidente**, descartando a qualidade (`C7M` → `C`, `Am` → `A`), e
  traduzem para graus (`I`, `IV`, `V`...) usando o tom e
  `data/transposition_matrix2.csv`.
- O resultado está em `data/dataset_seq_notas.csv`, coluna `NCIFRA`: 66.525
  linhas, 66.502 com `NCIFRA` preenchido, cobrindo 66.523 das 67.585 músicas de
  `dataset_final.csv` (98,4%).
- Essa representação **não é carregada pela aplicação** — `main.py` lê apenas
  `data/top/dataset_final.csv`.

Implicações de cada nível de normalização:

| Nível | Prós observáveis | Contras observáveis |
|---|---|---|
| Nenhum (além de lowercase) | Reproduz a tag; previsível; nenhum dado novo | `C7M` e `C7` são músicas diferentes; 683 tokens com `7M`/`7+`, 3.808 com `/`, 2.278 com `(` |
| Unificar grafias equivalentes (`C7M`→`C7`, `C7+`→`C7`) | Não muda as 6 contagens; reduz falsos negativos de grafia | Não resolve baixo invertido, parênteses, `sus`/`add`/`9`; precisa de tabela de equivalências |
| Descartar extensões (raiz + terça) | Aproxima músicas "parecidas"; menos tokens | Muda as 6 contagens (seq 3: 5 → 9); deixa de reproduzir o comportamento atual |
| Só raiz (como `normalize_chords.R`) | Key-independent se combinado com graus; vocabulário mínimo | Muda as 6 contagens (seq 3: 5 → 140); perde maior/menor; depende do tom e de matriz de transposição |
| Usar `NCIFRA` (graus) | Sequência escrita uma vez serve para qualquer tom | Cobre 98,4% das músicas; é um arquivo separado, não carregado hoje; colapsa qualidade |

### 5.2 Banco de dados vs. ADR 0001

O que a ADR 0001 fixa (`docs/adr/0001-local-only-docker-deploy.md:9-16`):

- um **único `Dockerfile`**, rodando localmente via gunicorn;
- backend com a arquitetura atual — `main.py` único, busca em memória sobre o
  CSV, Python 3.9;
- alvo de nuvem **intencionalmente indefinido**, com o Docker escolhido
  justamente por "não travar em uma plataforma".

O enunciado da feature (`00-enunciado.md:63-68`) reforça: container único, sem
serviços externos adicionais, músicas/gêneros continuam no CSV em memória, e só
o catálogo de sequências vai para o banco. O requisito de persistência é
explícito: "Não volta a ser perdido ao reiniciar o container"
(`00-enunciado.md:52-53`).

| Opção | Cabe na ADR 0001? | O que implica para o `Dockerfile` | Persistência entre reinícios/recriação |
|---|---|---|---|
| SQLite (stdlib) | Sim — continua um container, sem serviço | Nada obrigatório para funcionar; para persistir, `VOLUME /app/data` ou `docker run -v ...`; `sqlite3` já está na imagem | Sobrevive a `restart` mesmo sem volume (camada do container); só sobrevive a `docker run` novo com volume/bind mount |
| `shelve`/`dbm` (stdlib) | Sim | Idem | Idem; formato dependente de `dbm`/`pickle` |
| JSON/CSV próprio | Sim | Idem | Idem; reescrita integral |
| Só memória | Sim, mas não atende ao requisito | Nenhuma | Perde em `restart` — falha o requisito |
| Postgres/Redis em outro container | Não — exige segundo serviço e rede | Exigiria `docker-compose`, rede, healthcheck, volume próprio | Depende do serviço; reintroduz o acoplamento de plataforma que a ADR evitou |

Prós e contras observáveis de cada caminho:

- **SQLite**: já presente na imagem (3.46.1), sem dependência nova em
  `requirements.txt`; transacional; um arquivo; portátil entre plataformas, o
  que preserva a intenção da ADR de não travar em nuvem. Contra: precisa de
  caminho gravável e de decisão explícita sobre volume; um escritor por vez
  (hoje irrelevante, porque o gunicorn roda com 1 worker).
- **`shelve`/`dbm`**: mesma simplicidade de arquivo, sem SQL. Contra: formato
  dependente da implementação de `dbm` e de `pickle`; não dá para inspecionar
  com SQL; migração futura fica mais frágil.
- **JSON/CSV próprio**: zero dependência, inspecionável, diffável. Contra:
  reescrita do arquivo inteiro a cada cadastro; sem concorrência segura.
- **Só memória**: nenhuma mudança de infraestrutura, mas viola diretamente o
  requisito de persistência.
- **Serviço externo**: melhor isolamento e concorrência, mas contraria o
  "container único, sem serviços externos adicionais" do enunciado e a intenção
  da ADR de não acoplar a uma plataforma.

Um ponto de atrito concreto para qualquer opção de arquivo: o comando
documentado hoje é `docker run -p 8080:8080 ciframe` (`AGENTS.md`), sem volume.
Sem mudar esse comando (ou declarar `VOLUME` na imagem), o banco fica na camada
do container e se perde na recriação — exatamente o cenário que o requisito
quer evitar.

### 5.3 Frontend

| Opção | O que envolve | Prós | Contras |
|---|---|---|---|
| Manter os 4 presets hardcoded e só adicionar um construtor | `sequencia.js:2-37`, `sequencia.html:6-8` | Mudança pequena; nada quebra | A lista continua divergindo das 6 do backend (ids 2 e 3 sem botão); o catálogo real não é refletido, o que conflita com o requisito |
| Derivar os presets do backend | Precisa de um endpoint que exponha o catálogo; hoje `sequencias` é `dict` interno (`main.py:40-45`) e não há rota | Elimina a divergência 4-vs-6 e reflete cadastros novos | Cria dependência de rede no carregamento da página; exige definir o formato da API |
| Reaproveitar o seletor de acordes de `#/poracordes` | `acordes.js:2-44`, `:63-74` | Já existe UI de seleção e o padrão de "clicar para marcar" | Hoje é um conjunto sem ordem (`meusAcordes` é lista, mas a semântica é de conjunto); sequência precisa de ordem |
| Corrigir a paginação | `sequencia.js:73`, `main.py:226-228` | Torna visível o resultado completo | Sem isso, qualquer sequência com mais de 100 matches continua truncada na UI (caso das sequências 0 e 1) |
| Alinhar a lista de gêneros | `app.js:6-58` vs. `/generos` | Consistência com o backend | Hoje falta `R&B;`; a lista hardcoded não acompanha o CSV |

---

## Apêndice A — como reproduzir

Todos os números deste documento saem de um script versionado:

```
python3 scripts/validar_matching.py [caminho_do_csv]
```

Ele não importa Flask nem `main.py` (só biblioteca padrão), lê o CSV do mesmo
jeito que `main.py:49-63` e imprime: distribuição da coluna 7, tabela das 5
definições candidatas, igualdade por `id_unico_musica`, variantes de
tokenização/alinhamento e efeito das normalizações.

Saída em `data/top/dataset_final.csv`:

```
== 1. Coluna SEQ_FAMOSA ==
linhas carregadas: 67585 (1a linha descartada, como main.py:50)
  '' (vazio)    67071
  '1'             296
  '0'             199
  '4'               7
  '3'               5
  '2'               4
  '5'               3
  linhas com mais de uma tag: 0
  id_unico_musica duplicados: 0

== 2. Definicoes candidatas (comparadas por conjunto de id_unico_musica) ==
definicao                              contagem por sequencia (0..5)      extras faltando igual
-----------------------------------------------------------------------------------------------
tag pre-computada (baseline)           [199,296,4,5,7,3]                       -        -     -
A. contigua (substring)                [972,1246,3704,96,1522,144]          7170        0   nao
B. contigua + acordes deduplicados     [238,385,1650,22,799,26]             2907      301   nao
C. conjunto (ordem ignorada)           [5768,6894,14160,582,3847,365]      31102        0   nao
D. subsequencia ordenada               [4763,5887,13643,427,3641,280]      28127        0   nao
E. contigua + vocabulario fechado      [199,296,4,5,7,3]                       0        0   sim

== 3. Igualdade da definicao E por id_unico_musica ==
  0 BmGDA    regra=199 tag=199 iguais=True  so_regra=0 so_tag=0
  1 CGAmF    regra=296 tag=296 iguais=True  so_regra=0 so_tag=0
  2 EmG      regra=  4 tag=  4 iguais=True  so_regra=0 so_tag=0
  3 CA7DmG7  regra=  5 tag=  5 iguais=True  so_regra=0 so_tag=0
  4 GmF      regra=  7 tag=  7 iguais=True  so_regra=0 so_tag=0
  5 CC7FFm   regra=  3 tag=  3 iguais=True  so_regra=0 so_tag=0

== 4. Variantes de comparacao e de tokenizacao ==
  E por substring        identica a tag nas 6 sequencias: True
  E alinhada a tokens    identica a tag nas 6 sequencias: True

== 5. Tokenizacao: campo cru vs limpa_cifra ==
  linhas em que limpa_cifra muda a tokenizacao: 83
  E por substring          com tokens crus identica a tag: True
  E por alinhada a tokens  com tokens crus identica a tag: True

== 6. Efeito de normalizar acordes (definicao E) ==
  normalizacao                         contagem por sequencia (0..5)
  -----------------------------------------------------------------------
  nenhuma (baseline da tag)            [199,296,4,5,7,3]
  7M/7+/maj7 -> 7                      [199,296,4,5,7,3]
  so raiz (C7M -> C)                   [309,452,8,140,20,10]
  raiz + terca (C7M -> C, Am7 -> Am)   [286,418,4,9,9,3]

  tokens distintos no dataset: 6653
  tokens alterados por 7M/7+/maj7 -> 7: 838
  linhas afetadas por 7M/7+/maj7 -> 7: 10137
```

Verificação do endpoint, dentro da imagem Docker:

```
docker run --rm ciframe-research:latest python -c "..."
'BmGDA'     -> 100 resultados | CT= text/html; charset=utf-8
'CGAmF'     -> 100 resultados | CT= text/html; charset=utf-8
'EmG'       ->   4 resultados | CT= text/html; charset=utf-8
'CA7DmG7'   ->   5 resultados | CT= text/html; charset=utf-8
'GmF'       ->   7 resultados | CT= text/html; charset=utf-8
'CC7FFm'    ->   3 resultados | CT= text/html; charset=utf-8
'bm,g,d,a'  ->   0 resultados | CT= text/html; charset=utf-8
'XXYY'      ->   0 resultados | CT= text/html; charset=utf-8
generos backend: 52 | R&B; presente: True
musicas carregadas: 67585
python: 3.9.25
sqlite3: 3.46.1
dbm/shelve: ok
```

Paginação somando páginas:

```
BmGDA soma paginas 1..4 = 199
CGAmF soma paginas 1..4 = 296
pagina 4 de BmGDA: 0
```

Inspeção e persistência do container:

```
USER= VOLUMES=null WORKDIR=/app CMD=["gunicorn","--bind","0.0.0.0:8080","main:app"]
0                                     # uid dentro do container (root)
-rw-r--r-- 1 root root 6 ... /app/persist.txt
teste                                 # após docker restart
ls: cannot access '/app/persist.txt': No such file or directory   # após novo docker run
```

## Apêndice B — índice de referências

| Assunto | Referência |
|---|---|
| Colunas do CSV | `main.py:26-34` |
| Carga do CSV e descarte da 1ª linha | `main.py:49-50` |
| `replace('NA','')` global | `main.py:53` |
| `limpa_cifra` | `main.py:11-23` |
| `TAM_PAGINA` | `main.py:35` |
| Dict de sequências | `main.py:40-45` |
| Split da tag | `main.py:63` |
| Ordenação por popularidade | `main.py:88-89`, `main.py:95-96` |
| Rota `/similares` | `main.py:170-201` |
| Caminho de sequência | `main.py:190-197` |
| `get_similares_por_sequencia` | `main.py:203-223` |
| Teste da tag | `main.py:209` |
| Paginação | `main.py:226-228` |
| Caminho por acordes | `main.py:230-263` |
| `apply_filtro` | `main.py:266-272` |
| `acordes = list(set(cifra))` | `musica.py:17` |
| `seqs_famosas` | `musica.py:18` |
| URL da cifra | `musica.py:22` |
| `get_famosas` | `scripts/generate_data_set.py:7-24` |
| Lista fixa de sequências | `scripts/generate_data_set.py:8` |
| `str_notas` | `scripts/generate_data_set.py:69-76` |
| Atribuição da tag | `scripts/generate_data_set.py:84-88` |
| Impressão do CSV | `scripts/generate_data_set.py:89` |
| Nomes das sequências | `data/mapeamento_sequencias_famosas.txt` |
| Normalização por graus (R) | `scripts/normalize_chords.R:8-30`, `scripts/simplify_chords.R:8-28` |
| Representação normalizada | `data/dataset_seq_notas.csv` (coluna `NCIFRA`) |
| Matriz de transposição | `data/transposition_matrix2.csv` |
| Presets do frontend | `static/assets/js/controllers/sequencia.js:2-37` |
| Montagem da query | `static/assets/js/controllers/sequencia.js:55-77` |
| Limpar pesquisa | `static/assets/js/controllers/sequencia.js:92-95` |
| Template da página | `static/templates/sequencia.html:1-63` |
| Select de gênero | `static/templates/sequencia.html:24-30` |
| Grid de resultados | `static/templates/sequencia.html:40-59` |
| Rota `#/porsequencia` | `static/assets/js/routes.js:17-21` |
| `GENEROS` e `RESTAPI` | `static/assets/js/app.js:3-58` |
| Seletor de acordes existente | `static/assets/js/controllers/acordes.js:2-44`, `:63-74` |
| Dockerfile | `Dockerfile:1-12` |
| ADR local-only | `docs/adr/0001-local-only-docker-deploy.md:9-16` |
| Requisitos da feature | `docs/features/sequencias-customizadas/00-enunciado.md:45-68` |
| Script de validação | `scripts/validar_matching.py` |
