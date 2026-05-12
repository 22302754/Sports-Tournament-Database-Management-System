-- SQLite-compatible schema (local demo) mirroring database/01_ddl.sql
-- Plus triggers that are the equivalents of the PL/pgSQL blocks.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS roles (
    role_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name   TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    full_name     TEXT NOT NULL,
    role_id       INTEGER NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(role_id)
);

CREATE TABLE IF NOT EXISTS sports (
    sport_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS venues (
    venue_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    city       TEXT NOT NULL,
    country    TEXT NOT NULL DEFAULT 'Turkey',
    capacity   INTEGER NOT NULL CHECK (capacity > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, city)
);

CREATE TABLE IF NOT EXISTS teams (
    team_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    sport_id      INTEGER NOT NULL,
    coach_user_id INTEGER,
    name          TEXT NOT NULL,
    city          TEXT,
    founded_year  INTEGER CHECK (founded_year BETWEEN 1800 AND 2100),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (sport_id, name),
    FOREIGN KEY (sport_id)      REFERENCES sports(sport_id),
    FOREIGN KEY (coach_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS players (
    player_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER UNIQUE,
    team_id       INTEGER NOT NULL,
    full_name     TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    position      TEXT,
    jersey_number INTEGER CHECK (jersey_number BETWEEN 0 AND 999),
    nationality   TEXT,
    height_cm     INTEGER CHECK (height_cm BETWEEN 100 AND 250),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (team_id, jersey_number),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tournaments (
    tournament_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    sport_id          INTEGER NOT NULL,
    organizer_user_id INTEGER,
    name              TEXT NOT NULL,
    season            TEXT NOT NULL DEFAULT '2025-26',
    start_date        TEXT NOT NULL,
    end_date          TEXT NOT NULL,
    location          TEXT,
    prize_pool        REAL NOT NULL DEFAULT 0 CHECK (prize_pool >= 0),
    status            TEXT NOT NULL DEFAULT 'Upcoming'
                      CHECK (status IN ('Upcoming','Ongoing','Completed','Cancelled')),
    created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_date >= start_date),
    UNIQUE (name, season),
    FOREIGN KEY (sport_id)          REFERENCES sports(sport_id),
    FOREIGN KEY (organizer_user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS tournament_registrations (
    registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id   INTEGER NOT NULL,
    team_id         INTEGER NOT NULL,
    registered_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          TEXT NOT NULL DEFAULT 'Confirmed'
                    CHECK (status IN ('Pending','Confirmed','Withdrawn')),
    UNIQUE (tournament_id, team_id),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id) ON DELETE CASCADE,
    FOREIGN KEY (team_id)       REFERENCES teams(team_id)             ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS matches (
    match_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id   INTEGER NOT NULL,
    home_team_id    INTEGER NOT NULL,
    away_team_id    INTEGER NOT NULL,
    venue_id        INTEGER,
    referee_user_id INTEGER,
    scheduled_at    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Scheduled'
                    CHECK (status IN ('Scheduled','Ongoing','Completed','Cancelled')),
    home_score      INTEGER CHECK (home_score IS NULL OR home_score >= 0),
    away_score      INTEGER CHECK (away_score IS NULL OR away_score >= 0),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (home_team_id <> away_team_id),
    UNIQUE (venue_id, scheduled_at),
    FOREIGN KEY (tournament_id)   REFERENCES tournaments(tournament_id) ON DELETE CASCADE,
    FOREIGN KEY (home_team_id)    REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id)    REFERENCES teams(team_id),
    FOREIGN KEY (venue_id)        REFERENCES venues(venue_id)           ON DELETE SET NULL,
    FOREIGN KEY (referee_user_id) REFERENCES users(user_id)             ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_matches_tournament ON matches(tournament_id);
CREATE INDEX IF NOT EXISTS idx_matches_date       ON matches(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_regs_tournament    ON tournament_registrations(tournament_id);

DROP TRIGGER IF EXISTS trg_match_autostatus;
CREATE TRIGGER trg_match_autostatus AFTER UPDATE OF home_score, away_score ON matches
WHEN NEW.home_score IS NOT NULL AND NEW.away_score IS NOT NULL
     AND NEW.status IN ('Scheduled','Ongoing')
BEGIN
    UPDATE matches SET status = 'Completed' WHERE match_id = NEW.match_id;
END;
