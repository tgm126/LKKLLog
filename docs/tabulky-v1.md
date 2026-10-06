# Inventura tabulek první verze

> **Smazáno 6. 10. 2026** na serveru i lokálně (zálohy v `C:\GIT\LKKLLog-zalohy`). Dokument
> zůstává jako podklad.

Stav k 5. 10. 2026 (verze v0.14.3, větev `v1`). Všechny tabulky jsou ve schématu `public`
databáze `lkkllog`. Výpis je z lokální vývojové databáze; struktura na serveru je stejná
(stejné migrace), **počty řádků se liší** (lokální jsou jen testovací data).

**Všechny tabulky jsou určené ke smazání** po spuštění nové verze. Data, která má nová verze
převzít, zadá uživatel znovu; případný převod se domluví zvlášť.

## Přehled

Sloupec *Slabiny* shrnuje, co v modelu nesedí na normální formy nebo co se neosvědčilo.

| Tabulka | Skupina | Účel | Slabiny |
|---|---|---|---|
| `auth_group`, `auth_group_permissions`, `auth_permission` | framework | skupiny a práva Djanga | nepoužité (role jsou sloupce osoby) |
| `django_admin_log` | framework | historie vestavěné administrace | vedle vlastního auditního logu |
| `django_content_type` | framework | katalog modelů Djanga | – |
| `django_migrations` | framework | provedené migrace | – |
| `django_session` | framework | přihlášení (relace) | – |
| `osoby_osoba_groups`, `osoby_osoba_user_permissions` | framework | vazby osoby na skupiny a práva | nepoužité |
| `ciselniky_typletadla` | číselník | typy letadel (Blaník, Cessna 172…) → kategorie | kategorie je text bez číselníku |
| `ciselniky_druhprukazu` | číselník | druhy průkazů (PPL(A), SPL, medical, radio…), skupina | **pole kategorií v jednom sloupci** (porušuje 1NF), skupina jako textový kód |
| `ciselniky_kvalifikaceprukazu` | číselník | kvalifikace pod druhem průkazu (SEP, TMG, FI(S), třída 2…), má platnost | **pole kategorií** (1NF) |
| `ciselniky_provozniopravneni` | číselník | navijákář, služba RADIO, vyhlídkové lety | – |
| `ciselniky_druhterminu` | číselník | druhy termínů letadel (ARC, prohlídky…) | – |
| `lety_letiste` | číselník | letiště (ICAO, domovské, terén) | patřilo do aplikace lety, ne do číselníků |
| `lety_osnova` | číselník | výcvikové osnovy pro kategorii | dtto |
| `lety_uloha` | číselník | úlohy osnovy, u kterých účelů se nabízí | **pole účelů** (1NF) |
| `lety_letadlo` | kmenová data | letadlo, stav provozního deníku při spuštění | **typ a kategorie zkopírované z typu** (3NF), odkaz na typ nepovinný |
| `lety_terminletadla` | kmenová data | termíny letadla (do data / do náletu) | – |
| `osoby_osoba` | kmenová data | osoba = uživatel (heslo, e-mail, telefon), příznaky | role jako logické sloupce (`role_*`) samy o sobě nevadí, ale byly u osoby místo u účtu a mísily se se sloupci frameworku (`is_staff`, `is_superuser`); **sloučená osoba a přihlašovací účet** |
| `osoby_prukazosoby` | doklady | průkaz osoby (druh, číslo) | – |
| `osoby_kvalifikaceosoby` | doklady | kvalifikace na průkazu s platností | – |
| `osoby_preskoleni` | doklady | přeškolení osoby na typ letadla | – |
| `osoby_vycvik` | doklady | výcvik žáka (na průkaz, zahájen, sólo, ukončen) | – |
| `osoby_osoba_provozni_opravneni` | doklady | vazba osoba ↔ provozní oprávnění | – |
| `lety_let` | provoz | let: stav, účel, způsob vzletu, časy, plátce, vlek, verze | **kódy (stav, účel, způsob vzletu, krátký let, důvod zrušení) jen jako text bez číselníku**; **pole časů T&G** (1NF); `soukrome` je kopie příznaku letadla v okamžiku letu (historie řešená kopií sloupce) |
| `lety_posadka` | provoz | členové posádky letu a jejich funkce | funkce jako textový kód |
| `lety_uzaverka` | provoz | denní a měsíční uzávěrky s verzemi | souhrn jako JSON (záměrně snímek) |
| `lety_upozorneni` | provoz | odeslaná upozornění na neukončené lety | příjemci jako JSON |
| `lety_auditlog` | provoz | auditní log (kdo, kdy, co, změny) | obecný odkaz `objekt` + `objekt_id` bez cizího klíče; plní ho aplikace, ne trigger |
| `provoz_nastaveni` | provoz | nastavení (jeden řádek): režim e-mailů, hlídání, displej | **povolené adresy jako text se seznamem** (1NF), tabulka o jednom řádku |
| `provoz_pushodber` | provoz | odběry push notifikací zařízení | – |

## Další objekty v databázi

| Objekt | Druh | Účel |
|---|---|---|
| `lety_auditlog_jen_zapis` | trigger + funkce | do auditního logu jde jen přidávat (zákaz UPDATE a DELETE) |
| `btree_gist` | rozšíření | potřebné pro omezení EXCLUDE (jedno letadlo – jeden let v čase) |
| `plpgsql` | rozšíření | jazyk funkcí (standardní součást PostgreSQL) |

## Detail tabulek

Sloupce v pořadí z databáze; *NULL* = nepovinný, *identity* = automaticky číslovaný klíč.
Kontroly `poradi >= 0` a podobné kontroly nezáporných čísel jsou u číselníků a počtů všude.

### `auth_group` (0 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | integer | identity |
| name | character varying(150) |  |

Omezení a indexy:
- PK `auth_group_pkey`: `PRIMARY KEY (id)`
- UNIQUE `auth_group_name_key`: `UNIQUE (name)`
- INDEX `auth_group_name_a6ea08ec_like`: `btree (name varchar_pattern_ops)`

### `auth_group_permissions` (0 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| group_id | integer |  |
| permission_id | integer |  |

Omezení a indexy:
- FK `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm`: `FOREIGN KEY (permission_id) REFERENCES auth_permission(id) DEFERRABLE INITIALLY DEFERRED`
- FK `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id`: `FOREIGN KEY (group_id) REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED`
- PK `auth_group_permissions_pkey`: `PRIMARY KEY (id)`
- UNIQUE `auth_group_permissions_group_id_permission_id_0cd325b0_uniq`: `UNIQUE (group_id, permission_id)`
- INDEX `auth_group_permissions_group_id_b120cbf9`: `btree (group_id)`
- INDEX `auth_group_permissions_permission_id_84c5c92e`: `btree (permission_id)`

### `auth_permission` (124 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | integer | identity |
| name | character varying(255) |  |
| content_type_id | integer |  |
| codename | character varying(100) |  |

Omezení a indexy:
- FK `auth_permission_content_type_id_2f476e4b_fk_django_co`: `FOREIGN KEY (content_type_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED`
- PK `auth_permission_pkey`: `PRIMARY KEY (id)`
- UNIQUE `auth_permission_content_type_id_codename_01ab375a_uniq`: `UNIQUE (content_type_id, codename)`
- INDEX `auth_permission_content_type_id_2f476e4b`: `btree (content_type_id)`

### `ciselniky_druhprukazu` (9 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| nazev | character varying(80) |  |
| kod | character varying(30) | NULL |
| aktivni | boolean |  |
| poradi | smallint |  |
| skupina | character varying(12) |  |
| kategorie | character varying(10)[] |  |

Omezení a indexy:
- CHECK `ciselniky_druhprukazu_poradi_check`: `CHECK ((poradi >= 0))`
- PK `ciselniky_druhprukazu_pkey`: `PRIMARY KEY (id)`
- UNIQUE `druh_prukazu_kod`: `UNIQUE (kod)`
- UNIQUE `druh_prukazu_unikatni`: `UNIQUE (nazev)`

### `ciselniky_druhterminu` (9 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| nazev | character varying(80) |  |
| kod | character varying(30) | NULL |
| aktivni | boolean |  |
| poradi | smallint |  |

Omezení a indexy:
- CHECK `ciselniky_druhterminu_poradi_check`: `CHECK ((poradi >= 0))`
- PK `ciselniky_druhterminu_pkey`: `PRIMARY KEY (id)`
- UNIQUE `druh_terminu_unikatni`: `UNIQUE (nazev)`

### `ciselniky_kvalifikaceprukazu` (35 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| nazev | character varying(80) |  |
| kod | character varying(30) | NULL |
| aktivni | boolean |  |
| poradi | smallint |  |
| ma_platnost | boolean |  |
| kategorie | character varying(10)[] |  |
| druh_id | bigint |  |

Omezení a indexy:
- CHECK `ciselniky_kvalifikaceprukazu_poradi_check`: `CHECK ((poradi >= 0))`
- FK `ciselniky_kvalifikac_druh_id_56c7d380_fk_ciselniky`: `FOREIGN KEY (druh_id) REFERENCES ciselniky_druhprukazu(id) DEFERRABLE INITIALLY DEFERRED`
- PK `ciselniky_kvalifikaceprukazu_pkey`: `PRIMARY KEY (id)`
- UNIQUE `kvalifikace_kod`: `UNIQUE (druh_id, kod)`
- UNIQUE `kvalifikace_unikatni`: `UNIQUE (druh_id, nazev)`
- INDEX `ciselniky_kvalifikaceprukazu_druh_id_56c7d380`: `btree (druh_id)`

### `ciselniky_provozniopravneni` (3 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| nazev | character varying(80) |  |
| kod | character varying(30) | NULL |
| aktivni | boolean |  |
| poradi | smallint |  |

Omezení a indexy:
- CHECK `ciselniky_provozniopravneni_poradi_check`: `CHECK ((poradi >= 0))`
- PK `ciselniky_provozniopravneni_pkey`: `PRIMARY KEY (id)`
- UNIQUE `provozni_unikatni`: `UNIQUE (nazev)`

### `ciselniky_typletadla` (10 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| nazev | character varying(80) |  |
| kod | character varying(30) | NULL |
| aktivni | boolean |  |
| poradi | smallint |  |
| kategorie | character varying(10) |  |

Omezení a indexy:
- CHECK `ciselniky_typletadla_poradi_check`: `CHECK ((poradi >= 0))`
- PK `ciselniky_typletadla_pkey`: `PRIMARY KEY (id)`
- UNIQUE `typ_letadla_unikatni`: `UNIQUE (nazev)`

### `django_admin_log` (0 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | integer | identity |
| action_time | timestamp with time zone |  |
| object_id | text | NULL |
| object_repr | character varying(200) |  |
| action_flag | smallint |  |
| change_message | text |  |
| content_type_id | integer | NULL |
| user_id | bigint |  |

Omezení a indexy:
- CHECK `django_admin_log_action_flag_check`: `CHECK ((action_flag >= 0))`
- FK `django_admin_log_content_type_id_c4bce8eb_fk_django_co`: `FOREIGN KEY (content_type_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED`
- FK `django_admin_log_user_id_c564eba6_fk_osoby_osoba_id`: `FOREIGN KEY (user_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- PK `django_admin_log_pkey`: `PRIMARY KEY (id)`
- INDEX `django_admin_log_content_type_id_c4bce8eb`: `btree (content_type_id)`
- INDEX `django_admin_log_user_id_c564eba6`: `btree (user_id)`

### `django_content_type` (31 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | integer | identity |
| app_label | character varying(100) |  |
| model | character varying(100) |  |

Omezení a indexy:
- PK `django_content_type_pkey`: `PRIMARY KEY (id)`
- UNIQUE `django_content_type_app_label_model_76bd3d3b_uniq`: `UNIQUE (app_label, model)`

### `django_migrations` (54 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| app | character varying(255) |  |
| name | character varying(255) |  |
| applied | timestamp with time zone |  |

Omezení a indexy:
- PK `django_migrations_pkey`: `PRIMARY KEY (id)`

### `django_session` (1 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| session_key | character varying(40) |  |
| session_data | text |  |
| expire_date | timestamp with time zone |  |

Omezení a indexy:
- PK `django_session_pkey`: `PRIMARY KEY (session_key)`
- INDEX `django_session_expire_date_a5c62663`: `btree (expire_date)`
- INDEX `django_session_session_key_c0390e0f_like`: `btree (session_key varchar_pattern_ops)`

### `lety_auditlog` (9 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| kdy | timestamp with time zone |  |
| akce | character varying(30) |  |
| objekt | character varying(30) |  |
| objekt_id | bigint |  |
| zmeny | jsonb |  |
| duvod | character varying(30) |  |
| poznamka | character varying(300) |  |
| kdo_id | bigint | NULL |

Omezení a indexy:
- FK `lety_auditlog_kdo_id_7ddaa9cd_fk_osoby_osoba_id`: `FOREIGN KEY (kdo_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- PK `lety_auditlog_pkey`: `PRIMARY KEY (id)`
- INDEX `lety_auditl_objekt_fff25b_idx`: `btree (objekt, objekt_id)`
- INDEX `lety_auditlog_kdo_id_7ddaa9cd`: `btree (kdo_id)`
- INDEX `lety_auditlog_kdy_f675acdb`: `btree (kdy)`

### `lety_let` (1 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| stav | character varying(12) |  |
| ucel | character varying(12) |  |
| zpusob_vzletu | character varying(10) |  |
| cas_vzletu | timestamp with time zone | NULL |
| cas_pristani | timestamp with time zone | NULL |
| doba_min | integer | NULL, generovaný |
| kratky_let | character varying(16) |  |
| pocet_tg | smallint |  |
| pocet_hostu | smallint |  |
| plati_aeroklub | boolean |  |
| soukrome | boolean |  |
| duvod_zruseni | character varying(20) |  |
| opraveno_po_uzaverce | boolean |  |
| zalozeno | timestamp with time zone |  |
| zmeneno | timestamp with time zone |  |
| verze | integer |  |
| platce_id | bigint | NULL |
| vlecny_let_id | bigint | NULL |
| zalozil_id | bigint |  |
| letadlo_id | bigint |  |
| misto_pristani_id | bigint | NULL |
| misto_vzletu_id | bigint |  |
| uloha_id | bigint | NULL |
| casy_tg | timestamp with time zone[] |  |
| pocet_pristani | integer | NULL, generovaný |

Omezení a indexy:
- CHECK `casy_tg_do_poctu`: `CHECK ((pocet_tg >= cardinality(casy_tg)))`
- CHECK `duvod_jen_u_zruseneho`: `CHECK ((((stav)::text = 'zrusen'::text) OR ((duvod_zruseni)::text = ''::text)))`
- CHECK `lety_let_pocet_hostu_check`: `CHECK ((pocet_hostu >= 0))`
- CHECK `lety_let_pocet_tg_check`: `CHECK ((pocet_tg >= 0))`
- CHECK `lety_let_verze_check`: `CHECK ((verze >= 0))`
- CHECK `prave_jeden_platce`: `CHECK ((((platce_id IS NULL) AND plati_aeroklub) OR ((platce_id IS NOT NULL) AND (NOT plati_aeroklub))))`
- CHECK `pristani_po_vzletu`: `CHECK (((cas_pristani IS NULL) OR ((cas_pristani >= cas_vzletu) AND (cas_vzletu IS NOT NULL))))`
- CHECK `zruseny_ma_duvod`: `CHECK (((NOT ((stav)::text = 'zrusen'::text)) OR (NOT ((duvod_zruseni)::text = ''::text))))`
- FK `lety_let_letadlo_id_dc3cb9fd_fk_lety_letadlo_id`: `FOREIGN KEY (letadlo_id) REFERENCES lety_letadlo(id) DEFERRABLE INITIALLY DEFERRED`
- FK `lety_let_misto_pristani_id_df89ac4b_fk_lety_letiste_id`: `FOREIGN KEY (misto_pristani_id) REFERENCES lety_letiste(id) DEFERRABLE INITIALLY DEFERRED`
- FK `lety_let_misto_vzletu_id_68cfef32_fk_lety_letiste_id`: `FOREIGN KEY (misto_vzletu_id) REFERENCES lety_letiste(id) DEFERRABLE INITIALLY DEFERRED`
- FK `lety_let_platce_id_74648708_fk_osoby_osoba_id`: `FOREIGN KEY (platce_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- FK `lety_let_uloha_id_82b449f6_fk_lety_uloha_id`: `FOREIGN KEY (uloha_id) REFERENCES lety_uloha(id) DEFERRABLE INITIALLY DEFERRED`
- FK `lety_let_vlecny_let_id_3aa000e1_fk_lety_let_id`: `FOREIGN KEY (vlecny_let_id) REFERENCES lety_let(id) DEFERRABLE INITIALLY DEFERRED`
- FK `lety_let_zalozil_id_f41d234a_fk_osoby_osoba_id`: `FOREIGN KEY (zalozil_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- PK `lety_let_pkey`: `PRIMARY KEY (id)`
- UNIQUE `lety_let_vlecny_let_id_key`: `UNIQUE (vlecny_let_id)`
- EXCLUDE `letadlo_bez_prekryvu`: `EXCLUDE USING gist (letadlo_id WITH =, tstzrange(cas_vzletu, cas_pristani) WITH &&) WHERE (((cas_vzletu IS NOT NULL) AND (NOT ((stav)::text = 'zrusen'::text))))`
- INDEX `lety_let_cas_vzl_251db2_idx`: `btree (cas_vzletu)`
- INDEX `lety_let_letadlo_id_dc3cb9fd`: `btree (letadlo_id)`
- INDEX `lety_let_misto_pristani_id_df89ac4b`: `btree (misto_pristani_id)`
- INDEX `lety_let_misto_vzletu_id_68cfef32`: `btree (misto_vzletu_id)`
- INDEX `lety_let_platce_id_74648708`: `btree (platce_id)`
- INDEX `lety_let_uloha_id_82b449f6`: `btree (uloha_id)`
- INDEX `lety_let_zalozil_id_f41d234a`: `btree (zalozil_id)`

### `lety_letadlo` (10 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| imatrikulace | character varying(10) |  |
| typ | character varying(60) |  |
| kategorie | character varying(10) |  |
| pocet_mist | smallint |  |
| max_doba_min | integer | NULL |
| soukrome | boolean |  |
| vlecne | boolean |  |
| aktivni | boolean |  |
| poradi | smallint |  |
| nalet_pocatek_min | integer |  |
| starty_pocatek | integer |  |
| stav_k | date | NULL |
| typ_letadla_id | bigint | NULL |

Omezení a indexy:
- CHECK `kluzak_bez_vleku_a_nadrzi`: `CHECK (((NOT ((kategorie)::text = 'kluzak'::text)) OR ((max_doba_min IS NULL) AND (NOT vlecne))))`
- CHECK `letadlo_pocet_mist`: `CHECK (((pocet_mist >= 1) AND (pocet_mist <= 4)))`
- CHECK `lety_letadlo_max_doba_min_check`: `CHECK ((max_doba_min >= 0))`
- CHECK `lety_letadlo_nalet_pocatek_min_check`: `CHECK ((nalet_pocatek_min >= 0))`
- CHECK `lety_letadlo_pocet_mist_check`: `CHECK ((pocet_mist >= 0))`
- CHECK `lety_letadlo_poradi_check`: `CHECK ((poradi >= 0))`
- CHECK `lety_letadlo_starty_pocatek_check`: `CHECK ((starty_pocatek >= 0))`
- FK `lety_letadlo_typ_letadla_id_35be411d_fk_ciselniky_typletadla_id`: `FOREIGN KEY (typ_letadla_id) REFERENCES ciselniky_typletadla(id) DEFERRABLE INITIALLY DEFERRED`
- PK `lety_letadlo_pkey`: `PRIMARY KEY (id)`
- UNIQUE `lety_letadlo_imatrikulace_key`: `UNIQUE (imatrikulace)`
- INDEX `lety_letadlo_imatrikulace_c892125d_like`: `btree (imatrikulace varchar_pattern_ops)`
- INDEX `lety_letadlo_typ_letadla_id_35be411d`: `btree (typ_letadla_id)`

### `lety_letiste` (8 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| icao | character varying(4) | NULL |
| nazev | character varying(80) |  |
| domovske | boolean |  |
| teren | boolean |  |
| aktivni | boolean |  |
| poradi | smallint |  |

Omezení a indexy:
- CHECK `lety_letiste_poradi_check`: `CHECK ((poradi >= 0))`
- PK `lety_letiste_pkey`: `PRIMARY KEY (id)`
- UNIQUE `lety_letiste_icao_key`: `UNIQUE (icao)`
- INDEX `jedno_domovske_letiste`: `btree (domovske) WHERE domovske`
- INDEX `lety_letiste_icao_c3a8d639_like`: `btree (icao varchar_pattern_ops)`

### `lety_osnova` (11 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| kategorie | character varying(10) |  |
| nazev | character varying(80) |  |
| aktivni | boolean |  |
| poradi | smallint |  |

Omezení a indexy:
- CHECK `lety_osnova_poradi_check`: `CHECK ((poradi >= 0))`
- PK `lety_osnova_pkey`: `PRIMARY KEY (id)`
- UNIQUE `osnova_unikatni`: `UNIQUE (kategorie, nazev)`

### `lety_posadka` (1 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| funkce | character varying(12) |  |
| let_id | bigint |  |
| osoba_id | bigint |  |

Omezení a indexy:
- FK `lety_posadka_let_id_88ddb70f_fk_lety_let_id`: `FOREIGN KEY (let_id) REFERENCES lety_let(id) DEFERRABLE INITIALLY DEFERRED`
- FK `lety_posadka_osoba_id_edb0768c_fk_osoby_osoba_id`: `FOREIGN KEY (osoba_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- PK `lety_posadka_pkey`: `PRIMARY KEY (id)`
- UNIQUE `osoba_jednou_na_letu`: `UNIQUE (let_id, osoba_id)`
- INDEX `jeden_pic_na_letu`: `btree (let_id) WHERE ((funkce)::text = 'pic'::text)`
- INDEX `lety_posadka_let_id_88ddb70f`: `btree (let_id)`
- INDEX `lety_posadka_osoba_id_edb0768c`: `btree (osoba_id)`

### `lety_terminletadla` (30 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| datum | date | NULL |
| pri_naletu_h | integer | NULL |
| poznamka | character varying(200) |  |
| letadlo_id | bigint |  |
| druh_id | bigint |  |

Omezení a indexy:
- CHECK `lety_terminletadla_pri_naletu_h_check`: `CHECK ((pri_naletu_h >= 0))`
- CHECK `termin_ma_datum_nebo_nalet`: `CHECK (((datum IS NOT NULL) OR (pri_naletu_h IS NOT NULL)))`
- FK `lety_terminletadla_druh_id_203621e5_fk_ciselniky_druhterminu_id`: `FOREIGN KEY (druh_id) REFERENCES ciselniky_druhterminu(id) DEFERRABLE INITIALLY DEFERRED`
- FK `lety_terminletadla_letadlo_id_8d5dfbb3_fk_lety_letadlo_id`: `FOREIGN KEY (letadlo_id) REFERENCES lety_letadlo(id) DEFERRABLE INITIALLY DEFERRED`
- PK `lety_terminletadla_pkey`: `PRIMARY KEY (id)`
- INDEX `lety_terminletadla_druh_id_203621e5`: `btree (druh_id)`
- INDEX `lety_terminletadla_letadlo_id_8d5dfbb3`: `btree (letadlo_id)`

### `lety_uloha` (28 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| kod | character varying(20) |  |
| nazev | character varying(120) |  |
| ucely | character varying(12)[] |  |
| aktivni | boolean |  |
| poradi | smallint |  |
| osnova_id | bigint |  |

Omezení a indexy:
- CHECK `lety_uloha_poradi_check`: `CHECK ((poradi >= 0))`
- FK `lety_uloha_osnova_id_adfedd9e_fk_lety_osnova_id`: `FOREIGN KEY (osnova_id) REFERENCES lety_osnova(id) DEFERRABLE INITIALLY DEFERRED`
- PK `lety_uloha_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uloha_unikatni_kod`: `UNIQUE (osnova_id, kod)`
- INDEX `lety_uloha_osnova_id_adfedd9e`: `btree (osnova_id)`

### `lety_upozorneni` (0 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| druh | character varying(12) |  |
| kdy | timestamp with time zone |  |
| prijemci | jsonb |  |
| let_id | bigint |  |

Omezení a indexy:
- FK `lety_upozorneni_let_id_39007786_fk_lety_let_id`: `FOREIGN KEY (let_id) REFERENCES lety_let(id) DEFERRABLE INITIALLY DEFERRED`
- PK `lety_upozorneni_pkey`: `PRIMARY KEY (id)`
- UNIQUE `upozorneni_jednou`: `UNIQUE (let_id, druh)`
- INDEX `lety_upozorneni_let_id_39007786`: `btree (let_id)`

### `lety_uzaverka` (0 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| typ | character varying(5) |  |
| obdobi | date |  |
| verze | smallint |  |
| kdy | timestamp with time zone |  |
| souhrn | jsonb |  |
| uzavrel_id | bigint | NULL |
| znovu_otevreno | timestamp with time zone | NULL |

Omezení a indexy:
- CHECK `lety_uzaverka_verze_check`: `CHECK ((verze >= 0))`
- FK `lety_uzaverka_uzavrel_id_66989aae_fk_osoby_osoba_id`: `FOREIGN KEY (uzavrel_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- PK `lety_uzaverka_pkey`: `PRIMARY KEY (id)`
- UNIQUE `uzaverka_verze`: `UNIQUE (typ, obdobi, verze)`
- INDEX `lety_uzaverka_uzavrel_id_66989aae`: `btree (uzavrel_id)`

### `osoby_kvalifikaceosoby` (55 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| platnost_do | date | NULL |
| kvalifikace_id | bigint |  |
| prukaz_id | bigint |  |

Omezení a indexy:
- FK `osoby_kvalifikaceoso_kvalifikace_id_b41866f3_fk_ciselniky`: `FOREIGN KEY (kvalifikace_id) REFERENCES ciselniky_kvalifikaceprukazu(id) DEFERRABLE INITIALLY DEFERRED`
- FK `osoby_kvalifikaceoso_prukaz_id_78461f55_fk_osoby_pru`: `FOREIGN KEY (prukaz_id) REFERENCES osoby_prukazosoby(id) DEFERRABLE INITIALLY DEFERRED`
- PK `osoby_kvalifikaceosoby_pkey`: `PRIMARY KEY (id)`
- UNIQUE `kvalifikace_osoby_jednou`: `UNIQUE (prukaz_id, kvalifikace_id)`
- INDEX `osoby_kvalifikaceosoby_kvalifikace_id_b41866f3`: `btree (kvalifikace_id)`
- INDEX `osoby_kvalifikaceosoby_prukaz_id_78461f55`: `btree (prukaz_id)`

### `osoby_osoba` (14 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| password | character varying(128) |  |
| last_login | timestamp with time zone | NULL |
| is_superuser | boolean |  |
| jmeno | character varying(60) |  |
| prijmeni | character varying(60) |  |
| email | character varying(254) | NULL |
| role_casomeric | boolean |  |
| role_ucetni | boolean |  |
| externi | boolean |  |
| is_active | boolean |  |
| is_staff | boolean |  |
| vytvoreno | timestamp with time zone |  |
| testovaci | boolean |  |
| telefon | character varying(16) |  |
| pozvanka_odeslana | timestamp with time zone | NULL |
| role_spravce | boolean |  |

Omezení a indexy:
- CHECK `externi_bez_emailu`: `CHECK (((NOT externi) OR (email IS NULL)))`
- PK `osoby_osoba_pkey`: `PRIMARY KEY (id)`
- UNIQUE `osoby_osoba_email_key`: `UNIQUE (email)`
- INDEX `osoby_osoba_email_a72df09a_like`: `btree (email varchar_pattern_ops)`

### `osoby_osoba_groups` (0 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| osoba_id | bigint |  |
| group_id | integer |  |

Omezení a indexy:
- FK `osoby_osoba_groups_group_id_d9333e41_fk_auth_group_id`: `FOREIGN KEY (group_id) REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED`
- FK `osoby_osoba_groups_osoba_id_217b4255_fk_osoby_osoba_id`: `FOREIGN KEY (osoba_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- PK `osoby_osoba_groups_pkey`: `PRIMARY KEY (id)`
- UNIQUE `osoby_osoba_groups_osoba_id_group_id_2244e000_uniq`: `UNIQUE (osoba_id, group_id)`
- INDEX `osoby_osoba_groups_group_id_d9333e41`: `btree (group_id)`
- INDEX `osoby_osoba_groups_osoba_id_217b4255`: `btree (osoba_id)`

### `osoby_osoba_provozni_opravneni` (0 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| osoba_id | bigint |  |
| provozniopravneni_id | bigint |  |

Omezení a indexy:
- FK `osoby_osoba_provozni_osoba_id_9ea7f442_fk_osoby_oso`: `FOREIGN KEY (osoba_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- FK `osoby_osoba_provozni_provozniopravneni_id_09ff510c_fk_ciselniky`: `FOREIGN KEY (provozniopravneni_id) REFERENCES ciselniky_provozniopravneni(id) DEFERRABLE INITIALLY DEFERRED`
- PK `osoby_osoba_provozni_opravneni_pkey`: `PRIMARY KEY (id)`
- UNIQUE `osoby_osoba_provozni_opr_osoba_id_provozniopravne_16ac7e8e_uniq`: `UNIQUE (osoba_id, provozniopravneni_id)`
- INDEX `osoby_osoba_provozni_opravneni_osoba_id_9ea7f442`: `btree (osoba_id)`
- INDEX `osoby_osoba_provozni_opravneni_provozniopravneni_id_09ff510c`: `btree (provozniopravneni_id)`

### `osoby_osoba_user_permissions` (0 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| osoba_id | bigint |  |
| permission_id | integer |  |

Omezení a indexy:
- FK `osoby_osoba_user_per_osoba_id_7e778f5b_fk_osoby_oso`: `FOREIGN KEY (osoba_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- FK `osoby_osoba_user_per_permission_id_0c828707_fk_auth_perm`: `FOREIGN KEY (permission_id) REFERENCES auth_permission(id) DEFERRABLE INITIALLY DEFERRED`
- PK `osoby_osoba_user_permissions_pkey`: `PRIMARY KEY (id)`
- UNIQUE `osoby_osoba_user_permiss_osoba_id_permission_id_b7e8afb1_uniq`: `UNIQUE (osoba_id, permission_id)`
- INDEX `osoby_osoba_user_permissions_osoba_id_7e778f5b`: `btree (osoba_id)`
- INDEX `osoby_osoba_user_permissions_permission_id_0c828707`: `btree (permission_id)`

### `osoby_preskoleni` (40 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| datum | date | NULL |
| osoba_id | bigint |  |
| typ_id | bigint |  |

Omezení a indexy:
- FK `osoby_preskoleni_osoba_id_14c07f8f_fk_osoby_osoba_id`: `FOREIGN KEY (osoba_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- FK `osoby_preskoleni_typ_id_f5305807_fk_ciselniky_typletadla_id`: `FOREIGN KEY (typ_id) REFERENCES ciselniky_typletadla(id) DEFERRABLE INITIALLY DEFERRED`
- PK `osoby_preskoleni_pkey`: `PRIMARY KEY (id)`
- UNIQUE `preskoleni_jednou`: `UNIQUE (osoba_id, typ_id)`
- INDEX `osoby_preskoleni_osoba_id_14c07f8f`: `btree (osoba_id)`
- INDEX `osoby_preskoleni_typ_id_f5305807`: `btree (typ_id)`

### `osoby_prukazosoby` (39 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| cislo | character varying(40) |  |
| poznamka | character varying(200) |  |
| zmeneno | timestamp with time zone |  |
| druh_id | bigint |  |
| osoba_id | bigint |  |

Omezení a indexy:
- FK `osoby_prukazosoby_druh_id_fd0d647a_fk_ciselniky_druhprukazu_id`: `FOREIGN KEY (druh_id) REFERENCES ciselniky_druhprukazu(id) DEFERRABLE INITIALLY DEFERRED`
- FK `osoby_prukazosoby_osoba_id_70a93994_fk_osoby_osoba_id`: `FOREIGN KEY (osoba_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- PK `osoby_prukazosoby_pkey`: `PRIMARY KEY (id)`
- UNIQUE `prukaz_osoby_jednou`: `UNIQUE (osoba_id, druh_id)`
- INDEX `osoby_prukazosoby_druh_id_fd0d647a`: `btree (druh_id)`
- INDEX `osoby_prukazosoby_osoba_id_70a93994`: `btree (osoba_id)`

### `osoby_vycvik` (2 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| zahajen | date | NULL |
| solo_povoleno | date | NULL |
| ukoncen | date | NULL |
| poznamka | character varying(200) |  |
| druh_id | bigint |  |
| osoba_id | bigint |  |

Omezení a indexy:
- FK `osoby_vycvik_druh_id_f1a24017_fk_ciselniky_druhprukazu_id`: `FOREIGN KEY (druh_id) REFERENCES ciselniky_druhprukazu(id) DEFERRABLE INITIALLY DEFERRED`
- FK `osoby_vycvik_osoba_id_340c59b3_fk_osoby_osoba_id`: `FOREIGN KEY (osoba_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- PK `osoby_vycvik_pkey`: `PRIMARY KEY (id)`
- INDEX `osoby_vycvik_druh_id_f1a24017`: `btree (druh_id)`
- INDEX `osoby_vycvik_osoba_id_340c59b3`: `btree (osoba_id)`

### `provoz_nastaveni` (1 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| email_rezim | character varying(10) |  |
| povolene_adresy | text |  |
| testovaci_provoz | boolean |  |
| automaticka_uzaverka | boolean |  |
| displej_klic | character varying(64) |  |
| hlidat_zpusobilost | boolean |  |
| hlidat_rozletanost | boolean |  |
| hlidat_letadla | boolean |  |

Omezení a indexy:
- PK `provoz_nastaveni_pkey`: `PRIMARY KEY (id)`

### `provoz_pushodber` (0 řádků lokálně)

| sloupec | typ | pozn. |
|---|---|---|
| id | bigint | identity |
| endpoint | character varying(1000) |  |
| p256dh | character varying(200) |  |
| auth | character varying(100) |  |
| zarizeni | character varying(200) |  |
| vytvoreno | timestamp with time zone |  |
| osoba_id | bigint |  |

Omezení a indexy:
- FK `provoz_pushodber_osoba_id_c5f0b402_fk_osoby_osoba_id`: `FOREIGN KEY (osoba_id) REFERENCES osoby_osoba(id) DEFERRABLE INITIALLY DEFERRED`
- PK `provoz_pushodber_pkey`: `PRIMARY KEY (id)`
- UNIQUE `provoz_pushodber_endpoint_key`: `UNIQUE (endpoint)`
- INDEX `provoz_pushodber_endpoint_e022840e_like`: `btree (endpoint varchar_pattern_ops)`
- INDEX `provoz_pushodber_osoba_id_c5f0b402`: `btree (osoba_id)`
