# Sessões do opencode (BigPickle)

Arquivo de entrega: `igor.falcao@ccc.ufcg.edu.br-reppit.json`, um array JSON com as
4 sessões abaixo na ordem das fases (cada item é a saída de
`opencode session export <id>`; o `opencode export` do form não existe na v2.0.14).

| Arquivo | Fase | Comando RePPIT |
| --- | --- | --- |
| `01-pesquisa.json` | 1. Pesquisa | `/research-codebase` |
| `02-proposta.json` | 2. Proposta + ADR | `/make-proposals` |
| `03-plano.json` | 3. Plano | `/make-plan` |
| `04-implementacao-e-testes.json` | 4. Implementação e 5. Testes | `/implement`, `/review-code` |

As fases 4 e 5 ficaram na mesma sessão: o passo 9 do plano já previa rodar a
regressão e preencher o `04-test-report.md`. Os commits dessa sessão saíram com
o prefixo "fase 3:" por engano do agente, mas são da implementação.

`evidencia-sequencias.webm` é a gravação feita pelo agente durante a
verificação no browser.
