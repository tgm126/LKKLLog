-- 049: Způsob vzletu kluzáku – aerovlek na prvním místě a výchozí, naviják druhý
-- (rozhodnuto 13. 10. 2026). Nabídka v aplikaci bere pořadí z v_lov_zpusob_vzletu; výchozí
-- volbu (bez dnešního vzletu kluzáku) určuje aplikace (frontend/src/lety/novyLet.tsx).
-- Způsob vzletu je řídicí číselník (program podle kódu uplatňuje pravidla) – pořadí patří
-- do skriptu struktury.
UPDATE lkkl.lov_zpusob_vzletu SET poradi = 20 WHERE kod = 'VLEK';
UPDATE lkkl.lov_zpusob_vzletu SET poradi = 30 WHERE kod = 'NAVIJAK';
