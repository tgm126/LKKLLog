# TMG a SEP – kdo smí cvičit a zkoušet (podklad 7. 10. 2026)

Doplněk k `instruktori-a-examinatori.md` a `prezkouseni.md`. Jen podklad, nic se zatím
neimplementuje. **[ověřit]** = nepotvrzeno z úředního textu.

## 1. Situace v LKKL (podle správce)
- Na **TMG** létají piloti **obou** druhů: piloti kluzáků (SPL s rozšířením TMG) i piloti
  letounů (LAPL(A) / PPL(A) s třídou TMG).
- **TMG v klubu nevleká**; vlečná letadla jsou letouny (třída SEP).
- Kategorie letadla `LETOUN` v aplikaci odpovídá v klubu třídě **SEP (land)** – jednomotorový
  pístový letoun. Jiné třídy (vícemotorové, turbínové) klub nemá.

## 2. TMG – dva předpisy na jednom letadle

| | Pilot kluzáků (SPL + TMG) | Pilot letounů (LAPL(A) / PPL(A) + třída TMG) |
|---|---|---|
| Předpis | Part-SFCL | Part-FCL |
| Výcvik | **FI(S) s právy TMG** (SFCL.315(a)(4): 30 h PIC na TMG, kurz, předvedení výuky) | **FI(A) / CRI(A)**, který sám má třídu TMG (FCL.915(b)) |
| Zkouška | **FE(S) s právy TMG** (300 h, z toho 50 h výcviku na TMG; SFCL.415) | FE(A); kvalifikace třídy i CRE(A) |
| Rozlétanost | za 24 měsíců 12 h (6 h na TMG), 12 vzletů a přistání, **cvičný let ≥ 1 h s instruktorem**; jinak přezkoušení (SFCL.160(b)) | třída platí 24 měsíců; prodloužení zkušenostmi (12 h, 6 h PIC, 12 vzletů a přistání, **1 h s FI/CRI**) nebo přezkoušením FE/CRE (FCL.740.A) |
| Osnova v aplikaci | výcviková osnova kluzáků, cvičení II/10–12 | (osnova pro letouny zatím není) |

- **Napříč předpisy se necvičí:** FI(A) / CRI(A) nesmí cvičit pilota SPL na TMG – Part-SFCL to
  nepovoluje. **[ověřit, zda cvičný let pro rozlétanost SFCL.160(b) „s instruktorem“ smí
  udělat i FI(A) s TMG – text neříká „FI(S)“]**
- **Opačně jen u pilota:** držitel LAPL(A) / PPL(A) s třídou TMG má rozšíření SPL na TMG
  splněné (SFCL.150(c)) a rozlétanost TMG podle SFCL.160(b) neplní.

## 3. SEP – letouny (vlečné i ostatní)

| | LAPL(A) | PPL(A) – třída SEP |
|---|---|---|
| Výcvik | FI(A), CRI(A) SEP | FI(A), CRI(A) SEP |
| Zkouška k vydání | FE(A) s 500 h (jen LAPL) nebo s 1000 h | FE(A) s 1000 h; kvalifikace třídy i CRE(A) |
| Rozlétanost / platnost | v EU jen rozlétanost: za 24 měsíců 12 h, 12 vzletů a přistání, 1 h s instruktorem; jinak přezkoušení FE(A) (FCL.140.A) | třída platí 24 měsíců, **společné datum konce s TMG**; prodloužení jako u TMG (FCL.740.A) |
| Vlekání kluzáků | kvalifikace vlekání (FCL.805): **5 vleků za 24 měsíců**, jinak chybějící vleky s instruktorem nebo pod jeho dohledem | stejně |

- Instruktor smí cvičit jen to, co sám má: průkaz a třídu, pro kterou cvičí (FCL.915(b)).
  **CRI** se vydává **pro konkrétní třídu** (SEP, TMG); rozšíření na další třídu je samostatné.
  **CRE** zkouší jen třídy, pro které je sám instruktorem.
- Nálet na ultralehkých letounech (annexová letadla) jde podle ÚCL za podmínek započítat do
  prodloužení SEP (viz `licence-a-rozletanost.md`).

## 4. Co z toho plyne pro model (k projednání)

Právo pro **TMG** (a u CRI / CRE i pro **SEP**) je ve všech předpisech **samostatné
rozšíření** – nestačí „osoba má FI(S)“. Dnešní `lov_opravneni_kategorie` (FI_S → KLUZAK
i TMG…) by v nabídce na TMG ukázal každého FI(S).

- **A) Samostatné řádky** v `lov_opravneni`: FI_S_TMG, FE_S_TMG, FI_A_TMG, CRI_A_TMG,
  CRI_A_SEP… – jednoduché, ale řádků přibývá.
- **B) Kategorie ve vazbě osoby** (doporučeno):
  `lov_osoba_opravneni (osoba_id, opravneni_id, kategorie_id)`, PK přes všechny tři,
  složený FK `(opravneni_id, kategorie_id) → lov_opravneni_kategorie`. Číselník říká, pro
  které kategorie se oprávnění **může** vydat, vazba osoby, pro které ho **má**. Detail osoby
  už oprávnění zobrazuje po kategoriích – zaškrtávátko ve skupině TMG = oprávnění pro TMG.
  Převod: stávající oprávnění osob na všechny kategorie daného oprávnění, správce odškrtá.

Pro výběr osob není potřeba vědět, podle jakého průkazu pilot na TMG letí: nabídka
instruktorů na TMG = FI(S) s TMG ∪ FI(A) / CRI(A) s TMG (jen návrh, rozhoduje pilot). Druh
průkazu pilota bude potřeba až pro hlídání rozlétanosti.

## Zdroje
- Part-SFCL: [příloha III nařízení (EU) 2018/1976](https://www.legislation.gov.uk/eur/2018/1976/annex/III)
  (SFCL.150(c), SFCL.315(a)(4)); BGA [FI(S) TMG](https://members.gliding.co.uk/bga-training-organisation/fis-tmg/),
  [SPL TMG Extension](https://members.gliding.co.uk/bga-training-organisation/spl-tmg-extension/)
- Part-FCL (EASA Easy Access Rules): [FCL.1005.FE](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-aircrew-regulation-eu-no?page=40),
  [FCL.1005.CRE](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-aircrew-regulation-eu-no?page=42),
  [FCL.905.CRI](https://easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-aircrew-regulation-eu-no?page=32)
- ÚCL: [SEP/TMG prodloužení](https://www.caa.gov.cz/wp-content/uploads/2025/10/SEP-TMG-Administrativni-prodlouzeni.pdf),
  [annexová letadla a rozlétanost](https://www.caa.gov.cz/news/annexovana-letadla-a-plneni-pozadavku-na-rozletanost-prukazu-lapl-letoun-spl-a-lapl-kluzak-spl-a-lapl-balon-a-na-prodlouzeni-platnosti-kvalifikace-sep-land/)
