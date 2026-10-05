-- 005: přihlašovací účty a relace (přihlášená zařízení).
-- Účet = osoba aktivovaná v aplikaci (1:0..1). Přihlašuje se e-mailem z osoby a heslem.
-- Výjimečná práva jsou logické příznaky na účtu; co smí každý přihlášený, příznak nemá.

CREATE TABLE lkkl.ucet (
    osoba_id            bigint      PRIMARY KEY REFERENCES lkkl.osoba,
    heslo_hash          text,
    aktivni             boolean     NOT NULL DEFAULT true,
    admin               boolean     NOT NULL DEFAULT false,
    zalozen             timestamptz NOT NULL DEFAULT now(),
    pozvanka_odeslana   timestamptz,
    heslo_zmeneno       timestamptz,
    posledni_prihlaseni timestamptz,
    neuspesne_pokusy    smallint    NOT NULL DEFAULT 0 CHECK (neuspesne_pokusy >= 0),
    zablokovano_do      timestamptz
);
COMMENT ON TABLE lkkl.ucet IS 'Přihlašovací účet osoby; existence účtu = osoba aktivovaná v aplikaci.';
COMMENT ON COLUMN lkkl.ucet.heslo_hash IS 'Otisk hesla (argon2id, počítá aplikace); prázdné = heslo ještě nenastavené.';
COMMENT ON COLUMN lkkl.ucet.aktivni IS 'Ne = účet zablokovaný (bez ztráty historie).';
COMMENT ON COLUMN lkkl.ucet.admin IS 'Výjimečné právo: smí všechno.';
COMMENT ON COLUMN lkkl.ucet.heslo_zmeneno IS 'Po změně hesla přestanou platit dříve vydané odkazy pro nastavení hesla.';
COMMENT ON COLUMN lkkl.ucet.neuspesne_pokusy IS 'Neúspěšná přihlášení od posledního úspěšného (ochrana proti hádání hesla).';
COMMENT ON COLUMN lkkl.ucet.zablokovano_do IS 'Dočasné zablokování po příliš mnoha neúspěšných pokusech.';

CREATE TABLE lkkl.relace (
    id                text        PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
    osoba_id          bigint      NOT NULL REFERENCES lkkl.ucet,
    puvodni_osoba_id  bigint      REFERENCES lkkl.ucet,
    vytvorena         timestamptz NOT NULL DEFAULT now(),
    posledni_aktivita timestamptz NOT NULL DEFAULT now(),
    plati_do          timestamptz NOT NULL,
    zarizeni          text,
    CONSTRAINT plati_po_vytvoreni CHECK (plati_do > vytvorena),
    CONSTRAINT jako_nekdo_jiny CHECK (puvodni_osoba_id <> osoba_id)
);
COMMENT ON TABLE lkkl.relace IS 'Přihlášená zařízení. Platí 30 dní od poslední aktivity.';
COMMENT ON COLUMN lkkl.relace.id IS 'SHA-256 (hex) náhodného klíče z cookie; samotný klíč se neukládá.';
COMMENT ON COLUMN lkkl.relace.osoba_id IS 'Za koho relace jedná.';
COMMENT ON COLUMN lkkl.relace.puvodni_osoba_id IS 'Admin, který se přihlásil jako jiná osoba („přihlásit se jako“); jinak prázdné.';
COMMENT ON COLUMN lkkl.relace.zarizeni IS 'Popis zařízení (prohlížeč, systém) pro přehled přihlášení.';

CREATE INDEX relace_osoba ON lkkl.relace (osoba_id);

-- Účet může mít jen osoba s e-mailem (e-mail je přihlašovací údaj).
CREATE FUNCTION lkkl.ucet_osoba_ma_email() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT email FROM lkkl.osoba WHERE id = NEW.osoba_id) IS NULL THEN
        RAISE EXCEPTION 'Účet může mít jen osoba s e-mailem (osoba %).', NEW.osoba_id;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER ucet_osoba_ma_email
    BEFORE INSERT OR UPDATE OF osoba_id ON lkkl.ucet
    FOR EACH ROW EXECUTE FUNCTION lkkl.ucet_osoba_ma_email();

-- Osobě s účtem nejde e-mail smazat.
CREATE FUNCTION lkkl.osoba_email_u_uctu() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.email IS NULL AND EXISTS (SELECT 1 FROM lkkl.ucet WHERE osoba_id = NEW.id) THEN
        RAISE EXCEPTION 'Osoba % má účet, e-mail nejde smazat.', NEW.id;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER osoba_email_u_uctu
    BEFORE UPDATE OF email ON lkkl.osoba
    FOR EACH ROW EXECUTE FUNCTION lkkl.osoba_email_u_uctu();

-- Účty s údaji osoby; přihlásit se smí jen aktivní účet aktivní osoby.
CREATE VIEW lkkl.v_ucet AS
SELECT u.osoba_id,
       o.jmeno,
       o.prijmeni,
       o.email,
       u.heslo_hash IS NOT NULL       AS ma_heslo,
       u.aktivni AND o.aktivni        AS smi_se_prihlasit,
       u.admin,
       u.zalozen,
       u.pozvanka_odeslana,
       u.posledni_prihlaseni,
       u.zablokovano_do
FROM lkkl.ucet u
JOIN lkkl.osoba o ON o.id = u.osoba_id;
COMMENT ON VIEW lkkl.v_ucet IS 'Účty s údaji osoby (bez otisku hesla).';
