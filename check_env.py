from pathlib import Path
from dotenv import dotenv_values, load_dotenv
import os

p = Path("D:/BikeMaster/.env")
print("Exists:", p.exists())
print("Size:", p.stat().st_size)

vals = dotenv_values(dotenv_path=p)
print("Direct read: GROQ_API_KEY =", repr(vals.get("GROQ_API_KEY")))

load_dotenv(dotenv_path=p, override=True)
print("Env after load: GROQ_API_KEY =", repr(os.environ.get("GROQ_API_KEY")))
