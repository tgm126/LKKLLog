"""Převod licencí, medicalu a tabulky oprávnění na průkazy osob podle číselníků.

- licence a kvalifikace → průkaz osoby s kvalifikacemi (stejné systémové kódy),
- medical (třída 1, 2, LAPL) → průkaz Medical,
- oprávnění žák → výcvik; instruktor/examinátor → osvědčení instruktora / pověření
  examinátora; vlekař → kvalifikace „vlekání“ u PPL(A)/LAPL(A),
- pilot/instruktor/… v kategorii → přeškolení na všechny typy letadel té kategorie
  (aby nabídky v průvodci fungovaly hned; upraví se na kartě osoby).
"""

from django.db import migrations

VYCVIK = {"kluzak": "spl", "motor": "ppl_a", "tmg": "spl", "ul": "ull"}
INSTRUKTOR = {"kluzak": "fi_s", "motor": "fi_a", "tmg": "fi_a", "ul": "fi_ull"}
EXAMINATOR = {"kluzak": "fe_s", "motor": "fe_a", "tmg": "fe_a", "ul": "inspektor_laa"}
MEDICAL = {"1": "t1", "2": "t2", "lapl": "lapl"}


def prevest(apps, schema_editor):
    Licence = apps.get_model("osoby", "Licence")
    Medical = apps.get_model("osoby", "Medical")
    Opravneni = apps.get_model("osoby", "Opravneni")
    PrukazOsoby = apps.get_model("osoby", "PrukazOsoby")
    KvalifikaceOsoby = apps.get_model("osoby", "KvalifikaceOsoby")
    Vycvik = apps.get_model("osoby", "Vycvik")
    Preskoleni = apps.get_model("osoby", "Preskoleni")
    DruhPrukazu = apps.get_model("ciselniky", "DruhPrukazu")
    KvalifikacePrukazu = apps.get_model("ciselniky", "KvalifikacePrukazu")
    TypLetadla = apps.get_model("ciselniky", "TypLetadla")

    druhy = {d.kod: d for d in DruhPrukazu.objects.exclude(kod=None)}
    kvalifikace = {(k.druh.kod, k.kod): k for k in KvalifikacePrukazu.objects.select_related("druh")}

    def prukaz(osoba_id, kod, **kw):
        return PrukazOsoby.objects.get_or_create(osoba_id=osoba_id, druh=druhy[kod], defaults=kw)[0]

    def pridat(p, kod_druhu, kod_kvalifikace, platnost=None):
        kv = kvalifikace.get((kod_druhu, kod_kvalifikace))
        if kv:
            KvalifikaceOsoby.objects.get_or_create(
                prukaz=p, kvalifikace=kv, defaults={"platnost_do": platnost}
            )

    for lic in Licence.objects.all():
        if lic.typ not in druhy:
            continue
        p = prukaz(lic.osoba_id, lic.typ, cislo=lic.cislo, poznamka=lic.poznamka)
        for kv in lic.kvalifikace.all():
            pridat(p, lic.typ, kv.druh, kv.platnost_do)

    for m in Medical.objects.all():
        pridat(prukaz(m.osoba_id, "medical"), "medical", MEDICAL.get(m.trida), m.platnost_do)

    for o in Opravneni.objects.all():
        if o.uroven == "zak":
            if not Vycvik.objects.filter(osoba_id=o.osoba_id, druh=druhy[VYCVIK[o.kategorie]]):
                Vycvik.objects.create(osoba_id=o.osoba_id, druh=druhy[VYCVIK[o.kategorie]])
            continue
        if o.uroven in ("instruktor", "examinator"):
            pridat(prukaz(o.osoba_id, "instruktor"), "instruktor", INSTRUKTOR[o.kategorie])
        if o.uroven == "examinator":
            pridat(prukaz(o.osoba_id, "examinator"), "examinator", EXAMINATOR[o.kategorie])
        if o.uroven == "vlekar":
            for kod in ("ppl_a", "lapl_a"):
                p = PrukazOsoby.objects.filter(osoba_id=o.osoba_id, druh=druhy[kod]).first()
                if p:
                    pridat(p, kod, "vlekani")
                    break
        for typ in TypLetadla.objects.filter(kategorie=o.kategorie):
            Preskoleni.objects.get_or_create(osoba_id=o.osoba_id, typ=typ)


class Migration(migrations.Migration):
    dependencies = [
        ("osoby", "0010_doklady_z_ciselniku"),
        ("ciselniky", "0002_vychozi_hodnoty"),
        ("lety", "0011_typy_z_letadel"),
    ]

    operations = [migrations.RunPython(prevest, migrations.RunPython.noop)]
