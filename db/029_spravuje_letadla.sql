-- 029: právo „spravuje letadla“ (docs/modul-letadla.md) – záložka Letadla, zatím jen přepínač
-- mimo provoz. Přiděluje admin; admin má všechna práva automaticky (hlídá server).

ALTER TABLE lkkl.ucet ADD COLUMN spravuje_letadla boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.ucet.spravuje_letadla IS 'Smí spravovat letadla (mimo provoz); admin smí vždy.';

INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi) VALUES
    ('ucet', 'spravuje_letadla', 'spravuje letadla', 36);

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
       u.spravuje_osoby,
       u.spravuje_letadla
FROM lkkl.ucet u
JOIN lkkl.lov_osoba o ON o.id = u.osoba_id;
