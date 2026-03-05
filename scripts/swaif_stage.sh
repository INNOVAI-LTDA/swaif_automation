#!/usr/bin/env bash
set -euo pipefail

issue_title="${1:-}"
stage="${2:-}"
feature_dir="${3:-}"
execution_type="${4:-MVP}"
issue_number="${5:-}"
mode="${6:-suggest}"

allowed_stages="init specify plan tasks implement verify"
if [[ -z "${issue_title}" || -z "${stage}" || -z "${feature_dir}" || -z "${issue_number}" ]]; then
  echo "Usage: $0 <issue_title> <stage> <feature_dir> [execution_type] <issue_number> [mode]" >&2
  exit 1
fi
if [[ ! " ${allowed_stages} " =~ " ${stage} " ]]; then
  echo "Invalid stage: ${stage}" >&2
  exit 1
fi

feature_slug="${feature_dir#specs/}"
branch="swaif/${feature_slug}"

log_dir=".swaif/logs"
mkdir -p "${log_dir}"
log_file="${log_dir}/stage-${stage}-issue-${issue_number}-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "${log_file}") 2>&1

echo "=== SWAIF Stage Runner ==="
echo "stage=${stage} mode=${mode} feature=${feature_slug} issue=${issue_number}"

# branch
git fetch --prune origin "+refs/heads/${branch}:refs/remotes/origin/${branch}" 2>/dev/null || true
if git show-ref --verify --quiet "refs/remotes/origin/${branch}"; then
  git checkout -B "${branch}" "refs/remotes/origin/${branch}"
else
  git checkout -B "${branch}"
fi

mkdir -p "${feature_dir}"

intake="${feature_dir}/intake.md"
spec="${feature_dir}/spec.md"
plan="${feature_dir}/plan.md"
tasks="${feature_dir}/tasks.md"
verify="${feature_dir}/verify.md"

write_if_missing() {
  local f="$1"; shift
  if [[ ! -f "${f}" ]]; then printf "%s\n" "$@" > "${f}"; fi
}

ensure_prerequisite() {
  local file_path="$1"
  local fallback_content="$2"

  if [[ -f "${file_path}" ]]; then
    return 0
  fi

  if [[ "${mode}" == "suggest" ]]; then
    echo "Pré-requisito ausente: ${file_path} (mode=suggest, criando placeholder)."
    write_if_missing "${file_path}" "${fallback_content}"
    return 0
  fi

  echo "Pré-requisito ausente: ${file_path}" >&2
  exit 1
}

# intake from issue body
if [[ ! -f "${intake}" ]]; then
  if [[ -z "${ISSUE_BODY:-}" ]]; then
    echo "ISSUE_BODY ausente" >&2
    exit 1
  fi
  {
    echo "<!-- AUTO-GENERATED from GitHub Issue #${issue_number} -->"
    echo "<!-- Title: ${issue_title} -->"
    echo
    printf "%s\n" "${ISSUE_BODY}"
  } > "${intake}"
fi

# collect attachments (best-effort)
if [[ "${stage}" == "init" || "${stage}" == "specify" ]]; then
  if [[ -n "${PROJECTS_TOKEN:-}" && -n "${GITHUB_REPOSITORY:-}" && "${PROJECTS_TOKEN}" != "placeholder-token" ]]; then
    python3 scripts/swaif_collect_attachments.py \
      --repo "${GITHUB_REPOSITORY}" \
      --issue "${issue_number}" \
      --token "${PROJECTS_TOKEN}" \
      --out "${feature_dir}/attachments" || true
  else
    echo "Sem token/repo válido; pulei coleta de anexos."
  fi
fi

append_context_to_prompt() {
  local prompt="$1"
  local source_file="$2"
  local label="$3"

  if [[ ! -f "${source_file}" ]]; then
    printf "%s" "${prompt}"
    return 0
  fi

  {
    printf "%s

" "${prompt}"
    printf "=== %s (%s) ===
" "${label}" "${source_file}"
    sed -n '1,400p' "${source_file}"
  }
}

ai_generate() {
  local target="$1"
  local prompt="$2"
  local source_file="${3:-}"
  local source_label="${4:-contexto}"
  local final_prompt="${prompt}"

  if [[ -n "${source_file}" ]]; then
    final_prompt="$(append_context_to_prompt "${prompt}" "${source_file}" "${source_label}")"
  fi

  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "OPENAI_API_KEY ausente; não gero ${target}."
    return 0
  fi
  python3 scripts/swaif_ai_generate.py "${target}" "${final_prompt}"
}

case "${stage}" in
  init)
    write_if_missing "${spec}" "# Spec — ${feature_slug}\n\n> Baseado em intake.md.\n"
    write_if_missing "${plan}" "# Plan — ${feature_slug}\n\n> Stack e arquitetura.\n"
    write_if_missing "${tasks}" "# Tasks — ${feature_slug}\n\n> Tarefas pequenas com critério de aceite.\n"
    ;;
  specify)
    ai_generate "${spec}" "Escreva a SPEC para '${feature_slug}' usando o intake abaixo. Foque no WHAT/WHY, sem stack. Inclua critérios de aceite e não-objetivos." "${intake}" "Intake"
    ;;
  plan)
    ensure_prerequisite "${spec}" "# Spec — ${feature_slug}\n\n> Placeholder criado automaticamente no stage plan (mode=suggest).\n"
    ai_generate "${plan}" "Crie um plano técnico para '${feature_slug}' com Python/FastAPI/Postgres, baseado na SPEC abaixo. Endpoints, modelos e testes." "${spec}" "SPEC"
    ;;
  tasks)
    ensure_prerequisite "${plan}" "# Plan — ${feature_slug}\n\n> Placeholder criado automaticamente no stage tasks (mode=suggest).\n"
    ai_generate "${tasks}" "Gere tasks pequenas (<=2h) com critério de aceite, baseado no plano abaixo." "${plan}" "Plano"
    ;;
  implement)
    write_if_missing "${feature_dir}/IMPLEMENT_NOTES.md" "# Implementação\n\nPlaceholder (seguro).\n"
    ;;
  verify)
    write_if_missing "${verify}" "# Verify\n\n- [ ] Rodar testes\n- [ ] Revisar diffs\n"
    ;;
esac

if ! git diff --quiet; then
  git add "${feature_dir}" scripts || true
  git commit -m "SWAIF(${stage}): ${feature_slug} (issue #${issue_number})" || true
fi
