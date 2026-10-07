-- 023: právo „spravuje osoby“ (docs/modul-osoby.md) – seznam a úpravy osob, jejich oprávnění
-- a účtů (bez přidělování práv). Admin má všechna práva automaticky (hlídá server).

ALTER TABLE lkkl.ucet ADD COLUMN spravuje_osoby boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.ucet.spravuje_osoby IS 'Smí spravovat osoby (údaje, oprávnění, účty); admin smí vždy.';

INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi) VALUES
    ('ucet', 'spravuje_osoby', 'spravuje osoby', 35);

CREATE OR REPLACE VIEW lkkl.v_ucet AS
SELECT u.osoba_id,
       o.jmeno,
       o.prijmeni,
       o.email,
       u.heslo_hash IS NOT NULL AS ma_heslo,
       u.aktivni AND o.aktivni AS smi_se_prihlasit,
       u.admin,
       u.zalozen,
       u.pozvanka_odeslana,
       u.posledni_prihlaseni,
       u.zablokovano_do,
       u.smi_odblokovat,
       u.spravuje_osoby
FROM lkkl.ucet u
JOIN lkkl.lov_osoba o ON o.id = u.osoba_id;
