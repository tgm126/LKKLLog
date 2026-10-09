-- 038: Záznam odeslaných e-mailů (docs/modul-email.md, odsouhlaseno 9. 10. 2026). Aplikace
-- posílá z info@lkkl.cz jen odkaz pro nastavení hesla, ručně adminem u jedné osoby. Obsah se
-- neukládá – odkaz je tajný; záznam říká kdo, komu, na jakou adresu, kdy a s jakým výsledkem.
-- Provozní tabulka (bez auditu – sama je záznamem).

CREATE TABLE lkkl.email (
    id         bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kdy        timestamptz NOT NULL DEFAULT now(),
    druh       text        NOT NULL CHECK (druh IN ('ODKAZ_HESLO')),
    osoba_id   bigint      NOT NULL REFERENCES lkkl.lov_osoba,
    adresa     text        NOT NULL CHECK (btrim(adresa) <> ''),
    odeslal_id bigint      NOT NULL REFERENCES lkkl.lov_osoba,
    chyba      text        CHECK (btrim(chyba) <> '')
);

CREATE INDEX email_osoba ON lkkl.email (osoba_id, kdy);

COMMENT ON TABLE lkkl.email IS
    'Odeslané e-maily (bez obsahu): druh, komu (osoba a adresa v tu chvíli), kdo poslal, kdy; '
    'chyba prázdná = odesláno, jinak text chyby SMTP.';
COMMENT ON COLUMN lkkl.email.druh IS 'ODKAZ_HESLO = odkaz pro nastavení hesla.';
