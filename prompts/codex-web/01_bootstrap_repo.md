# Codex Web — Bootstrap do repositório (prompt)

Tarefa:
1) Crie/atualize a estrutura do repositório para IssueOps + Spec pipeline, seguindo estes caminhos:
   - .github/workflows/issueops-swaif-factory.yml
   - .github/ISSUE_TEMPLATE/swaif_feature.yml
   - scripts/swaif_stage.sh
   - scripts/swaif_ai_generate.py
   - scripts/swaif_collect_attachments.py
   - docs/SETUP.md
2) Rode validações:
   - python -m py_compile scripts/swaif_stage.sh (não aplica; é bash)
   - python -m py_compile scripts/swaif_ai_generate.py
   - python -m py_compile scripts/swaif_collect_attachments.py
   - python scripts/swaif_collect_attachments.py --help
3) Se algo falhar, corrija o mínimo necessário.
4) Abra um PR com as alterações.

Restrições:
- Não invente features além do necessário.
- Mantenha os scripts sem dependências externas (apenas stdlib).
