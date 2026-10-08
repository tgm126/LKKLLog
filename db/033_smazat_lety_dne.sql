-- 033: Admin smaže všechny lety jednoho dne přímo v databázi (zadání 8. 10. 2026) – např.
-- zkušební nebo omylem zadaný den. Jinak platí dál „let se nemaže, jen se zruší s důvodem“
-- (let_nemazat); výjimku má jen tato procedura, stejně jako zahájení ostrého provozu
-- (příznak transakce přes set_config). Volání ve správci databází:
--     CALL lkkl.smazat_lety_dne('2026-10-08');
-- Den letu jako v v_let: datum vzletu, u nevzlétnutého letu datum založení (UTC). Smaže lety
-- ve všech stavech (i ve vzduchu a naplánované), jejich posádku a T&G; u vleku vždy celou
-- dvojici. Audit zůstává – smazání v něm je („Smazání letu“ se starými hodnotami).

CREATE OR REPLACE FUNCTION lkkl.let_nemazat() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF current_setting('lkkl.mazani_letu_dne', true) IS DISTINCT FROM 'ano' THEN
        RAISE EXCEPTION 'Let se nemaže, jen se zruší s důvodem (celý den smaže admin: CALL lkkl.smazat_lety_dne(den)).';
    END IF;
    RETURN OLD;
END $$;

CREATE PROCEDURE lkkl.smazat_lety_dne(p_den date, INOUT smazano integer DEFAULT NULL)
LANGUAGE plpgsql AS $$
DECLARE
    v_lety bigint[];
BEGIN
    IF p_den IS NULL THEN
        RAISE EXCEPTION 'Zadejte den (RRRR-MM-DD).';
    END IF;
    -- lety dne a k nim druhá polovina vleku (vlečná i kluzák)
    SELECT array_agg(DISTINCT x.id) INTO v_lety
    FROM (
        SELECT l.id FROM lkkl.let l
        WHERE (coalesce(l.cas_vzletu, l.zalozeno) AT TIME ZONE 'UTC')::date = p_den
        UNION
        SELECT l.vlecny_let_id FROM lkkl.let l
        WHERE (coalesce(l.cas_vzletu, l.zalozeno) AT TIME ZONE 'UTC')::date = p_den
          AND l.vlecny_let_id IS NOT NULL
        UNION
        SELECT k.id FROM lkkl.let k JOIN lkkl.let v ON v.id = k.vlecny_let_id
        WHERE (coalesce(v.cas_vzletu, v.zalozeno) AT TIME ZONE 'UTC')::date = p_den
    ) x;
    smazano := coalesce(cardinality(v_lety), 0);
    IF smazano = 0 THEN
        RAISE NOTICE 'Dne % žádný let není.', p_den;
        RETURN;
    END IF;

    PERFORM set_config('lkkl.mazani_letu_dne', 'ano', true);
    -- kontrola letu po odebrání posádky a T&G až na konci transakce (let už nebude, kontrola
    -- ho přeskočí) – i když volající kontroly přepnul na okamžité
    SET CONSTRAINTS lkkl.posadka_kontrola, lkkl.let_tg_kontrola DEFERRED;
    DELETE FROM lkkl.let_tg WHERE let_id = ANY (v_lety);
    DELETE FROM lkkl.posadka WHERE let_id = ANY (v_lety);
    DELETE FROM lkkl.let WHERE id = ANY (v_lety);  -- kluzák i jeho vlečná jedním příkazem
    PERFORM set_config('lkkl.mazani_letu_dne', '', true);
    RAISE NOTICE 'Smazáno letů dne %: %.', p_den, smazano;
END $$;

COMMENT ON PROCEDURE lkkl.smazat_lety_dne(date, integer) IS
    'Admin: smaže všechny lety dne (datum vzletu, jinak založení; UTC) s posádkou a T&G, '
    'u vleku celou dvojici; vrátí počet. Audit zůstává. CALL lkkl.smazat_lety_dne(''RRRR-MM-DD'');';
