-- 030: Přihlášení jen ke čtení (sdílený počítač v klubovně) – vlastnost relace (zařízení),
-- ne účtu. Server v takové relaci odmítne každý zápis a práva se neuplatní
-- (docs/modul-desktop.md 6.1, docs/modul-prihlasovani.md 4.2). Stávající relace zůstávají
-- plné. Relace audit nemají.
ALTER TABLE lkkl.relace ADD COLUMN jen_cteni boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN lkkl.relace.jen_cteni IS
    'Přihlášeno jen ke čtení (sdílený počítač): server odmítne zápisy, práva se neuplatní.';
