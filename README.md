# SWAIF Factory (IssueOps + Spec Kit)

Este repositório é um “chão de fábrica” para transformar **Issues (intake do cliente)** em:
- `spec.md` → `plan.md` → `tasks.md`
- anexos coletados da issue (`attachments/`)
- branch `swaif/<feature_slug>` com PR (opcional)

## Como funciona (visão de 30s)
1) Crie uma issue usando o formulário **SWAIF Feature**.
2) (Opcional) anexe arquivos na issue (drag&drop) e cole os links no campo de artefatos.
3) Aplique labels `swaif:*` para disparar cada etapa (ou use comentário `/run ...`).
4) A automação grava tudo em `specs/<feature_slug>/`.

## Requisitos
- GitHub Actions habilitado no repo
- Secrets:
  - `PROJECTS_SECRET` (token com permissões para comentar issues e dar push em branch)
  - `OPENAI_API_KEY` (opcional, para gerar spec/plan/tasks automaticamente)

## Operação (labels)
- `swaif:init` → cria skeleton + intake.md (+ coleta anexos)
- `swaif:specify` → gera/atualiza spec.md (se OPENAI_API_KEY)
- `swaif:plan` → gera/atualiza plan.md (se OPENAI_API_KEY)
- `swaif:tasks` → gera/atualiza tasks.md (se OPENAI_API_KEY)
- `swaif:implement` → por padrão é conservador (placeholder)
- `swaif:verify` → checklist final

## Operação (comments)
- `/run specify`
- `/run plan`
- `/run tasks`
- `/run implement apply`

## Por que isso é “Spec Kit friendly”
O Spec Kit recomenda um fluxo: spec → plan → tasks, gerando artefatos por fase. citeturn0search0
Aqui fazemos o mesmo, mas acionado por IssueOps (GitHub Issues + Actions). citeturn0search14
