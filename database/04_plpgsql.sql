-- =============================================================
-- Sports Tournament Management System - PL/pgSQL blocks (7)
--   1) FUNCTION  team_points(team_id, tournament_id)        -> INTEGER
--   2) PROCEDURE schedule_match(...)                         (slot & rules check)
--   3) TRIGGER   trg_match_autostatus    (BEFORE UPDATE, auto-complete)
--   4) FUNCTION  team_goals_for(team_id, tournament_id)     -> INTEGER
--   5) FUNCTION  player_age(player_id)                      -> INTEGER
--   6) PROCEDURE update_match_score(match_id, home, away)    (with validation)
--   7) TRIGGER   trg_validate_match_teams (BEFORE INS/UPD, same-sport check)
-- =============================================================

-- 1) FUNCTION --------------------------------------------------
-- Returns total points (3 = win, 1 = draw) a team has in a tournament.
CREATE OR REPLACE FUNCTION team_points(p_team_id INTEGER, p_tournament_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    v_points INTEGER := 0;
BEGIN
    SELECT COALESCE(SUM(
             CASE
               WHEN home_team_id = p_team_id AND home_score >  away_score THEN 3
               WHEN away_team_id = p_team_id AND away_score >  home_score THEN 3
               WHEN (home_team_id = p_team_id OR away_team_id = p_team_id)
                    AND home_score = away_score THEN 1
               ELSE 0
             END), 0)
      INTO v_points
      FROM matches
     WHERE tournament_id = p_tournament_id
       AND status = 'Completed'
       AND (home_team_id = p_team_id OR away_team_id = p_team_id);
    RETURN v_points;
END;
$$ LANGUAGE plpgsql;

-- 2) PROCEDURE -------------------------------------------------
-- Safely schedules a match after verifying:
--   * both teams are different
--   * the venue is free at that timestamp
CREATE OR REPLACE PROCEDURE schedule_match(
    p_tournament_id   INTEGER,
    p_home_team_id    INTEGER,
    p_away_team_id    INTEGER,
    p_venue_id        INTEGER,
    p_scheduled_at    TIMESTAMP,
    p_referee_user_id INTEGER DEFAULT NULL
) AS $$
DECLARE
    v_conflict INTEGER;
BEGIN
    IF p_home_team_id = p_away_team_id THEN
        RAISE EXCEPTION 'Home and away teams must be different';
    END IF;

    IF p_venue_id IS NOT NULL THEN
        SELECT COUNT(*) INTO v_conflict
          FROM matches
         WHERE venue_id     = p_venue_id
           AND scheduled_at = p_scheduled_at
           AND status <> 'Cancelled';
        IF v_conflict > 0 THEN
            RAISE EXCEPTION 'Venue % is already booked at %', p_venue_id, p_scheduled_at;
        END IF;
    END IF;

    INSERT INTO matches(tournament_id, home_team_id, away_team_id,
                        venue_id, referee_user_id, scheduled_at)
    VALUES (p_tournament_id, p_home_team_id, p_away_team_id,
            p_venue_id, p_referee_user_id, p_scheduled_at);
END;
$$ LANGUAGE plpgsql;

-- 3) TRIGGER ---------------------------------------------------
-- Auto-switch a match to 'Completed' when both scores have been entered.
CREATE OR REPLACE FUNCTION fn_match_autostatus() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.home_score IS NOT NULL
       AND NEW.away_score IS NOT NULL
       AND NEW.status IN ('Scheduled','Ongoing') THEN
        NEW.status := 'Completed';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_match_autostatus ON matches;
CREATE TRIGGER trg_match_autostatus
BEFORE UPDATE OF home_score, away_score ON matches
FOR EACH ROW EXECUTE FUNCTION fn_match_autostatus();

-- 4) FUNCTION --------------------------------------------------
-- Returns the total goals scored by a team across completed matches
-- of a given tournament.
CREATE OR REPLACE FUNCTION team_goals_for(p_team_id INTEGER, p_tournament_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    v_goals INTEGER := 0;
BEGIN
    SELECT COALESCE(SUM(
             CASE WHEN home_team_id = p_team_id THEN home_score
                  WHEN away_team_id = p_team_id THEN away_score
                  ELSE 0 END), 0)
      INTO v_goals
      FROM matches
     WHERE tournament_id = p_tournament_id
       AND status        = 'Completed'
       AND (home_team_id = p_team_id OR away_team_id = p_team_id);
    RETURN v_goals;
END;
$$ LANGUAGE plpgsql;

-- 5) FUNCTION --------------------------------------------------
-- Returns the current age (in whole years) of a player.
CREATE OR REPLACE FUNCTION player_age(p_player_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    v_dob  DATE;
    v_age  INTEGER;
BEGIN
    SELECT date_of_birth INTO v_dob
      FROM players WHERE player_id = p_player_id;
    IF v_dob IS NULL THEN
        RETURN NULL;
    END IF;
    v_age := EXTRACT(YEAR FROM AGE(CURRENT_DATE, v_dob))::INTEGER;
    RETURN v_age;
END;
$$ LANGUAGE plpgsql;

-- 6) PROCEDURE -------------------------------------------------
-- Records the final score of a match after validating that:
--   * the match exists
--   * neither score is negative
--   * the match is not Cancelled
CREATE OR REPLACE PROCEDURE update_match_score(
    p_match_id   INTEGER,
    p_home_score INTEGER,
    p_away_score INTEGER
) AS $$
DECLARE
    v_status VARCHAR;
BEGIN
    IF p_home_score < 0 OR p_away_score < 0 THEN
        RAISE EXCEPTION 'Scores cannot be negative';
    END IF;

    SELECT status INTO v_status FROM matches WHERE match_id = p_match_id;
    IF v_status IS NULL THEN
        RAISE EXCEPTION 'Match % does not exist', p_match_id;
    END IF;
    IF v_status = 'Cancelled' THEN
        RAISE EXCEPTION 'Cannot update score of a cancelled match';
    END IF;

    UPDATE matches
       SET home_score = p_home_score,
           away_score = p_away_score
     WHERE match_id  = p_match_id;
END;
$$ LANGUAGE plpgsql;

-- 7) TRIGGER ---------------------------------------------------
-- Ensures both teams of a match belong to the same sport as the tournament.
CREATE OR REPLACE FUNCTION fn_validate_match_teams() RETURNS TRIGGER AS $$
DECLARE
    v_tour_sport INTEGER;
    v_home_sport INTEGER;
    v_away_sport INTEGER;
BEGIN
    SELECT sport_id INTO v_tour_sport FROM tournaments WHERE tournament_id = NEW.tournament_id;
    SELECT sport_id INTO v_home_sport FROM teams       WHERE team_id       = NEW.home_team_id;
    SELECT sport_id INTO v_away_sport FROM teams       WHERE team_id       = NEW.away_team_id;

    IF v_home_sport <> v_tour_sport OR v_away_sport <> v_tour_sport THEN
        RAISE EXCEPTION 'Both teams must belong to the same sport as the tournament (sport_id %)', v_tour_sport;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_match_teams ON matches;
CREATE TRIGGER trg_validate_match_teams
BEFORE INSERT OR UPDATE OF tournament_id, home_team_id, away_team_id ON matches
FOR EACH ROW EXECUTE FUNCTION fn_validate_match_teams();
