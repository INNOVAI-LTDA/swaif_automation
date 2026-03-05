# Setup do repositório (do zero)

## 1) Criar repo vazio
- Crie o repositório na sua Organization (público/privado).
- Faça clone local ou conecte no Codex Web.

## 2) Adicionar Secrets
Settings → Secrets and variables → Actions:
- `PROJECTS_SECRET` = token com permissão para:
  - comentar issues
  - dar push em branches
  - (opcional) abrir PR
- `OPENAI_API_KEY` = se quiser geração automática de docs (spec/plan/tasks)

## 3) Criar labels (manual rápido)
Crie labels:
- `swaif:init`
- `swaif:specify`
- `swaif:plan`
- `swaif:tasks`
- `swaif:implement`
- `swaif:verify`

## 4) Fluxo
1) Crie issue pelo template **SWAIF Feature**
2) Aplique `swaif:init`
3) Depois aplique as labels na ordem.
