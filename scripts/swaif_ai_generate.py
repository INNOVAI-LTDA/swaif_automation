#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request


def _build_payload(model: str, prompt: str) -> dict:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Você é um engenheiro de software sênior. Gere documentos claros e rastreáveis. Não invente requisitos; registre assunções.",
            },
            {"role": "user", "content": prompt},
        ],
    }


def generate(target: str, prompt: str, api_key: str, model: str, urlopen=urllib.request.urlopen) -> None:
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(_build_payload(model, prompt)).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=120) as resp:
            status = getattr(resp, "status", None)
            if status is None:
                status = resp.getcode()
            if status != 200:
                raise RuntimeError(f"OpenAI API returned unexpected status code: {status}")
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:200]
        raise RuntimeError(f"OpenAI API returned HTTP {e.code}: {body}") from e

    text = data["choices"][0]["message"]["content"].rstrip() + "\n"
    with open(target, "w", encoding="utf-8") as f:
        f.write(text)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: swaif_ai_generate.py <target_file> <prompt>", file=sys.stderr)
        return 2

    target = argv[1]
    prompt = argv[2]
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY not set", file=sys.stderr)
        return 1

    model = os.environ.get("SWAIF_MODEL", "").strip() or "gpt-5.2"
    try:
        generate(target, prompt, api_key, model)
    except RuntimeError as e:
        print(f"[ERR] {e}", file=sys.stderr)
        return 1
    print(f"Wrote: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
