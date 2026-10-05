-- 003 data: POČÁTEČNÍ naplnění – letiště a plochy do 150 km od LKKL (bez heliportů
-- a zrušených). Zdroj: OurAirports (https://ourairports.com/data/, public domain),
-- staženo 5. 10. 2026; názvy bez anglických přípon (Airfield, Airstrip…).
-- Aktuální data jsou v databázi – uživatel je mění přímo.

INSERT INTO lkkl.lov_letiste (icao, nazev, domovske, zem_sirka, zem_delka, nadm_vyska_ft) VALUES
    ('LKKL', 'Kladno', true, 50.11280, 14.08970, 1421),  -- 0 km, CZ
    (NULL, 'Jeneč', false, 50.08250, 14.22278, 1243),  -- 10 km, CZ
    ('LKSN', 'Slaný', false, 50.21639, 14.08784, 1079),  -- 12 km, CZ
    (NULL, 'Buranos Aires', false, 50.00893, 14.03774, 1247),  -- 12 km, CZ
    ('LKPR', 'Václav Havel Airport Prague', false, 50.10087, 14.25991, 1247),  -- 12 km, CZ
    ('LKBU', 'Bubovice', false, 49.97440, 14.17810, 1401),  -- 17 km, CZ
    ('LKPC', 'Panensky Tynec', false, 50.30610, 13.93420, 1207),  -- 24 km, CZ
    ('LKVO', 'Vodochody', false, 50.21660, 14.39580, 919),  -- 25 km, CZ
    ('LKSZ', 'Sazená', false, 50.32470, 14.25890, 761),  -- 26 km, CZ
    ('LKTC', 'Točná', false, 49.98544, 14.42647, 1027),  -- 28 km, CZ
    ('LKRK', 'Rakovnik', false, 50.09420, 13.68890, 1270),  -- 29 km, CZ
    (NULL, 'Panoší Újezd', false, 50.03867, 13.69681, 1558),  -- 29 km, CZ
    ('LKLT', 'Letňany', false, 50.13140, 14.52560, 909),  -- 31 km, CZ
    ('LKKB', 'Prague–Kbely', false, 50.12140, 14.54360, 939),  -- 32 km, CZ
    ('LKHV', 'Hořovice', false, 49.84810, 13.89350, 1214),  -- 33 km, CZ
    (NULL, 'Radovesice', false, 50.40905, 14.08401, 538),  -- 33 km, CZ
    (NULL, 'Dušníky', false, 50.41278, 14.19806, 728),  -- 34 km, CZ
    ('LKRO', 'Roudnice nad Labem', false, 50.41019, 14.22708, 732),  -- 34 km, CZ
    (NULL, 'Horní Počáply', false, 50.41812, 14.38427, 524),  -- 40 km, CZ
    ('LKRA', 'Rana Loumy', false, 50.40390, 13.75190, 879),  -- 40 km, CZ
    (NULL, 'Charvátce', false, 50.43343, 13.81111, 915),  -- 41 km, CZ
    (NULL, 'Borek', false, 50.21086, 14.65769, 557),  -- 42 km, CZ
    (NULL, 'Kralovice', false, 49.98509, 13.52882, NULL),  -- 42 km, CZ
    (NULL, 'Říčany', false, 49.97444, 14.64917, NULL),  -- 43 km, CZ
    (NULL, 'Bitozeves', false, 50.37272, 13.63398, 764),  -- 43 km, CZ
    ('LKPM', 'Příbram', false, 49.72010, 14.10060, 1529),  -- 44 km, CZ
    (NULL, 'Štětí', false, 50.46500, 14.40611, 787),  -- 45 km, CZ
    (NULL, 'Terezín', false, 50.51944, 14.15583, 482),  -- 45 km, CZ
    ('LKZD', 'Žatec-Macerka', false, 50.31750, 13.51280, 879),  -- 47 km, CZ
    (NULL, 'Polepy', false, 50.52027, 14.27224, 692),  -- 47 km, CZ
    (NULL, 'Krpy', false, 50.32592, 14.66553, 803),  -- 47 km, CZ
    (NULL, 'Osičiny', false, 50.01647, 14.77221, 1280),  -- 50 km, CZ
    (NULL, 'Podbořany', false, 50.25067, 13.40972, 1060),  -- 51 km, CZ
    (NULL, 'Vrátkov', false, 50.03954, 14.82274, 1033),  -- 53 km, CZ
    ('LKRY', 'Rokycany', false, 49.75194, 13.58972, 1329),  -- 54 km, CZ
    ('LKMO', 'Most', false, 50.52500, 13.68310, 1089),  -- 54 km, CZ
    (NULL, 'Žihle u Plas', false, 50.03095, 13.33782, NULL),  -- 54 km, CZ
    ('LKPS', 'Plasy Rybnice', false, 49.92030, 13.37690, 1430),  -- 55 km, CZ
    (NULL, 'Březno u Chomutova', false, 50.40943, 13.44546, 1106),  -- 56 km, CZ
    (NULL, 'Mladá', false, 50.24359, 14.85586, NULL),  -- 56 km, CZ
    ('LKBE', 'Benešov', false, 49.74080, 14.64470, 1319),  -- 57 km, CZ
    (NULL, 'Bezno', false, 50.35692, 14.80683, NULL),  -- 58 km, CZ
    (NULL, 'Nučice', false, 49.95110, 14.86994, NULL),  -- 59 km, CZ
    ('LKCH', 'Chomutov', false, 50.46890, 13.46810, 1132),  -- 59 km, CZ
    (NULL, 'Chrášťany', false, 50.05872, 14.92307, 876),  -- 60 km, CZ
    (NULL, 'Teplice', false, 50.62083, 13.80977, 1148),  -- 60 km, CZ
    (NULL, 'Milovice', false, 50.23743, 14.90999, 650),  -- 60 km, CZ
    (NULL, 'Kostomlaty', false, 50.20843, 14.92585, NULL),  -- 61 km, CZ
    ('LKPL', 'Letkov', false, 49.72310, 13.45220, 1371),  -- 63 km, CZ
    (NULL, 'Manětín', false, 49.98280, 13.22784, 1578),  -- 63 km, CZ
    ('LKMB', 'Mladá Boleslav', false, 50.39830, 14.89830, 781),  -- 66 km, CZ
    (NULL, 'Sázava', false, 49.88783, 14.94055, 1345),  -- 66 km, CZ
    ('LKUL', 'Usti Nad Labem', false, 50.69970, 13.96970, 791),  -- 66 km, CZ
    (NULL, 'Ramŝ', false, 50.64167, 14.54139, NULL),  -- 67 km, CZ
    (NULL, 'Nymburk', false, 50.16910, 15.05245, 607),  -- 69 km, CZ
    (NULL, 'Lukla', false, 50.51102, 13.33914, 2172),  -- 69 km, CZ
    ('LKVL', 'Vlašim', false, 49.72890, 14.87890, 1421),  -- 71 km, CZ
    (NULL, 'Loučeň', false, 50.27874, 15.06101, 636),  -- 72 km, CZ
    (NULL, 'Horní Libchava', false, 50.70301, 14.49898, 899),  -- 72 km, CZ
    (NULL, 'Hradčany', false, 50.61925, 14.73275, 912),  -- 72 km, CZ
    ('LKCE', 'Česká Lípa', false, 50.70940, 14.56670, 932),  -- 74 km, CZ
    (NULL, 'Křinec', false, 50.25470, 15.12511, 646),  -- 75 km, CZ
    ('LKLN', 'Plzeň-Líně', false, 49.67520, 13.27460, 1188),  -- 76 km, CZ
    (NULL, 'Plešnice', false, 49.77222, 13.16222, 1339),  -- 76 km, CZ
    (NULL, 'Kněžmost', false, 50.47862, 15.00551, NULL),  -- 77 km, CZ
    (NULL, 'Poděbrady', false, 50.18431, 15.16655, NULL),  -- 77 km, CZ
    ('LKKO', 'Kolín', false, 50.00190, 15.17330, 932),  -- 78 km, CZ
    (NULL, 'Bynovec', false, 50.82190, 14.27174, NULL),  -- 80 km, CZ
    ('LKMH', 'Mnichovo Hradiště', false, 50.54020, 15.00660, 800),  -- 81 km, CZ
    (NULL, 'Chabeřice Private ULM', false, 49.74757, 15.06424, NULL),  -- 81 km, CZ
    ('LKTO', 'Toužim', false, 50.08640, 12.95280, 2139),  -- 81 km, CZ
    (NULL, 'Chotěšov', false, 49.65167, 13.18972, 1181),  -- 82 km, CZ
    ('LKER', 'Erpužice', false, 49.80280, 13.03810, 1572),  -- 83 km, CZ
    (NULL, 'Ostrov', false, 50.33628, 12.96915, 1680),  -- 83 km, CZ
    (NULL, 'Bezdružice', false, 49.89971, 12.96496, 1991),  -- 84 km, CZ
    (NULL, 'Liban', false, 50.37044, 15.20104, 738),  -- 84 km, CZ
    ('LKKV', 'Karlovy Vary', false, 50.20300, 12.91500, 1989),  -- 84 km, CZ
    (NULL, 'Písek UL', false, 49.33944, 14.11389, 1351),  -- 86 km, CZ
    (NULL, 'Lochousice', false, 49.67491, 13.09942, 1289),  -- 86 km, CZ
    ('LKZB', 'Zbraslavice', false, 49.81420, 15.20170, 1621),  -- 86 km, CZ
    (NULL, 'Všeň', false, 50.55511, 15.09461, 823),  -- 87 km, CZ
    (NULL, 'Chřibská', false, 50.85819, 14.46569, 1260),  -- 87 km, CZ
    (NULL, 'Vlastibořice', false, 50.61929, 15.03542, NULL),  -- 88 km, CZ
    (NULL, 'Kněžice u Jičína', false, 50.26300, 15.29741, 712),  -- 88 km, CZ
    (NULL, 'Vyskeř', false, 50.53714, 15.15714, NULL),  -- 89 km, CZ
    (NULL, 'Příchvoj u Jičína', false, 50.44135, 15.23598, NULL),  -- 89 km, CZ
    (NULL, 'Český Dub', false, 50.67806, 14.99972, 1283),  -- 90 km, CZ
    (NULL, 'Kostelec', false, 49.67076, 13.03224, 1581),  -- 90 km, CZ
    ('EDAG', 'Großrückerswalde', false, 50.64417, 13.12639, 2198),  -- 90 km, DE
    (NULL, 'Druzcov u Lípy', false, 50.72779, 14.92524, 1509),  -- 90 km, CZ
    ('LKTA', 'Tábor', false, 49.39110, 14.70830, 1440),  -- 92 km, CZ
    (NULL, 'Přešťovice u Strakonic', false, 49.28438, 13.96844, 1316),  -- 93 km, CZ
    ('LKHD', 'Hodkovice nad Mohelkou', false, 50.65720, 15.07780, 1480),  -- 93 km, CZ
    (NULL, 'Rohozec', false, 49.98194, 15.39278, 679),  -- 94 km, CZ
    (NULL, 'Hory', false, 50.21695, 12.77669, 1640),  -- 94 km, CZ
    ('LKCV', 'Čáslav', false, 49.93970, 15.38180, 794),  -- 94 km, CZ
    (NULL, 'Pretzschendorf', false, 50.88404, 13.53104, 1610),  -- 94 km, DE
    ('LKKT', 'Klatovy Josef Hubáč', false, 49.41830, 13.32190, 1299),  -- 95 km, CZ
    ('LKJC', 'Jičín', false, 50.43000, 15.33310, 863),  -- 95 km, CZ
    (NULL, 'Kozojedy', false, 50.32500, 15.38890, NULL),  -- 95 km, CZ
    (NULL, 'Želeč', false, 49.33055, 14.65889, 1513),  -- 96 km, CZ
    (NULL, 'Katovice', false, 49.26835, 13.80078, NULL),  -- 96 km, CZ
    ('LKSA', 'Staňkov', false, 49.56652, 13.04867, 1404),  -- 96 km, CZ
    ('LKST', 'Strakonice', false, 49.25170, 13.89280, 1381),  -- 97 km, CZ
    ('EDAR', 'Pirna-Pratzschwitz', false, 50.97960, 13.90845, 402),  -- 97 km, DE
    (NULL, 'Kříženec Planá', false, 49.87060, 12.77250, 2076),  -- 98 km, CZ
    ('LKLB', 'Liberec', false, 50.76705, 15.02307, 1329),  -- 98 km, CZ
    (NULL, 'Jiřičky', false, 49.55222, 15.15556, 1683),  -- 99 km, CZ
    (NULL, 'Rabi', false, 49.27515, 13.62781, 1480),  -- 99 km, CZ
    (NULL, 'Rovná u Sokolova', false, 50.10113, 12.67876, 2541),  -- 101 km, CZ
    (NULL, 'Lipová Sport', false, 51.00873, 14.34385, 1253),  -- 101 km, CZ
    (NULL, 'Škudly', false, 50.02194, 15.52056, NULL),  -- 103 km, CZ
    (NULL, 'Lomnice nad Popelkou', false, 50.54000, 15.38806, NULL),  -- 104 km, CZ
    ('LKTD', 'Tachov', false, 49.79722, 12.70717, 1640),  -- 105 km, CZ
    ('LKPN', 'Podhořany', false, 49.93920, 15.54970, 1250),  -- 106 km, CZ
    ('LKSO', 'Soběslav', false, 49.24550, 14.71299, 1342),  -- 106 km, CZ
    (NULL, 'Litochovice u Strakonic', false, 49.15434, 13.95672, 1781),  -- 107 km, CZ
    (NULL, 'Napajedla', false, 49.19889, 13.60000, 1761),  -- 108 km, CZ
    (NULL, 'Stará Paka', false, 50.50139, 15.48306, 1588),  -- 108 km, CZ
    (NULL, 'Mohorn', false, 50.99796, 13.44617, 1173),  -- 108 km, DE
    (NULL, 'Choteč', false, 50.43389, 15.53056, 1076),  -- 108 km, CZ
    (NULL, 'Částkovice', false, 49.40935, 15.14369, 1926),  -- 109 km, CZ
    (NULL, 'Stará Voda Emergency Field', false, 49.99679, 12.57512, 2106),  -- 109 km, CZ
    ('LKHC', 'Hořice', false, 50.35760, 15.57698, 922),  -- 109 km, CZ
    (NULL, 'Vodňany', false, 49.12821, 14.17325, NULL),  -- 110 km, CZ
    (NULL, 'Veselí u Přelouče', false, 50.00682, 15.61692, 809),  -- 110 km, CZ
    ('EDOH', 'Langhennersdorf', false, 50.94833, 13.26167, 1266),  -- 110 km, DE
    (NULL, 'Kejžlice', false, 49.59190, 15.40137, 1588),  -- 110 km, CZ
    (NULL, 'Mříčná', false, 50.59624, 15.48122, NULL),  -- 112 km, CZ
    ('EDCJ', 'Chemnitz/Jahnsdorf', false, 50.74750, 12.83750, 1198),  -- 113 km, DE
    (NULL, 'Studenec', false, 50.54958, 15.53591, 1804),  -- 114 km, CZ
    ('LKSR', 'Prachatice', false, 49.08250, 14.07580, 1572),  -- 115 km, CZ
    (NULL, 'Horni Prim', false, 50.22931, 15.70205, 919),  -- 116 km, CZ
    ('EDDC', 'Dresden', false, 51.13412, 13.76783, 755),  -- 116 km, DE
    (NULL, 'Milhostov u Chebu', false, 50.16412, 12.46409, 1535),  -- 116 km, CZ
    (NULL, 'Dynín', false, 49.12834, 14.63344, NULL),  -- 116 km, CZ
    (NULL, 'Jilemnice', false, 50.61056, 15.53862, 1776),  -- 117 km, CZ
    (NULL, 'Hlaska', false, 49.06694, 14.24139, 1430),  -- 117 km, CZ
    (NULL, 'Jestřabí v Krkonoších', false, 50.68215, 15.48237, 2546),  -- 117 km, CZ
    (NULL, 'Nová Včelnice', false, 49.26722, 15.07778, 1765),  -- 118 km, CZ
    (NULL, 'Hartenstein-Thierfeld', false, 50.67580, 12.67895, 1361),  -- 118 km, DE
    ('LKPD', 'Pardubice', false, 50.01505, 15.73981, 741),  -- 118 km, CZ
    (NULL, 'Hrabice airstrip', false, 49.06812, 13.76030, NULL),  -- 119 km, CZ
    (NULL, 'Dlouhé Dvory', false, 50.26494, 15.73942, 941),  -- 119 km, CZ
    ('LKHB', 'Havlíčkův Brod', false, 49.59720, 15.54920, 1519),  -- 119 km, CZ
    (NULL, 'Třebihošť', false, 50.43546, 15.69312, 1640),  -- 119 km, CZ
    ('LKCB', 'Cheb', false, 50.06610, 12.41170, 1585),  -- 120 km, CZ
    (NULL, 'Zbilidy Ultrallightport', false, 49.44803, 15.44008, 2071),  -- 122 km, CZ
    ('LKCR', 'Chrudim', false, 49.93640, 15.78060, 981),  -- 122 km, CZ
    ('LKHS', 'Hosín', false, 49.04000, 14.49500, 1621),  -- 123 km, CZ
    (NULL, 'Kunětice', false, 50.06833, 15.81250, 728),  -- 123 km, CZ
    ('LKCT', 'Chotěboř', false, 49.68580, 15.67610, 1949),  -- 123 km, CZ
    (NULL, 'Jarošov', false, 49.18714, 15.04273, NULL),  -- 124 km, CZ
    ('EDAB', 'Bautzen', false, 51.19361, 14.51972, 568),  -- 124 km, DE
    ('LKVR', 'Vrchlabí', false, 50.62420, 15.64640, 1611),  -- 124 km, CZ
    ('LKJH', 'Jindřichův Hradec', false, 49.15068, 14.97241, 1667),  -- 124 km, CZ
    ('LKHK', 'Hradec Králové', false, 50.25320, 15.84520, 791),  -- 126 km, CZ
    ('LKDK', 'Dvůr Králové nad Labem', false, 50.41420, 15.83690, 932),  -- 129 km, CZ
    (NULL, 'Tirschenreuth', false, 49.87390, 12.32810, 1600),  -- 129 km, DE
    ('EDOA', 'Auerbach', false, 50.49730, 12.37799, 1880),  -- 129 km, DE
    (NULL, 'Brauna', false, 51.28286, 14.05552, 587),  -- 130 km, DE
    (NULL, 'Nabočany', false, 49.94600, 15.89545, NULL),  -- 130 km, CZ
    (NULL, 'Chvojenec', false, 50.10863, 15.92674, NULL),  -- 131 km, CZ
    ('EDBX', 'Görlitz', false, 51.15889, 14.95028, 778),  -- 131 km, DE
    ('EDCM', 'Kamenz', false, 51.29694, 14.12750, 495),  -- 132 km, DE
    ('LKCS', 'České Budějovice South Bohemian', false, 48.94817, 14.42832, 1417),  -- 132 km, CZ
    ('EDCI', 'Klix', false, 51.27182, 14.50571, 486),  -- 132 km, DE
    (NULL, 'Arnschwang', false, 49.27163, 12.77831, 1355),  -- 133 km, DE
    ('EDBI', 'Zwickau', false, 50.70167, 12.45389, 1050),  -- 133 km, DE
    ('LKPI', 'Přibyslav', false, 49.58080, 15.76280, 1739),  -- 134 km, CZ
    (NULL, 'Beedeln', false, 51.00724, 12.81454, NULL),  -- 134 km, DE
    ('LKJA', 'Jaroměř', false, 50.33140, 15.95390, 889),  -- 135 km, CZ
    ('LKJI', 'Jihlava', false, 49.41940, 15.63530, 1821),  -- 135 km, CZ
    ('EDNB', 'Arnbruck', false, 49.12472, 12.98556, 1716),  -- 136 km, DE
    (NULL, 'Trutnov-Volanov', false, 50.56750, 15.86528, 1486),  -- 136 km, CZ
    (NULL, 'Göpfersdorf', false, 50.91387, 12.61293, 960),  -- 137 km, DE
    ('EDAK', 'Großenhain', false, 51.30806, 13.55556, 417),  -- 138 km, DE
    (NULL, 'Česká Skalice', false, 50.39967, 15.99102, 1106),  -- 139 km, CZ
    (NULL, 'Radim u Chrudimi', false, 49.90672, 16.00672, NULL),  -- 139 km, CZ
    (NULL, 'Doudleby', false, 48.88504, 14.48638, 1542),  -- 139 km, CZ
    ('LKSK', 'Skuteč', false, 49.82780, 16.00580, 1601),  -- 141 km, CZ
    (NULL, 'Kramolín', false, 48.91500, 14.72639, 1650),  -- 141 km, CZ
    ('EDAU', 'Riesa-Göhlis', false, 51.29361, 13.35611, 322),  -- 141 km, DE
    (NULL, 'Luka nad Jihlavou', false, 49.38244, 15.71368, NULL),  -- 142 km, CZ
    (NULL, 'Cham-Janahof', false, 49.21205, 12.65410, 1200),  -- 144 km, DE
    (NULL, 'Vraclav u Vysokého Mýta', false, 49.95313, 16.10776, 1211),  -- 145 km, CZ
    (NULL, 'Riesa-Canitz', false, 51.30240, 13.22800, 410),  -- 146 km, DE
    ('LKNM', 'Nové Město nad Metují', false, 50.36420, 16.11360, 1001),  -- 147 km, CZ
    (NULL, 'Erbendorf', false, 49.84380, 12.06714, 1640),  -- 148 km, DE
    ('EDAC', 'Leipzig–Altenburg', false, 50.98195, 12.50639, 640),  -- 148 km, DE
    ('EDOT', 'Greiz-Obergrochlitz', false, 50.64398, 12.17457, 1266),  -- 148 km, DE
    (NULL, 'Náchod Vysokov', false, 50.41296, 16.12185, 1443),  -- 148 km, CZ
    ('EPJG', 'Jelenia Góra', false, 50.89890, 15.78560, 1119),  -- 148 km, PL
    ('EDAT', 'Nardt', false, 51.45111, 14.19944, 382),  -- 149 km, DE
    ('EDQW', 'Weiden in der Oberpfalz', false, 49.67890, 12.11640, 1329),  -- 149 km, DE
    ('EDOQ', 'Oschatz', false, 51.29677, 13.07869, 502);  -- 150 km, DE
