BEGIN TRANSACTION;
-- Inserting proposals
INSERT INTO proposal (author_id, author_name, type, subject, description, cost, created)
VALUES
(277, 'John Doe', 1, 'Increase in annual membership fees', 'Proposal to increase the annual membership fees by 10% to support community programs.', 5000, '2024-02-21 09:42:56'),
(797, 'Jane Smith', 0, 'New office renovation plan', 'A proposal to approve the office renovation plan for upgrading infrastructure.', 25000, '2024-03-11 10:33:12'),
(1980, 'George White', 2, 'Cooperative expansion', 'Proposal to expand the cooperative by opening two new branches in nearby cities.', 30000, '2024-01-14 08:22:45'),
(3135, 'Emily Brown', 3, 'Audit proposal for financial transparency', 'A proposal to hire an external auditor to ensure financial transparency for the past year.', 10000, '2024-05-03 16:14:29'),
(656, 'Michael Green', 1, 'New IT infrastructure', 'Proposal to approve funds for the upgrade of the IT infrastructure for the organization.', 15000, '2024-07-17 11:27:12'),
(4291, 'David Harris', 2, 'Renewable energy investment', 'Proposal to invest in renewable energy sources for the cooperative operations.', 20000, '2024-08-19 13:45:02'),
(3570, 'Sophia Lewis', 0, 'Employee wellness program', 'A proposal to approve the funding for an employee wellness program to improve overall well-being.', 8000, '2024-02-28 17:00:12'),
(277, 'John Doe', 3, 'Approval of new board members', 'Proposal to approve the nominations for new board members of the organization.', 0, '2024-06-24 14:56:03'),
(797, 'Jane Smith', 1, 'Team-building activities for employees', 'A proposal to fund team-building activities to improve employee morale and teamwork.', 7000, '2024-01-09 10:18:23'),
(1980, 'George White', 2, 'Cooperative member training', 'Proposal to introduce a mandatory training program for all cooperative members.', 6000, '2024-05-22 12:10:14'),
(3135, 'Emily Brown', 3, 'Leadership development program', 'Proposal to launch a leadership development program for current managers and aspiring leaders.', 12000, '2024-03-06 15:35:50'),
(656, 'Michael Green', 0, 'Sustainability practices implementation', 'Proposal to implement new sustainability practices within the organization.', 10000, '2024-04-10 09:21:45');

-- Events for Proposal 1 (Increase in annual membership fees)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(1, 277, 'John Doe', 1, 'In favour of increasing the membership fees to support growth.', '2024-02-21 09:50:42'),
(1, 797, 'Jane Smith', 0, 'Against the increase; we should explore other ways to raise funds.', '2024-02-21 09:55:35'),
(1, 3135, 'Emily Brown', 1, 'In favour, we need these funds to improve community services.', '2024-02-21 10:00:25'),
(1, 656, 'Michael Green', 1, 'In favour, but I have concerns about how it will affect members.', '2024-02-21 10:05:50'),
(1, 4291, 'David Harris', 0, 'Against. Increasing fees will alienate long-term members.', '2024-02-21 10:10:15'),
(1, 3570, 'Sophia Lewis', 1, 'In favour. I believe the benefits outweigh the potential downsides.', '2024-02-21 10:12:22');

-- Events for Proposal 2 (New office renovation plan)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(2, 1980, 'George White', 1, 'In favour of the renovation; its long overdue.', '2024-03-11 10:40:15'),
(2, 656, 'Michael Green', 0, 'Against. We should allocate the funds elsewhere.', '2024-03-11 10:45:42'),
(2, 4291, 'David Harris', 1, 'In favour, the office needs a more professional look.', '2024-03-11 10:50:00'),
(2, 277, 'John Doe', 1, 'I fully support the renovation. It will improve productivity.', '2024-03-11 10:55:25');

-- Events for Proposal 3 (Cooperative expansion)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(3, 4291, 'David Harris', 1, 'In favour. Expanding will provide us with more opportunities to grow.', '2024-01-14 08:30:12'),
(3, 3570, 'Sophia Lewis', 0, 'Against. I think we need to consolidate our existing operations first.', '2024-01-14 08:35:10'),
(3, 797, 'Jane Smith', 1, 'I support the expansion, but we should ensure it is well-planned.', '2024-01-14 08:40:27'),
(3, 1980, 'George White', NULL, 'I’m not sure yet; I need more details on the market research.', '2024-01-14 08:45:38');

-- Events for Proposal 4 (Audit proposal for financial transparency)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(4, 277, 'John Doe', 1, 'In favour of the external audit for transparency.', '2024-05-03 16:20:02'),
(4, 1980, 'George White', 1, 'In favour. Its important to ensure financial accountability.', '2024-05-03 16:25:10'),
(4, 656, 'Michael Green', 0, 'Against. I believe our internal systems are sufficient for now.', '2024-05-03 16:30:42'),
(4, 4291, 'David Harris', NULL, 'I need more details on the cost before I decide.', '2024-05-03 16:35:25');

-- Events for Proposal 5 (New IT infrastructure)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(5, 656, 'Michael Green', 1, 'In favour. We need to improve our IT systems to stay competitive.', '2024-07-17 11:35:14'),
(5, 4291, 'David Harris', 0, 'Against. We should consider alternatives before spending so much.', '2024-07-17 11:40:02'),
(5, 3570, 'Sophia Lewis', 1, 'In favour. Better IT infrastructure will boost efficiency.', '2024-07-17 11:45:10'),
(5, 797, 'Jane Smith', 1, 'In favour, this is essential for the long-term health of the company.', '2024-07-17 11:50:29'),
(5, 1980, 'George White', NULL, 'I have some reservations about the projected costs, but overall I support the initiative.', '2024-07-17 11:55:50');

-- Events for Proposal 6 (Renewable energy investment)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(6, 3570, 'Sophia Lewis', 1, 'In favour of renewable energy; its the future.', '2024-08-19 13:50:02'),
(6, 797, 'Jane Smith', 0, 'Against. I need more assurances on return on investment.', '2024-08-19 13:55:10'),
(6, 3135, 'Emily Brown', NULL, 'Im undecided. I need more information on the potential savings.', '2024-08-19 13:57:29');

-- Events for Proposal 7 (Employee wellness program)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(7, 277, 'John Doe', 1, 'In favour of the wellness program. Our employees need support.', '2024-02-28 17:10:10'),
(7, 4291, 'David Harris', NULL, 'I think we need to focus on the details of the program first.', '2024-02-28 17:15:22'),
(7, 1980, 'George White', 1, 'In favour of wellness initiatives. They will improve employee productivity.', '2024-02-28 17:20:50');

-- Events for Proposal 8 (Approval of new board members)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(8, 797, 'Jane Smith', 1, 'In favour of the new members. They bring fresh perspectives.', '2024-06-24 15:00:03'),
(8, 1980, 'George White', 0, 'Against. Im not sure the new members have enough relevant experience.', '2024-06-24 15:05:07'),
(8, 656, 'Michael Green', NULL, 'I’m still evaluating the nominees and have no decision yet.', '2024-06-24 15:10:12');

-- Events for Proposal 9 (Team-building activities for employees)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(9, 3135, 'Emily Brown', 1, 'In favour. Team-building activities will help improve collaboration.', '2024-01-09 10:30:20'),
(9, 656, 'Michael Green', NULL, 'I support the idea but need to ensure the budget is reasonable.', '2024-01-09 10:35:45');

-- Events for Proposal 10 (Cooperative member training)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(10, 4291, 'David Harris', 1, 'In favour. Training will strengthen cooperative skills and improve efficiency.', '2024-05-22 12:15:00'),
(10, 3570, 'Sophia Lewis', NULL, 'I’m still unsure. I need to know the specifics of the training program.', '2024-05-22 12:18:34');

-- Events for Proposal 11 (Leadership development program)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(11, 277, 'John Doe', 1, 'In favour. Leadership development is essential for company growth.', '2024-03-06 15:45:22'),
(11, 797, 'Jane Smith', 0, 'Against. We should focus on operational needs before leadership programs.', '2024-03-06 15:50:55');

-- Events for Proposal 12 (Sustainability practices implementation)
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(12, 1980, 'George White', 1, 'In favour. We must reduce our carbon footprint and be more sustainable.', '2024-04-10 09:35:48'),
(12, 656, 'Michael Green', NULL, 'I support sustainability practices, but I would need more details.', '2024-04-10 09:40:11');

-- Events for Proposal 1 (Increase in annual membership fees)
-- Majority in favour, 5 votes in favour, 1 against
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(1, 277, 'John Doe', 1, 'In favour of increasing the membership fees to support growth.', '2024-02-21 09:50:42'),
(1, 797, 'Jane Smith', 0, 'Against the increase; we should explore other ways to raise funds.', '2024-02-21 09:55:35'),
(1, 3135, 'Emily Brown', 1, 'In favour, we need these funds to improve community services.', '2024-02-21 10:00:25'),
(1, 656, 'Michael Green', 1, 'In favour, but I have concerns about how it will affect members.', '2024-02-21 10:05:50'),
(1, 4291, 'David Harris', 0, 'Against. Increasing fees will alienate long-term members.', '2024-02-21 10:10:15'),
(1, 3570, 'Sophia Lewis', 1, 'In favour. I believe the benefits outweigh the potential downsides.', '2024-02-21 10:12:22'),
(1, 1234, 'Random User', 1, 'In favour of the increase. We need additional resources.', '2024-02-21 10:15:00');

-- Events for Proposal 2 (New office renovation plan)
-- Majority against, 4 votes against, 1 in favour
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(2, 1980, 'George White', 1, 'In favour of the renovation; its long overdue.', '2024-03-11 10:40:15'),
(2, 656, 'Michael Green', 0, 'Against. We should allocate the funds elsewhere.', '2024-03-11 10:45:42'),
(2, 4291, 'David Harris', 0, 'Against. We need to prioritize other projects first.', '2024-03-11 10:50:00'),
(2, 277, 'John Doe', 0, 'Against. The cost of the renovation is too high for this period.', '2024-03-11 10:55:25'),
(2, 797, 'Jane Smith', 0, 'Against. I think there are more urgent needs at the moment.', '2024-03-11 11:00:00');

-- Events for Proposal 3 (Cooperative expansion)
-- Majority in favour, 4 votes in favour, 1 against
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(3, 4291, 'David Harris', 1, 'In favour. Expanding will provide us with more opportunities to grow.', '2024-01-14 08:30:12'),
(3, 3570, 'Sophia Lewis', 0, 'Against. I think we need to consolidate our existing operations first.', '2024-01-14 08:35:10'),
(3, 797, 'Jane Smith', 1, 'I support the expansion, but we should ensure it is well-planned.', '2024-01-14 08:40:27'),
(3, 277, 'John Doe', 1, 'In favour. The expansion is crucial for future success.', '2024-01-14 08:45:15'),
(3, 1980, 'George White', 1, 'I am in favour of the expansion. It will strengthen our position in the market.', '2024-01-14 08:50:00'),
(3, 4567, 'Random User', 1, 'I believe expanding now is a strategic move that will benefit the cooperative.', '2024-01-14 08:55:00');

-- Events for Proposal 4 (Audit proposal for financial transparency)
-- Majority in favour, 3 votes in favour, 1 against
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(4, 277, 'John Doe', 1, 'In favour of the external audit for transparency.', '2024-05-03 16:20:02'),
(4, 1980, 'George White', 1, 'In favour. Its important to ensure financial accountability.', '2024-05-03 16:25:10'),
(4, 656, 'Michael Green', 0, 'Against. I believe our internal systems are sufficient for now.', '2024-05-03 16:30:42'),
(4, 4291, 'David Harris', 1, 'I support the audit. Transparency is important for trust.', '2024-05-03 16:35:25'),
(4, 3135, 'Emily Brown', NULL, 'I am undecided. I need more details on how this will impact our operations.', '2024-05-03 16:40:00');

-- Events for Proposal 5 (New IT infrastructure)
-- Majority in favour, 4 votes in favour, 1 against
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(5, 656, 'Michael Green', 1, 'In favour. We need to improve our IT systems to stay competitive.', '2024-07-17 11:35:14'),
(5, 4291, 'David Harris', 0, 'Against. We should consider alternatives before spending so much.', '2024-07-17 11:40:02'),
(5, 3570, 'Sophia Lewis', 1, 'In favour. Better IT infrastructure will boost efficiency.', '2024-07-17 11:45:10'),
(5, 797, 'Jane Smith', 1, 'In favour, this is essential for the long-term health of the company.', '2024-07-17 11:50:29'),
(5, 1980, 'George White', 1, 'In favour, this is an important investment in our future.', '2024-07-17 11:55:00'),
(5, 7654, 'Random User', 1, 'I strongly support this infrastructure upgrade. It is necessary for growth.', '2024-07-17 12:00:00');

-- Events for Proposal 6 (Renewable energy investment)
-- Majority in favour, 4 votes in favour, 2 against
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(6, 3570, 'Sophia Lewis', 1, 'In favour of renewable energy; its the future.', '2024-08-19 13:50:02'),
(6, 797, 'Jane Smith', 0, 'Against. I need more assurances on return on investment.', '2024-08-19 13:55:10'),
(6, 3135, 'Emily Brown', NULL, 'Im undecided. I need more information on the potential savings.', '2024-08-19 13:57:29'),
(6, 4291, 'David Harris', 1, 'In favour. We need to invest in sustainability and renewable energy.', '2024-08-19 13:59:00'),
(6, 1980, 'George White', 1, 'Im in favour. Renewable energy is the future.', '2024-08-19 14:05:25'),
(6, 1893, 'Random User', 1, 'I support this initiative, as it will help us reduce costs in the long run.', '2024-08-19 14:10:00');

-- Events for Proposal 7 (Employee wellness program)
-- Majority in favour, 3 votes in favour, 1 against
INSERT INTO event (proposal_id, author_id, author_name, decision, comment, created)
VALUES
(7, 277, 'John Doe', 1, 'In favour of the wellness program. Our employees need support.', '2024-02-28 17:10:10'),
(7, 4291, 'David Harris', NULL, 'I think we need to focus on the details of the program first.', '2024-02-28 17:15:22'),
(7, 1980, 'George White', 1, 'In favour of wellness initiatives. They will improve employee productivity.', '2024-02-28 17:20:50'),
(7, 7654, 'Random User', 1, 'I support the wellness program. It will benefit everyone in the long term.', '2024-02-28 17:25:30');

COMMIT;
