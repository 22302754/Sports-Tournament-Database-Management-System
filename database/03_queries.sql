-- =============================================================
-- Sports Tournament Management System - Analytical Queries (7)
-- Demonstrates: JOINs, LEFT JOIN, subqueries, GROUP BY, HAVING,
--               ORDER BY, aggregates SUM / AVG / COUNT.
-- =============================================================

-- Q1 ----------------------------------------------------------
-- Top 10 scoring teams across all completed matches
-- (UNION ALL, GROUP BY, SUM, ORDER BY, LIMIT)
SELECT  t.name AS team,
        s.name AS sport,
        SUM(g.goals_for) AS goals_for
FROM (
        SELECT home_team_id AS team_id, home_score AS goals_for
          FROM matches WHERE status='Completed' AND home_score IS NOT NULL
        UNION ALL
        SELECT away_team_id, away_score
          FROM matches WHERE status='Completed' AND away_score IS NOT NULL
     ) g
JOIN    teams  t ON t.team_id  = g.team_id
JOIN    sports s ON s.sport_id = t.sport_id
GROUP BY t.name, s.name
ORDER BY goals_for DESC, team
LIMIT 10;

-- Q2 ----------------------------------------------------------
-- Standings of a given tournament: W / D / L / Pts for every team.
-- Uses UNION + GROUP BY aggregation with conditional SUM.
-- Replace :tid by the tournament id.
WITH results AS (
  SELECT home_team_id AS team_id,
         CASE WHEN home_score > away_score THEN 3
              WHEN home_score = away_score THEN 1
              ELSE 0 END AS pts,
         CASE WHEN home_score > away_score THEN 1 ELSE 0 END AS wins,
         CASE WHEN home_score = away_score THEN 1 ELSE 0 END AS draws,
         CASE WHEN home_score < away_score THEN 1 ELSE 0 END AS losses
    FROM matches
   WHERE status = 'Completed' AND tournament_id = 1
  UNION ALL
  SELECT away_team_id AS team_id,
         CASE WHEN away_score > home_score THEN 3
              WHEN away_score = home_score THEN 1
              ELSE 0 END AS pts,
         CASE WHEN away_score > home_score THEN 1 ELSE 0 END AS wins,
         CASE WHEN away_score = home_score THEN 1 ELSE 0 END AS draws,
         CASE WHEN away_score < home_score THEN 1 ELSE 0 END AS losses
    FROM matches
   WHERE status = 'Completed' AND tournament_id = 1
)
SELECT t.name AS team,
       SUM(r.wins)   AS wins,
       SUM(r.draws)  AS draws,
       SUM(r.losses) AS losses,
       SUM(r.pts)    AS points
  FROM results r JOIN teams t ON t.team_id = r.team_id
 GROUP BY t.name
 ORDER BY points DESC, wins DESC;

-- Q3 ----------------------------------------------------------
-- Venue utilization: matches hosted, by venue.
SELECT  v.name AS venue,
        v.city,
        COUNT(m.match_id) AS total_matches,
        SUM(CASE WHEN m.status = 'Completed' THEN 1 ELSE 0 END) AS completed,
        SUM(CASE WHEN m.status = 'Scheduled' THEN 1 ELSE 0 END) AS scheduled
FROM    venues v
LEFT JOIN matches m ON m.venue_id = v.venue_id
GROUP BY v.name, v.city
ORDER BY total_matches DESC;

-- Q4 ----------------------------------------------------------
-- Teams that have registered but have never played a match (LEFT JOIN / IS NULL).
SELECT  te.team_id, te.name, s.name AS sport
FROM    teams te
JOIN    sports s ON s.sport_id = te.sport_id
LEFT JOIN matches m
       ON m.home_team_id = te.team_id OR m.away_team_id = te.team_id
WHERE   m.match_id IS NULL;

-- Q5 ----------------------------------------------------------
-- Teams scoring strictly above the average goals-per-team (scalar subquery).
SELECT  t.name AS team, SUM(g.goals_for) AS goals
FROM (
        SELECT home_team_id AS team_id, home_score AS goals_for
          FROM matches WHERE status='Completed' AND home_score IS NOT NULL
        UNION ALL
        SELECT away_team_id, away_score
          FROM matches WHERE status='Completed' AND away_score IS NOT NULL
     ) g
JOIN    teams t ON t.team_id = g.team_id
GROUP BY t.name
HAVING  SUM(g.goals_for) > (
           SELECT AVG(goals_per_team)
             FROM (SELECT SUM(home_score+away_score) AS goals_per_team
                     FROM matches
                    WHERE status='Completed'
                    GROUP BY tournament_id) gt
        )
ORDER BY goals DESC;

-- Q6 ----------------------------------------------------------
-- Monthly match statistics for the past 12 months.
SELECT  TO_CHAR(date_trunc('month', scheduled_at), 'YYYY-MM') AS month,
        COUNT(*)                                              AS matches,
        SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END)   AS completed,
        SUM(CASE WHEN status='Cancelled' THEN 1 ELSE 0 END)   AS cancelled,
        COALESCE(SUM(home_score + away_score), 0)             AS total_goals
FROM    matches
WHERE   scheduled_at >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY date_trunc('month', scheduled_at)
ORDER BY month;

-- Q7 ----------------------------------------------------------
-- Referees with workload above the average (HAVING + subquery).
SELECT  u.full_name AS referee,
        COUNT(m.match_id) AS matches_officiated
FROM    users u
JOIN    matches m ON m.referee_user_id = u.user_id
GROUP BY u.full_name
HAVING  COUNT(m.match_id) >= (
          SELECT AVG(c) FROM (
              SELECT COUNT(*) AS c
                FROM matches
               WHERE referee_user_id IS NOT NULL
               GROUP BY referee_user_id) a
        )
ORDER BY matches_officiated DESC;
