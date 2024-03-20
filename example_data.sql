BEGIN TRANSACTION;
INSERT INTO "proposal" VALUES (1,9000,0,' AX Mikrotik','Vážený VV,

chtěl bych nasadit nový Mikrotik na spoj Trnava -> Homyle2.
Tímto bych to posunul z AN rovnou na AX.
Prosím tedy o toto:

2x https://abctech.cz/mikrotik-l11ug-5haxd_d41513.html

Doufám, že u toho budou dost dlouhé podložky a šroubky, aby to pasovalo do gentleboxů.',5000,'2024-03-07 11:03:15',NULL);
INSERT INTO "proposal" VALUES (2,9000,1,'Hlasovani pro SO','kvůli přechodu na 10G v Bydžově budeme nuceni vyměnit routr, do stávajícího routru na ATOM platformě nedáme víc než jednoportovou 10G kartu (na víc nemá deska PCI-E linky), využijeme tedy "náhradní routr" s EPYC deskou do které dáme 4x10G SuperMicro kartu (PCI-E 8x). Náhradní routr koupíme nový. Žádám tedy o:

1x https://smicro.cz/supermicro-mbd-m11sdv-4c-ln4f-b-1
1x 8GB ram
2x 240GB SSD
1x 2U RM case
3x ventilátor
1x ATX PSU
1x 2x10Gb karta ',123,'2024-03-06 11:03:15',NULL);
INSERT INTO "proposal" VALUES (3,9000,0,'Probluz router a swtich','Ahoj,
prosím o schválení:

1x https://www.abctech.cz/default.asp?cls=stoitem&stiid=39472&whisperword=5009
1x rack uši pro 5009
1x https://www.abctech.cz/mikrotik-cloud-router-switch-crs112-8p-4s-in-8x-glan-s-poe-4x-sfp-los-5_d36032.html?fulltextword=crs112
1x rack uši pro crs112
1x DAC kabel k propojení
1x techniky na přehození

Po předělání el. na Probluzi bychom ještě potřebovali věci výše, protože stávající Mikrotik router funguje jen na 230V. Techniky prosím o přehození, protože tomu nerozumím a navíc el. předělávali oni, sám budu maximálně nápomocen.

Děkuji.',11000,'2024-03-20 13:06:34',NULL);
INSERT INTO "user" VALUES (1,'user1',NULL,10,'2024-03-20 13:07:16');
INSERT INTO "user" VALUES (2,'user2',NULL,10,'2024-03-20 13:07:35');
INSERT INTO "user" VALUES (3,'user3',NULL,10,'2024-03-20 13:07:44');
INSERT INTO "user" VALUES (3579,'VojtaLhta',NULL,10,'2024-03-20 13:06:49');
INSERT INTO "user" VALUES (9000,'OndraLhota','ondrej@pithart.com',1,'2024-03-07 11:02:46');
INSERT INTO "event" VALUES (1,1,9000,1,NULL,'2024-03-07 11:02:46');
INSERT INTO "event" VALUES (2,1,1,1,NULL,'2024-03-20 13:08:53');
INSERT INTO "event" VALUES (3,1,2,1,'souhlas','2024-03-20 13:09:06');
INSERT INTO "event" VALUES (4,1,3,1,NULL,'2024-03-20 13:09:35');
INSERT INTO "event" VALUES (5,1,3579,0,'nelibi','2024-03-20 13:12:35');
COMMIT;
