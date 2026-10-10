-- 047: export záznamů o letech – PDF e-mailem adminům (docs/modul-export.md).
--   ucet.smi_exportovat – právo nechat si poslat export (admin smí vždy)
--   email: druh EXPORT_LETU s exportovaným obdobím (obsah ani PDF se neukládá)
--   v_souhrn_platce – souhrn ukončených letů podle plátce a letadla (podklad pro účetnictví)

ALTER TABLE lkkl.ucet ADD COLUMN smi_exportovat boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.ucet.smi_exportovat IS
    'Smí si nechat poslat export letů (PDF e-mailem adminům); admin smí vždy.';

INSERT INTO lkkl.lov_audit_popisek (tabulka, sloupec, popisek, poradi, skryt_hodnotu)
VALUES ('ucet', 'smi_exportovat', 'exportuje lety', 38, false);

CREATE OR REPLACE VIEW lkkl.v_ucet AS
SELECT u.osoba_id,
       o.jmeno,
       o.prijmeni,
       o.email,
       u.heslo_hash IS NOT NULL AS ma_heslo,
       u.prihlaseni_povoleno AND o.platny AS smi_se_prihlasit,
       u.admin,
       u.zalozen,
       u.pozvanka_odeslana,
       u.posledni_prihlaseni,
       u.zablokovano_do,
       u.smi_odblokovat,
       u.spravuje_osoby,
       u.spravuje_letadla,
       u.spravuje_vycvik,
       u.smi_exportovat
FROM lkkl.ucet u
JOIN lkkl.lov_osoba o ON o.id = u.osoba_id;

-- Záznam odeslaného exportu: komu (admin), kdo vyžádal, které dny [od, do).
ALTER TABLE lkkl.email
    DROP CONSTRAINT email_druh_check,
    ADD CONSTRAINT email_druh_check CHECK (druh IN ('ODKAZ_HESLO', 'EXPORT_LETU')),
    ADD COLUMN obdobi daterange,
    ADD CONSTRAINT email_obdobi CHECK ((druh = 'EXPORT_LETU') = (obdobi IS NOT NULL)),
    ADD CONSTRAINT email_obdobi_neprazdne CHECK (NOT isempty(obdobi));
COMMENT ON COLUMN lkkl.email.obdobi IS 'Exportované dny [od, do) – jen u druhu EXPORT_LETU.';

CREATE VIEW lkkl.v_souhrn_platce AS
SELECT den, platce_id, plati_aeroklub, platce_jmeno, platce_prijmeni,
       letadlo_id, rejstrik, je_vlecny,
       count(*)::integer AS lety,
       sum(pocet_pristani)::integer AS pristani,
       sum(doba_uctovana_min)::integer AS minut
FROM lkkl.v_let
WHERE stav = 'UKONCEN'
GROUP BY den, platce_id, plati_aeroklub, platce_jmeno, platce_prijmeni,
         letadlo_id, rejstrik, je_vlecny;

COMMENT ON VIEW lkkl.v_souhrn_platce IS
    'Souhrn podle plátce: ukončené lety po dni, plátci (osoba nebo aeroklub) a letadle '
    '(vlečná ve vleku zvlášť) – počet letů, přistání a účtovaných minut. Podklad exportu '
    'pro účetnictví (docs/modul-export.md).';
