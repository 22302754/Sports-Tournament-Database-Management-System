from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..auth import role_required

matches_bp = Blueprint("matches", __name__)

WRITE = ("admin", "organizer")
SCORE = ("admin", "organizer", "referee")


def _all_matches():
    sql = """SELECT m.match_id, m.scheduled_at, m.status,
                    m.home_score, m.away_score,
                    ht.name AS home_team, at_.name AS away_team,
                    v.name  AS venue,
                    t.name  AS tournament,
                    COALESCE(u.full_name,'-') AS referee
               FROM matches m
               JOIN tournaments t  ON t.tournament_id = m.tournament_id
               JOIN teams       ht ON ht.team_id  = m.home_team_id
               JOIN teams      at_ ON at_.team_id = m.away_team_id
               LEFT JOIN venues v  ON v.venue_id  = m.venue_id
               LEFT JOIN users  u  ON u.user_id   = m.referee_user_id"""
    params = ()
    role = current_user.role
    if role == "coach":
        sql += " WHERE ht.coach_user_id=%s OR at_.coach_user_id=%s"
        params = (current_user.id, current_user.id)
    elif role == "referee":
        sql += " WHERE m.referee_user_id=%s"
        params = (current_user.id,)
    elif role == "player":
        sql += """ WHERE ht.team_id IN (SELECT team_id FROM players WHERE user_id=%s)
                      OR at_.team_id IN (SELECT team_id FROM players WHERE user_id=%s)"""
        params = (current_user.id, current_user.id)
    sql += " ORDER BY m.scheduled_at DESC"
    return db.execute(sql, params, fetch="all")


def _lookups():
    tournaments = db.execute(
        "SELECT tournament_id, name, sport_id FROM tournaments ORDER BY start_date DESC",
        fetch="all")
    teams    = db.execute("SELECT team_id, name, sport_id FROM teams ORDER BY name", fetch="all")
    venues   = db.execute("SELECT venue_id, name, city FROM venues ORDER BY name", fetch="all")
    referees = db.execute(
        """SELECT u.user_id, u.full_name FROM users u JOIN roles r ON r.role_id=u.role_id
            WHERE r.role_name IN ('referee','admin') ORDER BY u.full_name""", fetch="all")
    return tournaments, teams, venues, referees


def _render(match=None, editing=False):
    tournaments, teams, venues, referees = _lookups()
    return render_template("matches/list.html", matches=_all_matches(),
                           match=match, form_tournaments=tournaments,
                           form_teams=teams, form_venues=venues,
                           form_referees=referees, editing=editing)


@matches_bp.route("/")
@login_required
def list_view():
    return _render()


@matches_bp.route("/new", methods=["GET", "POST"])
@role_required(*WRITE)
def create():
    if request.method == "POST":
        try:
            db.execute(
                """INSERT INTO matches(tournament_id,home_team_id,away_team_id,
                             venue_id,referee_user_id,scheduled_at,status)
                   VALUES (%s,%s,%s,%s,%s,%s,'Scheduled')""",
                (int(request.form["tournament_id"]),
                 int(request.form["home_team_id"]),
                 int(request.form["away_team_id"]),
                 int(request.form["venue_id"]) if request.form.get("venue_id") else None,
                 int(request.form["referee_user_id"]) if request.form.get("referee_user_id") else None,
                 request.form["scheduled_at"]),
                commit=True)
            flash("Match scheduled.", "success")
            return redirect(url_for("matches.list_view"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
    return _render(match=None, editing=True)


@matches_bp.route("/<int:mid>/edit", methods=["GET", "POST"])
@role_required(*SCORE)
def edit(mid):
    m = db.execute("SELECT * FROM matches WHERE match_id=%s", (mid,), fetch="one")
    if not m:
        flash("Match not found.", "danger")
        return redirect(url_for("matches.list_view"))
    if current_user.role == "referee" and m["referee_user_id"] != current_user.id:
        flash("You can only edit matches you officiate.", "danger")
        return redirect(url_for("matches.list_view"))
    if request.method == "POST":
        db.execute(
            """UPDATE matches SET tournament_id=%s, home_team_id=%s, away_team_id=%s,
                      venue_id=%s, referee_user_id=%s, scheduled_at=%s,
                      status=%s, home_score=%s, away_score=%s
                WHERE match_id=%s""",
            (int(request.form["tournament_id"]),
             int(request.form["home_team_id"]),
             int(request.form["away_team_id"]),
             int(request.form["venue_id"]) if request.form.get("venue_id") else None,
             int(request.form["referee_user_id"]) if request.form.get("referee_user_id") else None,
             request.form["scheduled_at"],
             request.form["status"],
             int(request.form["home_score"]) if request.form.get("home_score") not in (None, "") else None,
             int(request.form["away_score"]) if request.form.get("away_score") not in (None, "") else None,
             mid),
            commit=True)
        flash("Match updated.", "success")
        return redirect(url_for("matches.list_view"))
    return _render(match=m, editing=True)


@matches_bp.route("/<int:mid>/delete", methods=["POST"])
@role_required("admin", "organizer")
def delete(mid):
    db.execute("DELETE FROM matches WHERE match_id=%s", (mid,), commit=True)
    flash("Match deleted.", "info")
    return redirect(url_for("matches.list_view"))
