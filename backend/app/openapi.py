"""Popis rozhraní (OpenAPI) jako JSON – zdroj typů pro frontend (code review 9. 10. 2026, A2):
`frontend/npm run api-typy` ho vygeneruje a převede na `frontend/src/api.gen.ts`.

    uv run python -m app.openapi [soubor]      bez souboru na standardní výstup (UTF-8)
"""

import json
import sys
from pathlib import Path

from .main import app


def popis() -> dict:
    """Popis rozhraní bez automatických názvů položek („Cas Vzletu“) – v typech frontendu by
    byly jen šum; popisy z dokumentačních řetězců modelů zůstávají."""
    o = app.openapi()
    for schema in o["components"]["schemas"].values():
        for polozka in schema.get("properties", {}).values():
            polozka.pop("title", None)
    return o


def main(argv: list[str]) -> None:
    text = json.dumps(popis(), ensure_ascii=False, indent=1)
    if argv:
        Path(argv[0]).parent.mkdir(parents=True, exist_ok=True)
        Path(argv[0]).write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))


if __name__ == "__main__":
    main(sys.argv[1:])
