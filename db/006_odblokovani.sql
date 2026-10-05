-- 006: právo odblokovat účet zablokovaný po neúspěšných pokusech o přihlášení.

ALTER TABLE lkkl.ucet ADD COLUMN smi_odblokovat boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.ucet.smi_odblokovat IS 'Výjimečné právo: smí odblokovat účet zablokovaný po neúspěšných pokusech.';

CREATE OR REPLACE VIEW lkkl.v_ucet AS
SELECT u.osoba_id,
       o.jmeno,
       o.prijmeni,
       o.email,
       u.heslo_hash IS NOT NULL       AS ma_heslo,
       u.aktivni AND o.aktivni        AS smi_se_prihlasit,
       u.admin,
       u.zalozen,
       u.pozvanka_odeslana,
       u.posledni_prihlaseni,
       u.zablokovano_do,
       u.smi_odblokovat
FROM lkkl.ucet u
JOIN lkkl.osoba o ON o.id = u.osoba_id;
