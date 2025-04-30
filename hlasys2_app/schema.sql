DROP TABLE IF EXISTS proposal;
DROP TABLE IF EXISTS user;

CREATE TABLE proposal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL,
    author_name TEXT NOT NULL,
    -- 0 = Executive committee (VV), 1 = General committee (SO), 2 = Cooperative board (Představenstvo Druzstva), 3 = Control Committee (Kontrolni Komise)
    type INTEGER NOT NULL DEFAULT 0,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    cost INTEGER,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    edited TIMESTAMP DEFAULT NULL
);

CREATE TABLE event (
    id INTEGER PRIMARY KEY,
    proposal_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    author_name TEXT NOT NULL,
    -- 0 = against, 1 = in favour
    decision INTEGER,
    comment TEXT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposal_id) REFERENCES proposal (id),
    -- It has to be one, or the other
    CHECK (decision IS NOT NULL or comment IS NOT NULL)
);
