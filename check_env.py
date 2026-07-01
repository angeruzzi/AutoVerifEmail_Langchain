"""
Valida se todas as variáveis obrigatórias do .env estão preenchidas
antes de executar o agente.

Uso: python check_env.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REQUIRED = [
    "OPENAI_API_KEY",
    "EVOLUTION_API_KEY",
    "EVOLUTION_INSTANCE",
    "WHATSAPP_TARGET_NUMBER",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "FALLBACK_EMAIL_TO",
]

OPTIONAL_FILES = [
    ("GMAIL_CREDENTIALS_PATH", "credentials.json"),
]

ok = True

missing = [v for v in REQUIRED if not os.getenv(v)]
if missing:
    print("ERRO — variáveis obrigatórias ausentes no .env:")
    for v in missing:
        print(f"  - {v}")
    ok = False
else:
    print("OK — todas as variáveis obrigatórias estão preenchidas.")

for env_var, default in OPTIONAL_FILES:
    path = Path(os.getenv(env_var, default))
    if not path.exists():
        print(f"AVISO — {path} não encontrado (necessário para autenticação Gmail).")
        ok = False
    else:
        print(f"OK — {path} encontrado.")

sys.exit(0 if ok else 1)
