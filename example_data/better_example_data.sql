BEGIN TRANSACTION;
DROP TABLE IF EXISTS "event";
CREATE TABLE event (
    id INTEGER PRIMARY KEY,
    proposal_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    author_name TEXT NOT NULL,
    -- 0 = against, 1 = in favour
    decision INTEGER,
    comment TEXT,
    created TIMESTAMP NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (proposal_id) REFERENCES proposal (id),
    -- It has to be one, or the other
    CHECK (decision IS NOT NULL or comment IS NOT NULL)
);
DROP TABLE IF EXISTS "proposal";
CREATE TABLE proposal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL,
    author_name TEXT NOT NULL,
    -- 0 = Executive committee (VV), 1 = General committee (SO), 2 = Cooperative board (Představenstvo Druzstva), 3 = Členové spolku, 4 = Členové družstva
    type INTEGER NOT NULL DEFAULT 0,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    -- Estimated cost CZK
    cost INTEGER,
    -- Order state - None, Ordered, Ready, etc
    state TEXT,
    created TIMESTAMP NOT NULL DEFAULT (datetime('now','localtime')),
    deleted TIMESTAMP DEFAULT NULL,
    -- List of IDs that can vote on this proposal, set at creation of the proposal and must not change
    deciders TEXT NOT NULL,
    -- How many votes in favour of proposal are required for it to be accepted. Calculated at proposal creation from selected requirement
    acceptance_treshold INT NOT NULL,
    -- When the proposal was decided (Locked)
    decided TIMESTAMP DEFAULT NULL
);
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (1,1,3579,'VLHOTA',1,'jo','2025-11-24 13:42:19');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (2,1,797,'zit',1,'jo','2025-11-24 13:42:33');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (3,1,277,'kub',1,'jo','2025-11-24 13:42:48');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (4,1,4921,'mk',1,'jo','2025-11-24 13:43:03');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (5,2,4921,'mk',0,'ne','2025-11-24 13:51:52');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (6,2,277,'kub',0,'ne','2025-11-24 13:51:53');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (7,2,797,'zit',0,'ne','2025-11-24 13:51:53');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (8,2,3579,'VLHOTA',0,'ne','2025-11-24 13:51:53');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (9,3,4921,'mk',0,NULL,'2025-11-24 14:04:06');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (10,3,277,'kub',0,NULL,'2025-11-24 14:04:06');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (11,3,797,'zit',0,NULL,'2025-11-24 14:04:06');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (12,4,4921,'mk',0,NULL,'2025-11-24 14:06:40');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (13,4,277,'kub',0,NULL,'2025-11-24 14:06:40');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (14,4,797,'zit',0,NULL,'2025-11-24 14:06:40');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (15,4,3579,'VLHOTA',0,NULL,'2025-11-24 14:06:40');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (16,4,656,'loc',0,NULL,'2025-11-24 14:06:59');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (17,5,4921,'mk',1,NULL,'2025-11-24 14:07:41');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (18,5,277,'kub',1,NULL,'2025-11-24 14:07:41');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (19,5,797,'zit',1,NULL,'2025-11-24 14:07:41');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (20,5,3579,'VLHOTA',1,NULL,'2025-11-24 14:07:41');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (21,5,656,'loc',1,NULL,'2025-11-24 14:07:41');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (22,6,4921,'mk',1,NULL,'2025-11-24 14:09:27');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (23,7,3579,'VLHOTA',1,NULL,'2025-11-24 14:07:41');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (24,7,797,'zit',1,NULL,'2025-11-24 14:07:41');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (25,7,277,'kub',1,NULL,'2025-11-24 14:07:41');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (26,7,4921,'mk',1,NULL,'2025-11-24 14:06:40');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (27,10,3579,'VLHOTA',0,'ne','2025-11-24 15:25:55');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (28,10,797,'zit',0,'ne','2025-11-24 15:25:55');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (29,10,277,'kub',0,'ne','2025-11-24 15:25:55');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (30,10,4921,'mk',0,'ne','2025-11-24 15:25:55');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (31,12,3579,'VLHOTA',1,'jo','2025-11-24 15:26:49');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (32,12,797,'zit',0,'ne','2025-11-24 15:26:49');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (33,13,3579,'VLHOTA',0,'ne','2025-11-24 15:27:19');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (34,13,797,'zit',0,'ne','2025-11-24 15:27:19');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (35,13,277,'kub',0,'ne','2025-11-24 15:27:19');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (36,14,3579,'VLHOTA',1,'jooo','2025-11-24 15:31:04');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (37,14,797,'zit',1,'jooo','2025-11-24 15:31:04');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (38,14,277,'kub',1,'jooo','2025-11-24 15:31:04');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (39,14,4921,'mk',1,'jooo','2025-11-24 15:31:04');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (40,14,1980,'pkriz',1,'jooo','2025-11-24 15:31:04');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (41,15,3579,'VLHOTA',1,'jooo','2025-11-24 15:49:28');
INSERT INTO "event" ("id","proposal_id","author_id","author_name","decision","comment","created") VALUES (42,15,1980,'pkriz',1,'jooo','2025-11-24 15:49:29');
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (1,9000,'Ondřej Pithart',0,'Test pro VV s 1/2 SCHVALIT','Test pro VV s 1/2',123123,NULL,'2025-11-24 13:41:17',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "3135": "Vecíno", "656": "Locutus", "4921": "Miky", "3579": "VojtaLhota"}',4,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (2,9000,'Ondřej Pithart',0,'Test pro VV s 1/2 ZAMITNOUT','Test pro VV s 1/2 ZAMITNOUT',9770,NULL,'2025-11-24 13:51:09',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "3135": "Vecíno", "656": "Locutus", "4921": "Miky", "3579": "VojtaLhota"}',4,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (3,9000,'Ondřej Pithart',0,'Test pro VV s 2/3 nedostatek','Test pro VV s 2/3 nedostatek',123,NULL,'2025-11-24 14:03:03',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "3135": "Vecíno", "656": "Locutus", "4921": "Miky", "3579": "VojtaLhota"}',5,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (4,9000,'Ondřej Pithart',0,'Test pro VV s 2/3 ZAMITNOUT','Test pro VV s 2/3 Zamitnout',1,NULL,'2025-11-24 14:06:03',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "3135": "Vecíno", "656": "Locutus", "4921": "Miky", "3579": "VojtaLhota"}',5,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (5,9000,'Ondřej Pithart',0,'Test pro VV s 2/3 SCHVALIT','Test pro VV s 2/3 projit',945000,NULL,'2025-11-24 14:07:20',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "3135": "Vecíno", "656": "Locutus", "4921": "Miky", "3579": "VojtaLhota"}',5,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (6,9000,'Ondřej Pithart',0,'Test pro VV s 1/2 nedostatek hlasu','jediny hlas',6000000,NULL,'2025-11-24 14:08:49',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "3135": "Vecíno", "656": "Locutus", "4921": "Miky", "3579": "VojtaLhota"}',4,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (7,9000,'Ondřej Pithart',2,'Test pro PD s 1/2 SCHVALIT','Test pro PD s 1/2 SCHVALIT',65000,NULL,'2025-11-24 14:10:23',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "4921": "Miky", "3579": "VojtaLhota"}',3,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (10,9000,'Ondřej Pithart',2,'Test pro PD s 1/2 ZAMITNOUT','Test pro PD s 1/2 ZAMITNOUT',5695400,NULL,'2025-11-24 15:23:29',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "4921": "Miky", "3579": "VojtaLhota"}',3,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (11,9000,'Ondřej Pithart',2,'Test pro PD s 1/2 NECHAT VYHNIT','Test pro PD s 1/2 NECHAT VYHNIT',3461400,NULL,'2025-11-24 15:23:44',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "4921": "Miky", "3579": "VojtaLhota"}',3,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (12,9000,'Ondřej Pithart',2,'Test pro PD s 2/3 NECHAT VYHNIT','Test pro PD s 1/2 NECHAT VYHNIT',1905000,NULL,'2025-11-24 15:24:22',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "4921": "Miky", "3579": "VojtaLhota"}',3,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (13,9000,'Ondřej Pithart',2,'Test pro PD s 2/3 ZAMITNOUT','Test pro PD s 1/2 NECHAT VYHNIT',6403000,NULL,'2025-11-24 15:24:27',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "4921": "Miky", "3579": "VojtaLhota"}',3,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (14,9000,'Ondřej Pithart',2,'Test pro PD s 2/3 SCHVALIT','Test pro PD s 1/2 NECHAT VYHNIT',3746400,NULL,'2025-11-24 15:24:29',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "4921": "Miky", "3579": "VojtaLhota"}',3,NULL);
INSERT INTO "proposal" ("id","author_id","author_name","type","subject","description","cost","state","created","deleted","deciders","acceptance_treshold","decided") VALUES (15,9000,'Ondřej Pithart',2,'Test pro PD s 2/3 TESNE PRED SCHVALENIM','Test pro PD s 2/3 TESNE PRED SCHVALENIM',3746400,NULL,'2025-11-24 15:48:55',NULL,'{"277": "Jakub", "797": "zitnyp", "1980": "pavkriz", "4921": "Miky", "3579": "VojtaLhota", "9000": "ondra"}',3,NULL);
COMMIT;
