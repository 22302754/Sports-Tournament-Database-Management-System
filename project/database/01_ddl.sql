-- =============================================================
-- Sports Tournament Management System - DDL
-- =============================================================

DROP TABLE IF EXISTS matches                  CASCADE;
DROP TABLE IF EXISTS tournament_registrations CASCADE;
DROP TABLE IF EXISTS tournaments              CASCADE;
DROP TABLE IF EXISTS players                  CASCADE;
DROP TABLE IF EXISTS teams                    CASCADE;
DROP TABLE IF EXISTS venues                   CASCADE;
DROP TABLE IF EXISTS sports                   CASCADE;
DROP TABLE IF EXISTS users                    CASCADE;
DROP TABLE IF EXISTS roles                    CASCADE;

-- 1) ROLES (user groups)
CREATE TABLE roles (
    role_id     SERIAL PRIMARY KEY,
    role_name   VARCHAR(30) NOT NULL UNIQUE,
    description VARCHAR(200) DEFAULT ''
);

-- 2) USERS (authentication)
CREATE TABLE users (
    user_id       SERIAL PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email         VARCHAR(120) NOT NULL UNIQUE,
    full_name     VARCHAR(120) NOT NULL,
    role_id       INTEGER      NOT NULL REFERENCES roles(role_id) ON DELETE RESTRICT,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3) SPORTS
CREATE TABLE sports (
    sport_id    SERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(200) DEFAULT ''
);

-- 4) VENUES
CREATE TABLE venues (
    venue_id   SERIAL PRIMARY KEY,
    name       VARCHAR(120) NOT NULL,
    city       VARCHAR(80)  NOT NULL,
    country    VARCHAR(60)  NOT NULL DEFAULT 'Turkey',
    capacity   INTEGER      NOT NULL CHECK (capacity > 0),
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, city)
);

-- 5) TEAMS
CREATE TABLE teams (
    team_id       SERIAL PRIMARY KEY,
    sport_id      INTEGER NOT NULL REFERENCES sports(sport_id) ON DELETE RESTRICT,
    coach_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    name          VARCHAR(100) NOT NULL,
    city          VARCHAR(80),
    founded_year  INTEGER CHECK (founded_year BETWEEN 1800 AND 2100),
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (sport_id, name)
);

-- 6) PLAYERS
CREATE TABLE players (
    player_id     SERIAL PRIMARY KEY,
    user_id       INTEGER UNIQUE REFERENCES users(user_id) ON DELETE SET NULL,
    team_id       INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    full_name     VARCHAR(120) NOT NULL,
    date_of_birth DATE NOT NULL,
    position      VARCHAR(40),
    jersey_number INTEGER CHECK (jersey_number BETWEEN 0 AND 999),
    nationality   VARCHAR(60),
    height_cm     INTEGER CHECK (height_cm BETWEEN 100 AND 250),
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (team_id, jersey_number)
);

-- 7) TOURNAMENTS
CREATE TABLE tournaments (
    tournament_id     SERIAL PRIMARY KEY,
    sport_id          INTEGER NOT NULL REFERENCES sports(sport_id) ON DELETE RESTRICT,
    organizer_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    name              VARCHAR(120) NOT NULL,
    season            VARCHAR(20)  NOT NULL DEFAULT '2025-26',
    start_date        DATE NOT NULL,
    end_date          DATE NOT NULL,
    location          VARCHAR(120),
    prize_pool        NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (prize_pool >= 0),
    status            VARCHAR(20)   NOT NULL DEFAULT 'Upcoming'
                      CHECK (status IN ('Upcoming','Ongoing','Completed','Cancelled')),
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_date >= start_date),
    UNIQUE (name, season)
);

-- 8) TOURNAMENT_REGISTRATIONS (junction: which teams entered which tournaments)
CREATE TABLE tournament_registrations (
    registration_id SERIAL PRIMARY KEY,
    tournament_id   INTEGER NOT NULL REFERENCES tournaments(tournament_id) ON DELETE CASCADE,
    team_id         INTEGER NOT NULL REFERENCES teams(team_id)             ON DELETE CASCADE,
    registered_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status          VARCHAR(20) NOT NULL DEFAULT 'Confirmed'
                    CHECK (status IN ('Pending','Confirmed','Withdrawn')),
    UNIQUE (tournament_id, team_id)
);

-- 9) MATCHES
CREATE TABLE matches (
    match_id        SERIAL PRIMARY KEY,
    tournament_id   INTEGER NOT NULL REFERENCES tournaments(tournament_id) ON DELETE CASCADE,
    home_team_id    INTEGER NOT NULL REFERENCES teams(team_id)  ON DELETE RESTRICT,
    away_team_id    INTEGER NOT NULL REFERENCES teams(team_id)  ON DELETE RESTRICT,
    venue_id        INTEGER REFERENCES venues(venue_id)         ON DELETE SET NULL,
    referee_user_id INTEGER REFERENCES users(user_id)           ON DELETE SET NULL,
    scheduled_at    TIMESTAMP NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'Scheduled'
                    CHECK (status IN ('Scheduled','Ongoing','Completed','Cancelled')),
    home_score      INTEGER CHECK (home_score IS NULL OR home_score >= 0),
    away_score      INTEGER CHECK (away_score IS NULL OR away_score >= 0),
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (home_team_id <> away_team_id),
    UNIQUE (venue_id, scheduled_at)
);

-- Indexes for common lookups
CREATE INDEX idx_matches_tournament ON matches(tournament_id);
CREATE INDEX idx_matches_date       ON matches(scheduled_at);
CREATE INDEX idx_players_team       ON players(team_id);
CREATE INDEX idx_regs_tournament    ON tournament_registrations(tournament_id);
