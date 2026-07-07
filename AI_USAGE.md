# AI_USAGE — Registro de uso de IA

> Documento exigido pela Política de Uso de IA do case (seção 2). Mantido **incrementalmente durante o desenvolvimento** — cada entrada reflete um evento real da construção deste projeto.

## Ferramenta e fluxo de trabalho

- **Ferramenta:** Claude Code (Anthropic) como copiloto de engenharia, operado em sessão interativa.
- **Fluxo adotado:**
  1. Análise do case e planejamento em *plan mode*, com decisões de arquitetura tomadas e registradas explicitamente antes de qualquer código (stack, escopo, workflow de git);
  2. Implementação por fases (uma branch/PR por fase), com revisão humana do código gerado;
  3. Verificação contínua — testes, linters e type checkers rodando antes de cada commit (garantido por git hooks).
- **Transparência:** todos os commits levam o trailer `Co-Authored-By: Claude`, refletindo a coautoria de forma auditável no próprio histórico.

## Prompts estratégicos

| Fase | Prompt (resumo) | Resultado |
| --- | --- | --- |
| Planejamento | "Analise minuciosamente o case e faça um planejamento do melhor cenário de desenvolvimento, com as melhores práticas de arquitetura limpa" | Plano em 9 fases; decisões: arquitetura em 3 camadas com DIP, Strategy Pattern data-driven para precificação, relatórios em 2 camadas (CQRS-lite), simulação em tempo real feita **no backend** para evitar duplicar regra financeira em JS com float |
| Scaffolding | Geração dos skeletons de backend (FastAPI, 3 camadas, error handlers globais) e frontend (Vite + React TS) com tooling estrito | Estrutura pronta com mypy strict, ruff, eslint, prettier, vitest e pre-commit validados desde o primeiro commit |

## Onde a IA errou ou gerou código desatualizado (e como foi corrigido)

- **Constante deprecada do Starlette:** o código inicial dos error handlers usava `HTTP_422_UNPROCESSABLE_ENTITY`, deprecada em favor de `HTTP_422_UNPROCESSABLE_CONTENT` (RFC 9110). Detectado rodando `pytest -W error` (prática de tratar warnings como erro) e corrigido.
- **Config de pre-commit desatualizada:** a primeira versão da config usava o hook id legado `ruff` e revisões antigas dos repositórios de hooks. Corrigido com `pre-commit autoupdate` e migração para o id atual `ruff-check`.
- **Template do Vite 8 divergente do esperado:** o scaffold veio com `oxlint` (novo padrão do template) em vez de ESLint. Decisão humana: trocar por ESLint + typescript-eslint + prettier — ferramentas maduras e amplamente conhecidas, mais adequadas ao contexto de time em ambiente financeiro.

## Análise crítica (consolidada ao final)

- **Onde a IA economizou tempo:** *(preenchido ao final do desenvolvimento)*
- **Onde a IA atrapalhou:** *(preenchido ao final do desenvolvimento)*
