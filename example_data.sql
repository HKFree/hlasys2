PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
INSERT INTO proposal VALUES(1,9000,0,'Test subject','test descr descr descr descr descr descr ',5000,'2024-03-07 11:03:15',NULL);
INSERT INTO proposal VALUES(2,9000,1,'Hlasovani pro SO','nevim co napsat xd ',123,'2024-03-06 11:03:15',NULL);
INSERT INTO user VALUES(9000,'OndraLhota','ondrej@pithart.com',1,'2024-03-07 11:02:46');
INSERT INTO event VALUES(1, 1, 9000, 1, NULL, '2024-03-07 11:02:46');
COMMIT;
