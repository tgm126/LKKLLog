-- 004: osoby (členové i externí). Přihlašovací účet a role budou v samostatných tabulkách.

CREATE TABLE lkkl.osoba (
    id          bigint  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    jmeno       text    NOT NULL CHECK (btrim(jmeno) <> ''),
    prijmeni    text    NOT NULL CHECK (btrim(prijmeni) <> ''),
    email       text    CHECK (email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'),
    telefon     text    CHECK (telefon ~ '^\+[1-9][0-9]{7,14}$'),
    cislo_clena text    UNIQUE CHECK (cislo_clena ~ '^[0-9]+$'),
    clen        boolean NOT NULL DEFAULT true,
    aktivni     boolean NOT NULL DEFAULT true,
    CONSTRAINT cislo_jen_u_clena CHECK (cislo_clena IS NULL OR clen)
);
COMMENT ON TABLE lkkl.osoba IS 'Osoby: členové klubu i externí (piloti a instruktoři z jiných klubů). Hosté se neevidují, u letu jen počtem.';
COMMENT ON COLUMN lkkl.osoba.email IS 'Přihlášení a upozornění; jedinečný bez ohledu na velikost písmen.';
COMMENT ON COLUMN lkkl.osoba.telefon IS 'Mezinárodní tvar bez mezer, např. +420601234567.';
COMMENT ON COLUMN lkkl.osoba.cislo_clena IS 'Číslo člena klubu (text kvůli úvodním nulám); jen u členů.';
COMMENT ON COLUMN lkkl.osoba.clen IS 'Člen klubu (ne = externí osoba).';
COMMENT ON COLUMN lkkl.osoba.aktivni IS 'Ne = bývalý člen nebo už nelétá; osoba zůstává kvůli historii letů.';

CREATE UNIQUE INDEX osoba_email_jedinecny ON lkkl.osoba (lower(email));
