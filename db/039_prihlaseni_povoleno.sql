-- 039: Účet – sloupec aktivni přejmenován na prihlaseni_povoleno (rozhodnuto 9. 10. 2026).
-- Název odpovídá významu (přístup do aplikace) a nemíchá se s aktivní osobou
-- (lov_osoba.platny – v aplikaci „Aktivní“). Přihlásit se smí jen ten, kdo má přihlášení
-- povolené a je platná (aktivní) osoba: v_ucet.smi_se_prihlasit (pohled přejmenování sleduje).
-- Audit: popisek a název akce i pro staré záznamy se sloupcem aktivni.

ALTER TABLE lkkl.ucet RENAME COLUMN aktivni TO prihlaseni_povoleno;

COMMENT ON COLUMN lkkl.ucet.prihlaseni_povoleno IS
    'Ano = smí se přihlásit (přístup do aplikace); ne = přístup vypnutý bez ztráty historie. '
    'Přihlásit se jde jen s platnou (aktivní) osobou – v_ucet.smi_se_prihlasit.';

UPDATE lkkl.lov_audit_popisek SET popisek = 'smí se přihlásit'
WHERE tabulka = 'ucet' AND sloupec = 'aktivni';
INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi, skryt_hodnotu)
VALUES ('ucet', 'prihlaseni_povoleno', 'smí se přihlásit', 10, false);

CREATE OR REPLACE FUNCTION lkkl.audit_akce(p_tabulka text, p_operace text, z jsonb)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $$
    SELECT CASE p_tabulka
        WHEN 'let' THEN CASE
            WHEN p_operace = 'INSERT' THEN 'Založení letu'
            WHEN p_operace = 'DELETE' THEN 'Smazání letu'
            WHEN z ? 'zruseni_duvod_id' AND z -> 'zruseni_duvod_id' -> 'na' <> 'null' THEN 'Zrušení'
            WHEN z ? 'zruseni_duvod_id' THEN 'Obnovení letu'
            WHEN z ? 'cas_pristani' AND z -> 'cas_pristani' -> 'z' = 'null' THEN 'Přistání'
            WHEN z ? 'cas_pristani' AND z -> 'cas_pristani' -> 'na' = 'null' THEN 'Zpět: přistání'
            WHEN z ? 'cas_vzletu' AND z -> 'cas_vzletu' -> 'z' = 'null' THEN 'Vzlet'
            WHEN z ? 'cas_vzletu' AND z -> 'cas_vzletu' -> 'na' = 'null' THEN 'Zpět: vzlet'
            ELSE 'Úprava' END
        WHEN 'posadka' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Posádka' WHEN 'DELETE' THEN 'Posádka: odebrání' ELSE 'Úprava posádky' END
        WHEN 'let_tg' THEN CASE p_operace
            WHEN 'INSERT' THEN 'T&G' WHEN 'DELETE' THEN 'Zpět: T&G' ELSE 'Úprava T&G' END
        WHEN 'lov_osoba' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení osoby' WHEN 'DELETE' THEN 'Smazání osoby' ELSE 'Úprava osoby' END
        WHEN 'lov_osoba_opravneni' THEN CASE
            WHEN p_operace = 'INSERT' THEN 'Přidání oprávnění'
            WHEN p_operace = 'DELETE' THEN 'Odebrání oprávnění'
            WHEN z -> 'omezene' -> 'na' = 'true' THEN 'Omezení oprávnění'
            WHEN z -> 'omezene' -> 'na' = 'false' THEN 'Zrušení omezení'
            ELSE 'Úprava oprávnění' END
        WHEN 'lov_osoba_opravneni_kategorie' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Oprávnění: přidání kategorie'
            WHEN 'DELETE' THEN 'Oprávnění: odebrání kategorie'
            ELSE 'Úprava oprávnění' END
        WHEN 'ucet' THEN CASE
            WHEN p_operace = 'INSERT' THEN 'Aktivace účtu'
            WHEN p_operace = 'DELETE' THEN 'Zrušení účtu'
            -- přihlášení povoleno / vypnuto (do 039 sloupec aktivni – staré záznamy auditu)
            WHEN coalesce(z -> 'prihlaseni_povoleno', z -> 'aktivni') -> 'na' = 'false' THEN 'Přihlášení vypnuto'
            WHEN coalesce(z -> 'prihlaseni_povoleno', z -> 'aktivni') -> 'na' = 'true' THEN 'Přihlášení povoleno'
            WHEN z ? 'heslo_zmeneno' THEN 'Změna hesla'
            WHEN z ? 'zablokovano_do' AND z -> 'zablokovano_do' -> 'na' <> 'null'
                THEN 'Zablokování po neúspěšných pokusech'
            WHEN z ? 'zablokovano_do' THEN 'Odblokování'
            WHEN z ? 'pozvanka_odeslana' THEN 'Pozvánka'
            ELSE 'Úprava účtu' END
        WHEN 'lov_letadlo' THEN CASE p_operace
            WHEN 'INSERT' THEN 'Založení letadla' WHEN 'DELETE' THEN 'Smazání letadla' ELSE 'Úprava letadla' END
        ELSE p_operace
    END
$$;
