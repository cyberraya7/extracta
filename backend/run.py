import os
from pathlib import Path

from dotenv import load_dotenv
import uvicorn

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")


if __name__ == "__main__":
    reload_enabled = os.environ.get("UVICORN_RELOAD", "0") == "1"
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=reload_enabled,
        reload_excludes=["**/uploads/**", "**/.git/**"],
    )
