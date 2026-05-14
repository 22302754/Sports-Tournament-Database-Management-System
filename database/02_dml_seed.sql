-- =============================================================
-- Sports Tournament Management System - DML / Seed Data
-- =============================================================

INSERT INTO roles (role_name, description) VALUES
 ('admin',     'System administrators with full access'),
 ('organizer', 'Create tournaments, schedule matches, assign referees'),
 ('coach',     'Manages a single team and its roster'),
 ('referee',   'Officiates matches and records results'),
 ('player',    'Player accounts (limited, own data only)');

INSERT INTO users (username, password_hash, email, full_name, role_id) VALUES
 ('admin',   'pbkdf2:sha256:600000$seed$ph', 'admin@tour.com',  'System Admin',    (SELECT role_id FROM roles WHERE role_name='admin')),
 ('org1',    'pbkdf2:sha256:600000$seed$ph', 'org1@tour.com',   'Olivia Turner',   (SELECT role_id FROM roles WHERE role_name='organizer')),
 ('coach_a', 'pbkdf2:sha256:600000$seed$ph', 'coacha@tour.com', 'Carlos Mendes',   (SELECT role_id FROM roles WHERE role_name='coach')),
 ('coach_b', 'pbkdf2:sha256:600000$seed$ph', 'coachb@tour.com', 'Bruno Silva',     (SELECT role_id FROM roles WHERE role_name='coach')),
 ('coach_c', 'pbkdf2:sha256:600000$seed$ph', 'coachc@tour.com', 'David Yilmaz',    (SELECT role_id FROM roles WHERE role_name='coach')),
 ('ref1',    'pbkdf2:sha256:600000$seed$ph', 'ref1@tour.com',   'Ruth Fischer',    (SELECT role_id FROM roles WHERE role_name='referee')),
 ('ref2',    'pbkdf2:sha256:600000$seed$ph', 'ref2@tour.com',   'Rafael Dominguez',(SELECT role_id FROM roles WHERE role_name='referee')),
 ('player1', 'pbkdf2:sha256:600000$seed$ph', 'p1@tour.com',     'Leo Martinez',    (SELECT role_id FROM roles WHERE role_name='player'));

INSERT INTO sports (name, description) VALUES
 ('Football',   '11-a-side association football'),
 ('Basketball', '5-a-side basketball'),
 ('Volleyball', '6-a-side volleyball'),
 ('Tennis',     'Singles and doubles tennis');

INSERT INTO venues (name, city, country, capacity) VALUES
 ('Olympic Stadium',     'Istanbul', 'Turkey', 75000),
 ('Seaside Arena',       'Izmir',    'Turkey', 18000),
 ('Central Sports Hall', 'Ankara',   'Turkey', 12000),
 ('Bosphorus Court',     'Istanbul', 'Turkey',  8000);

INSERT INTO teams (sport_id, coach_user_id, name, city, founded_year) VALUES
 ((SELECT sport_id FROM sports WHERE name='Football'),   (SELECT user_id FROM users WHERE username='coach_a'), 'Red Eagles',   'Istanbul', 1975),
 ((SELECT sport_id FROM sports WHERE name='Football'),   (SELECT user_id FROM users WHERE username='coach_b'), 'Blue Tigers',  'Ankara',   1982),
 ((SELECT sport_id FROM sports WHERE name='Football'),   (SELECT user_id FROM users WHERE username='coach_c'), 'Green Sharks', 'Izmir',    1990),
 ((SELECT sport_id FROM sports WHERE name='Basketball'), (SELECT user_id FROM users WHERE username='coach_a'), 'City Hoops',   'Istanbul', 2001);

INSERT INTO players (team_id, full_name, date_of_birth, position, jersey_number, nationality, height_cm) VALUES
 ((SELECT team_id FROM teams WHERE name='Red Eagles'),   'Leo Martinez',  '1998-03-12', 'Forward',     10, 'Spain',     182),
 ((SELECT team_id FROM teams WHERE name='Red Eagles'),   'Mark Keller',   '1996-07-04', 'Midfielder',   8, 'Germany',   178),
 ((SELECT team_id FROM teams WHERE name='Red Eagles'),   'Anton Petrov',  '1999-11-23', 'Goalkeeper',   1, 'Russia',    190),
 ((SELECT team_id FROM teams WHERE name='Blue Tigers'),  'Omar Hassan',   '1997-02-18', 'Forward',      9, 'Egypt',     180),
 ((SELECT team_id FROM teams WHERE name='Blue Tigers'),  'Kaan Demir',    '1995-05-30', 'Defender',     4, 'Turkey',    185),
 ((SELECT team_id FROM teams WHERE name='Green Sharks'), 'Diego Sanchez', '2000-09-09', 'Forward',     11, 'Argentina', 176);

INSERT INTO tournaments (sport_id, organizer_user_id, name, season,
                         start_date, end_date, location, prize_pool, status) VALUES
 ((SELECT sport_id FROM sports WHERE name='Football'),
  (SELECT user_id  FROM users  WHERE username='org1'),
  'National Football Cup', '2025-26',
  CURRENT_DATE - INTERVAL '30 day', CURRENT_DATE + INTERVAL '60 day',
  'Turkey', 250000, 'Ongoing'),
 ((SELECT sport_id FROM sports WHERE name='Basketball'),
  (SELECT user_id  FROM users  WHERE username='org1'),
  'Spring Basketball League', '2025-26',
  CURRENT_DATE + INTERVAL '15 day', CURRENT_DATE + INTERVAL '120 day',
  'Ankara', 75000, 'Upcoming');

INSERT INTO tournament_registrations (tournament_id, team_id, status) VALUES
 ((SELECT tournament_id FROM tournaments WHERE name='National Football Cup'),
  (SELECT team_id FROM teams WHERE name='Red Eagles'),   'Confirmed'),
 ((SELECT tournament_id FROM tournaments WHERE name='National Football Cup'),
  (SELECT team_id FROM teams WHERE name='Blue Tigers'),  'Confirmed'),
 ((SELECT tournament_id FROM tournaments WHERE name='National Football Cup'),
  (SELECT team_id FROM teams WHERE name='Green Sharks'), 'Confirmed'),
 ((SELECT tournament_id FROM tournaments WHERE name='Spring Basketball League'),
  (SELECT team_id FROM teams WHERE name='City Hoops'),   'Pending');

INSERT INTO matches (tournament_id, home_team_id, away_team_id, venue_id,
                     referee_user_id, scheduled_at, status, home_score, away_score) VALUES
 ((SELECT tournament_id FROM tournaments WHERE name='National Football Cup'),
  (SELECT team_id FROM teams  WHERE name='Red Eagles'),
  (SELECT team_id FROM teams  WHERE name='Blue Tigers'),
  (SELECT venue_id FROM venues WHERE name='Olympic Stadium'),
  (SELECT user_id  FROM users  WHERE username='ref1'),
  CURRENT_TIMESTAMP - INTERVAL '10 day', 'Completed', 3, 1),
 ((SELECT tournament_id FROM tournaments WHERE name='National Football Cup'),
  (SELECT team_id FROM teams  WHERE name='Blue Tigers'),
  (SELECT team_id FROM teams  WHERE name='Green Sharks'),
  (SELECT venue_id FROM venues WHERE name='Seaside Arena'),
  (SELECT user_id  FROM users  WHERE username='ref2'),
  CURRENT_TIMESTAMP - INTERVAL '3 day',  'Completed', 2, 2),
 ((SELECT tournament_id FROM tournaments WHERE name='National Football Cup'),
  (SELECT team_id FROM teams  WHERE name='Red Eagles'),
  (SELECT team_id FROM teams  WHERE name='Green Sharks'),
  (SELECT venue_id FROM venues WHERE name='Olympic Stadium'),
  (SELECT user_id  FROM users  WHERE username='ref1'),
  CURRENT_TIMESTAMP + INTERVAL '5 day',  'Scheduled', NULL, NULL);

-- Example UPDATE and DELETE
UPDATE matches SET status = 'Ongoing'
 WHERE scheduled_at BETWEEN CURRENT_TIMESTAMP AND CURRENT_TIMESTAMP + INTERVAL '1 hour';

DELETE FROM matches
 WHERE status = 'Cancelled' AND scheduled_at < CURRENT_DATE - INTERVAL '90 day';
