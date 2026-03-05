#!/usr/bin/env python3
import json, os, sys, urllib.request, urllib.error

if len(sys.argv) < 3:
    print("Usage: swaif_ai_generate.py <target_file> <prompt>", file=sys.stderr)
    sys.exit(2)

target = sys.argv[1]
prompt = sys.argv[2]
api_key = os.environ.get("OPENAI_API_KEY", "").strip()
if not api_key:
    print("OPENAI_API_KEY not set", file=sys.stderr)
    sys.exit(1)

model = os.environ.get("SWAIF_MODEL", "gpt-5.2")
payload = {
  "model": model,
  "messages": [
    {"role":"system","content":"Você é um engenheiro de software sênior. Gere documentos claros e rastreáveis. Não invente requisitos; registre assunções."},
    {"role":"user","content": prompt}
  ]
}

req = urllib.request.Request(
    "https://api.openai.com/v1/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
except urllib.error.HTTPError as e:
    print("HTTPError:", e.read().decode("utf-8", "ignore"), file=sys.stderr)
    raise

text = data["choices"][0]["message"]["content"].rstrip() + "\n"
with open(target, "w", encoding="utf-8") as f:
    f.write(text)
print(f"Wrote: {target}")
