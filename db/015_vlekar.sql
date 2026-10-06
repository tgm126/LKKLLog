-- 015: příznak vlekaře u osoby – průvodce novým letem nabízí za vlekaře osoby s příznakem.
-- Až budou doklady osob (kvalifikace vlekání), rozhodne se, zda příznak odvodit, nebo nechat
-- jako klubové oprávnění.

ALTER TABLE lkkl.osoba ADD COLUMN vlekar boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.osoba.vlekar IS 'Smí vlekat kluzáky (nabízí se jako vlekař).';

INSERT INTO lkkl.audit_popisek (tabulka, sloupec, popisek, poradi) VALUES
    ('osoba', 'vlekar', 'vlekař', 65);
