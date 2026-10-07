-- 028: letiště v rychlé volbě místa (průvodce, detail letu, letiště pro dnešek); ostatní
-- letiště se najdou přes „Hledat…“. Moje letiště (můj provoz, jinak domovské) se nabízí vždy.
ALTER TABLE lkkl.lov_letiste ADD COLUMN rychla_volba boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.lov_letiste.rychla_volba IS
    'Nabízí se v rychlé volbě místa; ostatní letiště jen přes Hledat… (mění správce v databázi).';

-- Počáteční nastavení podle zadání správce (7. 10. 2026): domovské a okolní letiště.
UPDATE lkkl.lov_letiste SET rychla_volba = true
WHERE domovske OR kod IN ('LKPC', 'LKSZ', 'LKCH', 'LKRK', 'LKHV', 'LKPS');

-- Nabídka letišť i s příznakem (nový sloupec na konci pohledu).
CREATE OR REPLACE VIEW lkkl.v_lov_letiste AS
SELECT id, kod, nazev, poradi, domovske, zem_sirka, zem_delka, nadm_vyska_ft, rychla_volba
FROM lkkl.lov_letiste WHERE platny ORDER BY domovske DESC, poradi, nazev;
