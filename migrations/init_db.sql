-- init_db.sql (PostgreSQL)

CREATE TABLE IF NOT EXISTS chats (
    chat_id BIGINT PRIMARY KEY,
    rules_message_id BIGINT,
    non_bot_members INTEGER,
    bot_count INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS rules (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    text TEXT NOT NULL,
    created_at BIGINT NOT NULL,
    accepted_at BIGINT
);

CREATE TABLE IF NOT EXISTS votes (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    chat_id BIGINT NOT NULL,
    vote_message_id BIGINT,
    created_at BIGINT NOT NULL,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS vote_voters (
    vote_id INTEGER NOT NULL REFERENCES votes(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    username TEXT,
    display_name TEXT,
    choice TEXT NOT NULL,
    voted_at BIGINT NOT NULL,
    PRIMARY KEY (vote_id, user_id)
);
