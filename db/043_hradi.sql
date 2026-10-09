-- 043: „Platí“ → „Hradí“ (rozhodnuto 9. 10. 2026) – popisky historie letu; sloupce platce_id
-- a plati_aeroklub zůstávají (jen text pro člověka).
UPDATE lkkl.lov_audit_popisek SET popisek = 'hradí' WHERE tabulka = 'let' AND sloupec = 'platce_id';
UPDATE lkkl.lov_audit_popisek SET popisek = 'hradí aeroklub'
WHERE tabulka = 'let' AND sloupec = 'plati_aeroklub';
