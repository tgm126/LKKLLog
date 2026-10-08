-- 034: Nastavení systému místo fáze provozu (rozhodnuto 8. 10. 2026). Hobby aplikace nahrazuje
-- sešit, data jdou dál do účetního programu – žádná automatika podle typu provozu: fáze
-- testování → pilot → ostrý provoz, jednorázové vyprázdnění provozních tabulek a hlídání
-- „zpět nejde“ se ruší. Zbývá jediný řádek nastavení; testovací provoz zatím řídí jen žlutý
-- pruh v aplikaci a přepíná se přímo v databázi:
--     UPDATE lkkl.nastaveni SET testovaci_provoz = false;
-- Zkušební lety se mažou po dnech: CALL lkkl.smazat_lety_dne('RRRR-MM-DD'); (033) – DELETE
-- vybraných řádků se zápisem do auditu. Celou tabulku letů a audit dál nejde vyprázdnit
-- příkazem TRUNCATE (obešel by audit) – výjimka pro zahájení ostrého provozu se ruší.

CREATE TABLE lkkl.nastaveni (
    jediny           boolean PRIMARY KEY DEFAULT true CHECK (jediny),
    testovaci_provoz boolean NOT NULL DEFAULT true
);
COMMENT ON TABLE lkkl.nastaveni IS
    'Nastavení systému (jediný řádek, sloupec = jedno nastavení; nové přidá migrace).';
COMMENT ON COLUMN lkkl.nastaveni.testovaci_provoz IS
    'Ano = aplikace ukazuje žlutý pruh TESTOVACÍ PROVOZ. Nic jiného neřídí.';

INSERT INTO lkkl.nastaveni (testovaci_provoz)
SELECT faze <> 'ostry' FROM lkkl.provoz;

DROP FUNCTION lkkl.zahajit_ostry_provoz();
DROP VIEW lkkl.v_provozni_tabulky;
DROP TABLE lkkl.provoz;
DROP FUNCTION lkkl.provoz_zmena();

CREATE OR REPLACE FUNCTION lkkl.nevyprazdnovat() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Tabulka % se nevyprazdňuje.', TG_TABLE_NAME;
END $$;
