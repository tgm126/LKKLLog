"""Stav období (den, měsíc) z pohledu uzávěrek. Let patří ke dni podle data vzletu v UTC."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from .models import Let, Uzaverka

OTEVRENO = "otevreno"
DEN = "den"
MESIC = "mesic"
_PORADI = {OTEVRENO: 0, DEN: 1, MESIC: 2}


def prisnejsi(*stavy: str) -> str:
    return max(stavy, key=_PORADI.__getitem__)


def den_letu(let: Let) -> date | None:
    return let.cas_vzletu.astimezone(UTC).date() if let.cas_vzletu else None


def zacatek_mesice(den: date) -> date:
    return den.replace(day=1)


def dalsi_mesic(mesic: date) -> date:
    return (mesic.replace(day=28) + timedelta(days=4)).replace(day=1)


def rozsah(od: date, do: date) -> tuple[datetime, datetime]:
    """Polootevřený interval [od 00:00, do+1 00:00) v UTC."""
    return (
        datetime.combine(od, time.min, tzinfo=UTC),
        datetime.combine(do + timedelta(days=1), time.min, tzinfo=UTC),
    )


@dataclass
class Uzavreno:
    """Uzavřené dny a měsíce (platné uzávěrky, bez znovu otevřených)."""

    dny: set[date] = field(default_factory=set)
    mesice: set[date] = field(default_factory=set)

    @classmethod
    def nacti(cls) -> Uzavreno:
        u = cls()
        for typ, obdobi in (
            Uzaverka.objects.filter(znovu_otevreno__isnull=True)
            .values_list("typ", "obdobi")
            .distinct()
        ):
            (u.dny if typ == Uzaverka.Typ.DEN else u.mesice).add(obdobi)
        return u

    def stav(self, den: date | None) -> str:
        if den is None:  # připravený let ještě nemá den
            return OTEVRENO
        if zacatek_mesice(den) in self.mesice:
            return MESIC
        if den in self.dny:
            return DEN
        return OTEVRENO
