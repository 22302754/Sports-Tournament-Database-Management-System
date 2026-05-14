from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from .. import db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def home():
    return redirect(url_for("dashboard.index"))


@dashboard_bp.route("/dashboard")
@login_required
def index():
    role = current_user.role

    if role in ("admin", "organizer"):
        stats = {
            "tournaments": db.execute("SELECT COUNT(*) AS n FROM tournaments", fetch="one")["n"],
            "teams":       db.execute("SELECT COUNT(*) AS n FROM teams",       fetch="one")["n"],
            "players":     db.execute("SELECT COUNT(*) AS n FROM players",     fetch="one")["n"],
            "upcoming":    db.execute(
                "SELECT COUNT(*) AS n FROM matches "
                "WHERE status='Scheduled' AND scheduled_at >= CURRENT_TIMESTAMP",
                fetch="one")["n"],
        }
        upcoming_matches = db.execute(
            """SELECT m.match_id, m.scheduled_at,
                      ht.name AS home_team, at_.name AS away_team,
                      v.name  AS venue, t.name AS tournament
                 FROM matches m
                 JOIN teams       ht  ON ht.team_id   = m.home_team_id
                 JOIN teams       at_ ON at_.team_id  = m.away_team_id
                 LEFT JOIN venues v   ON v.venue_id   = m.venue_id
                 JOIN tournaments t   ON t.tournament_id = m.tournament_id
                WHERE m.status = 'Scheduled'
                ORDER BY m.scheduled_at
                LIMIT 5""", fetch="all")

    elif role == "coach":
        team = db.execute(
            "SELECT team_id, name FROM teams WHERE coach_user_id=%s LIMIT 1",
            (current_user.id,), fetch="one")
        team_id = team["team_id"] if team else -1
        stats = {
            "tournaments": db.execute(
                """SELECT COUNT(DISTINCT tournament_id) AS n FROM matches
                    WHERE home_team_id=%s OR away_team_id=%s""",
                (team_id, team_id), fetch="one")["n"],
            "teams":       1 if team else 0,
            "players":     db.execute("SELECT COUNT(*) AS n FROM players WHERE team_id=%s",
                                      (team_id,), fetch="one")["n"],
            "upcoming":    db.execute(
                """SELECT COUNT(*) AS n FROM matches
                    WHERE status='Scheduled' AND scheduled_at >= CURRENT_TIMESTAMP
                      AND (home_team_id=%s OR away_team_id=%s)""",
                (team_id, team_id), fetch="one")["n"],
        }
        upcoming_matches = db.execute(
            """SELECT m.match_id, m.scheduled_at,
                      ht.name AS home_team, at_.name AS away_team,
                      v.name  AS venue, t.name AS tournament
                 FROM matches m
                 JOIN teams       ht  ON ht.team_id   = m.home_team_id
                 JOIN teams       at_ ON at_.team_id  = m.away_team_id
                 LEFT JOIN venues v   ON v.venue_id   = m.venue_id
                 JOIN tournaments t   ON t.tournament_id = m.tournament_id
                WHERE m.status='Scheduled'
                  AND (m.home_team_id=%s OR m.away_team_id=%s)
                ORDER BY m.scheduled_at LIMIT 5""",
            (team_id, team_id), fetch="all")

    elif role == "referee":
        stats = {
            "tournaments": db.execute(
                """SELECT COUNT(DISTINCT tournament_id) AS n FROM matches
                    WHERE referee_user_id=%s""",
                (current_user.id,), fetch="one")["n"],
            "teams":       0,
            "players":     0,
            "upcoming":    db.execute(
                """SELECT COUNT(*) AS n FROM matches
                    WHERE referee_user_id=%s AND status='Scheduled'
                      AND scheduled_at >= CURRENT_TIMESTAMP""",
                (current_user.id,), fetch="one")["n"],
        }
        upcoming_matches = db.execute(
            """SELECT m.match_id, m.scheduled_at,
                      ht.name AS home_team, at_.name AS away_team,
                      v.name  AS venue, t.name AS tournament
                 FROM matches m
                 JOIN teams       ht  ON ht.team_id   = m.home_team_id
                 JOIN teams       at_ ON at_.team_id  = m.away_team_id
                 LEFT JOIN venues v   ON v.venue_id   = m.venue_id
                 JOIN tournaments t   ON t.tournament_id = m.tournament_id
                WHERE m.referee_user_id=%s AND m.status='Scheduled'
                ORDER BY m.scheduled_at LIMIT 5""",
            (current_user.id,), fetch="all")

    else:
        player = db.execute(
            "SELECT team_id FROM players WHERE user_id=%s", (current_user.id,), fetch="one")
        team_id = player["team_id"] if player else -1
        stats = {
            "tournaments": db.execute(
                """SELECT COUNT(DISTINCT tournament_id) AS n FROM matches
                    WHERE home_team_id=%s OR away_team_id=%s""",
                (team_id, team_id), fetch="one")["n"],
            "teams":       1 if player else 0,
            "players":     db.execute("SELECT COUNT(*) AS n FROM players WHERE team_id=%s",
                                      (team_id,), fetch="one")["n"],
            "upcoming":    db.execute(
                """SELECT COUNT(*) AS n FROM matches
                    WHERE status='Scheduled' AND scheduled_at >= CURRENT_TIMESTAMP
                      AND (home_team_id=%s OR away_team_id=%s)""",
                (team_id, team_id), fetch="one")["n"],
        }
        upcoming_matches = db.execute(
            """SELECT m.match_id, m.scheduled_at,
                      ht.name AS home_team, at_.name AS away_team,
                      v.name  AS venue, t.name AS tournament
                 FROM matches m
                 JOIN teams       ht  ON ht.team_id   = m.home_team_id
                 JOIN teams       at_ ON at_.team_id  = m.away_team_id
                 LEFT JOIN venues v   ON v.venue_id   = m.venue_id
                 JOIN tournaments t   ON t.tournament_id = m.tournament_id
                WHERE m.status='Scheduled'
                  AND (m.home_team_id=%s OR m.away_team_id=%s)
                ORDER BY m.scheduled_at LIMIT 5""",
            (team_id, team_id), fetch="all")

    return render_template("dashboard.html", stats=stats,
                           upcoming_matches=upcoming_matches)
