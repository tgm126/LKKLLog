"""Základ modelů rozhraní (Pydantic). Dokumentační řetězce u položek (`\"\"\"…\"\"\"` pod
položkou) jdou do popisu rozhraní OpenAPI a odtud do typů frontendu (`frontend/src/api.gen.ts`,
code review 9. 10. 2026, A2) – komentář se píše jednou, u zdroje."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


class Polozka(Model):
    """Položka jednoduchého číselníku z pohledu v_lov_* (CLAUDE.md 10)."""

    id: int
    kod: str
    nazev: str


class Zmena(Model):
    """Záznam historie z auditu (v_historie_letu, v_audit)."""

    kdy: datetime
    kdo: str
    akce: str
    popis: str | None


Stav = Literal["NAPLANOVAN", "VE_VZDUCHU", "UKONCEN", "ZRUSEN"]
"""Stav letu (v_let, db/009)."""
DruhProvozu = Literal["PLACHTARSKY", "MOTOROVY"]
"""Plachtařský (kluzák a vlečný let) nebo motorový provoz – souhrny dne (db/035)."""
