DROP TABLE IF EXISTS proposal;
DROP TABLE IF EXISTS user;

CREATE TABLE proposal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER NOT NULL, -- TODO: foreign key
    -- 0 = Executive committee (VV), 1 = General committee (SO), 2 = Cooperative directors (Představenstvo ID)
    type INTEGER NOT NULL DEFAULT 0,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    cost INTEGER,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    edited TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES user (id)
);

CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    -- 0 - root, 1-9 reserved, 10 - user
    role INTEGER NOT NULL DEFAULT 10,
    last_access TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE event (
    id INTEGER PRIMARY KEY,
    proposal_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    -- 0 = against, 1 = in favour
    decision INTEGER,
    comment TEXT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposal_id) REFERENCES proposal (id),
    FOREIGN KEY (user_id) REFERENCES user (id),
    -- It has to be one, or the other
    CHECK (decision IS NOT NULL or comment IS NOT NULL)
);
