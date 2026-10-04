"""Telefon osoby v mezinárodním tvaru (zobrazuje se jen na vyžádání, viz návrh)."""


def normalizovat(v) -> str:
    """„731 123 456“ → „+420731123456“, „00421…“ → „+421…“; prázdné → ""."""
    if isinstance(v, float) and v.is_integer():
        v = int(v)  # číslo zadané bez mezer (dřív z Excelu) může přijít jako float
    text = "" if v is None else str(v).strip()
    t = "".join(znak for znak in text if znak.isdigit() or znak == "+")
    if t.startswith("00"):
        t = "+" + t[2:]
    if t and not t.startswith("+") and len(t) == 9:
        t = "+420" + t
    return t
