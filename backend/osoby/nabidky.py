"""Kdo se hodí do které role v posádce – podle průkazů, výcviku a přeškolení.

Pro nabídky v průvodci letem (frontend posadka.ts). Nic neblokuje, jen řadí výběr.
"""

from django.db.models import Prefetch, QuerySet

from ciselniky.models import SkupinaPrukazu

from .models import DruhKvalifikace, PrukazOsoby, Vycvik


def _kategorie(kvalifikace) -> set[str]:
    return set().union(*(set(k.kvalifikace.kategorie) for k in kvalifikace))


def pro_nabidky(osoby: QuerySet) -> list[dict]:
    osoby = osoby.prefetch_related(
        Prefetch(
            "prukazy",
            queryset=PrukazOsoby.objects.select_related("druh").prefetch_related(
                "kvalifikace__kvalifikace"
            ),
        ),
        Prefetch(
            "vycviky", queryset=Vycvik.objects.filter(ukoncen__isnull=True).select_related("druh")
        ),
        "preskoleni",
    )
    vysledek = []
    for o in osoby:
        pilot, vlekar, instruktor, dozor, examinator = set(), set(), set(), set(), set()
        for p in o.prukazy.all():
            kvalifikace = list(p.kvalifikace.all())
            if p.druh.skupina == SkupinaPrukazu.PILOTNI:
                vleky = [k for k in kvalifikace if k.druh == DruhKvalifikace.VLEKANI]
                ostatni = [k for k in kvalifikace if k.druh != DruhKvalifikace.VLEKANI]
                # Kategorie podle tříd a způsobů vzletu, jinak podle průkazu.
                pilot |= _kategorie(ostatni) or set(p.druh.kategorie)
                vlekar |= _kategorie(vleky)
            elif p.druh.skupina == SkupinaPrukazu.INSTRUKTOR:
                instruktor |= _kategorie(kvalifikace)
                # Omezený instruktor učí pod dohledem a nesmí povolit sólo (SFCL.350).
                dozor |= _kategorie(
                    k for k in kvalifikace if k.druh != DruhKvalifikace.FI_S_OMEZENY
                )
            elif p.druh.skupina == SkupinaPrukazu.EXAMINATOR:
                examinator |= _kategorie(kvalifikace)
        vysledek.append(
            {
                "id": o.pk,
                "jmeno": o.jmeno,
                "prijmeni": o.prijmeni,
                "externi": o.externi,
                "pilot": sorted(pilot),
                "vlekar": sorted(vlekar),
                "instruktor": sorted(instruktor),
                "dozor": sorted(dozor),
                "examinator": sorted(examinator),
                "zak": sorted(set().union(*(set(v.druh.kategorie) for v in o.vycviky.all()))),
                "typy": [p.typ_id for p in o.preskoleni.all()],
            }
        )
    return vysledek
