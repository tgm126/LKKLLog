-- 003 data: POČÁTEČNÍ naplnění – česká letiště s kódem ICAO do 150 km od LKKL.
-- Zdroj: OurAirports (https://ourairports.com/data/, public domain),
-- staženo 5. 10. 2026; názvy bez anglických přípon (Airfield, Airstrip…).
-- Aktuální data jsou v databázi – uživatel je mění přímo.

INSERT INTO lkkl.lov_letiste (icao, nazev, domovske, zem_sirka, zem_delka, nadm_vyska_ft) VALUES
    ('LKKL', 'Kladno', true, 50.11280, 14.08970, 1421),  -- 0 km, CZ
    ('LKSN', 'Slaný', false, 50.21639, 14.08784, 1079),  -- 12 km, CZ
    ('LKPR', 'Václav Havel Airport Prague', false, 50.10087, 14.25991, 1247),  -- 12 km, CZ
    ('LKBU', 'Bubovice', false, 49.97440, 14.17810, 1401),  -- 17 km, CZ
    ('LKPC', 'Panensky Tynec', false, 50.30610, 13.93420, 1207),  -- 24 km, CZ
    ('LKVO', 'Vodochody', false, 50.21660, 14.39580, 919),  -- 25 km, CZ
    ('LKSZ', 'Sazená', false, 50.32470, 14.25890, 761),  -- 26 km, CZ
    ('LKTC', 'Točná', false, 49.98544, 14.42647, 1027),  -- 28 km, CZ
    ('LKRK', 'Rakovnik', false, 50.09420, 13.68890, 1270),  -- 29 km, CZ
    ('LKLT', 'Letňany', false, 50.13140, 14.52560, 909),  -- 31 km, CZ
    ('LKKB', 'Prague–Kbely', false, 50.12140, 14.54360, 939),  -- 32 km, CZ
    ('LKHV', 'Hořovice', false, 49.84810, 13.89350, 1214),  -- 33 km, CZ
    ('LKRO', 'Roudnice nad Labem', false, 50.41019, 14.22708, 732),  -- 34 km, CZ
    ('LKRA', 'Rana Loumy', false, 50.40390, 13.75190, 879),  -- 40 km, CZ
    ('LKPM', 'Příbram', false, 49.72010, 14.10060, 1529),  -- 44 km, CZ
    ('LKZD', 'Žatec-Macerka', false, 50.31750, 13.51280, 879),  -- 47 km, CZ
    ('LKRY', 'Rokycany', false, 49.75194, 13.58972, 1329),  -- 54 km, CZ
    ('LKMO', 'Most', false, 50.52500, 13.68310, 1089),  -- 54 km, CZ
    ('LKPS', 'Plasy Rybnice', false, 49.92030, 13.37690, 1430),  -- 55 km, CZ
    ('LKBE', 'Benešov', false, 49.74080, 14.64470, 1319),  -- 57 km, CZ
    ('LKCH', 'Chomutov', false, 50.46890, 13.46810, 1132),  -- 59 km, CZ
    ('LKPL', 'Letkov', false, 49.72310, 13.45220, 1371),  -- 63 km, CZ
    ('LKMB', 'Mladá Boleslav', false, 50.39830, 14.89830, 781),  -- 66 km, CZ
    ('LKUL', 'Usti Nad Labem', false, 50.69970, 13.96970, 791),  -- 66 km, CZ
    ('LKVL', 'Vlašim', false, 49.72890, 14.87890, 1421),  -- 71 km, CZ
    ('LKCE', 'Česká Lípa', false, 50.70940, 14.56670, 932),  -- 74 km, CZ
    ('LKLN', 'Plzeň-Líně', false, 49.67520, 13.27460, 1188),  -- 76 km, CZ
    ('LKKO', 'Kolín', false, 50.00190, 15.17330, 932),  -- 78 km, CZ
    ('LKMH', 'Mnichovo Hradiště', false, 50.54020, 15.00660, 800),  -- 81 km, CZ
    ('LKTO', 'Toužim', false, 50.08640, 12.95280, 2139),  -- 81 km, CZ
    ('LKER', 'Erpužice', false, 49.80280, 13.03810, 1572),  -- 83 km, CZ
    ('LKKV', 'Karlovy Vary', false, 50.20300, 12.91500, 1989),  -- 84 km, CZ
    ('LKZB', 'Zbraslavice', false, 49.81420, 15.20170, 1621),  -- 86 km, CZ
    ('LKTA', 'Tábor', false, 49.39110, 14.70830, 1440),  -- 92 km, CZ
    ('LKHD', 'Hodkovice nad Mohelkou', false, 50.65720, 15.07780, 1480),  -- 93 km, CZ
    ('LKCV', 'Čáslav', false, 49.93970, 15.38180, 794),  -- 94 km, CZ
    ('LKKT', 'Klatovy Josef Hubáč', false, 49.41830, 13.32190, 1299),  -- 95 km, CZ
    ('LKJC', 'Jičín', false, 50.43000, 15.33310, 863),  -- 95 km, CZ
    ('LKSA', 'Staňkov', false, 49.56652, 13.04867, 1404),  -- 96 km, CZ
    ('LKST', 'Strakonice', false, 49.25170, 13.89280, 1381),  -- 97 km, CZ
    ('LKLB', 'Liberec', false, 50.76705, 15.02307, 1329),  -- 98 km, CZ
    ('LKTD', 'Tachov', false, 49.79722, 12.70717, 1640),  -- 105 km, CZ
    ('LKPN', 'Podhořany', false, 49.93920, 15.54970, 1250),  -- 106 km, CZ
    ('LKSO', 'Soběslav', false, 49.24550, 14.71299, 1342),  -- 106 km, CZ
    ('LKHC', 'Hořice', false, 50.35760, 15.57698, 922),  -- 109 km, CZ
    ('LKSR', 'Prachatice', false, 49.08250, 14.07580, 1572),  -- 115 km, CZ
    ('LKPD', 'Pardubice', false, 50.01505, 15.73981, 741),  -- 118 km, CZ
    ('LKHB', 'Havlíčkův Brod', false, 49.59720, 15.54920, 1519),  -- 119 km, CZ
    ('LKCB', 'Cheb', false, 50.06610, 12.41170, 1585),  -- 120 km, CZ
    ('LKCR', 'Chrudim', false, 49.93640, 15.78060, 981),  -- 122 km, CZ
    ('LKHS', 'Hosín', false, 49.04000, 14.49500, 1621),  -- 123 km, CZ
    ('LKCT', 'Chotěboř', false, 49.68580, 15.67610, 1949),  -- 123 km, CZ
    ('LKVR', 'Vrchlabí', false, 50.62420, 15.64640, 1611),  -- 124 km, CZ
    ('LKJH', 'Jindřichův Hradec', false, 49.15068, 14.97241, 1667),  -- 124 km, CZ
    ('LKHK', 'Hradec Králové', false, 50.25320, 15.84520, 791),  -- 126 km, CZ
    ('LKDK', 'Dvůr Králové nad Labem', false, 50.41420, 15.83690, 932),  -- 129 km, CZ
    ('LKCS', 'České Budějovice South Bohemian', false, 48.94817, 14.42832, 1417),  -- 132 km, CZ
    ('LKPI', 'Přibyslav', false, 49.58080, 15.76280, 1739),  -- 134 km, CZ
    ('LKJA', 'Jaroměř', false, 50.33140, 15.95390, 889),  -- 135 km, CZ
    ('LKJI', 'Jihlava', false, 49.41940, 15.63530, 1821),  -- 135 km, CZ
    ('LKSK', 'Skuteč', false, 49.82780, 16.00580, 1601),  -- 141 km, CZ
    ('LKNM', 'Nové Město nad Metují', false, 50.36420, 16.11360, 1001);  -- 147 km, CZ
