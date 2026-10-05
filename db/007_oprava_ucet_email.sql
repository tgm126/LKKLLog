-- 007: trigger ucet_osoba_ma_email hlásil u neexistující osoby „nemá e-mail“;
-- neexistující osobu má odmítnout cizí klíč.

CREATE OR REPLACE FUNCTION lkkl.ucet_osoba_ma_email() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_email text;
BEGIN
    SELECT email INTO v_email FROM lkkl.osoba WHERE id = NEW.osoba_id;
    IF FOUND AND v_email IS NULL THEN
        RAISE EXCEPTION 'Účet může mít jen osoba s e-mailem (osoba %).', NEW.osoba_id;
    END IF;
    RETURN NEW;
END $$;
