import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


p = Path(__file__).with_name(".env")
print("Exists:", p.exists())
print("Size:", p.stat().st_size if p.exists() else 0)

vals = dotenv_values(dotenv_path=p)
print("Direct read: GROQ_API_KEY =", _mask_secret(vals.get("GROQ_API_KEY")))

load_dotenv(dotenv_path=p, override=True)
print("Env after load: GROQ_API_KEY =", _mask_secret(os.environ.get("GROQ_API_KEY")))
