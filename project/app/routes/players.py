from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..auth import role_required

players_bp = Blueprint("players", __name__)

WRITE = ("admin", "organizer", "coach")


def _coach_team_id():
    row = db.execute(
        "SELECT team_id FROM teams WHERE coach_user_id=%s LIMIT 1",
        (current_user.id,), fetch="one")
    return row["team_id"] if row else -1


def _list_data():
    sql = """SELECT p.player_id, p.full_name, p.date_of_birth, p.position,
                    p.jersey_number, p.nationality, p.height_cm,
                    t.name AS team, t.team_id
               FROM players p
               JOIN teams   t ON t.team_id = p.team_id"""
    params = ()
    where = []

    if current_user.role == "coach":
        where.append("t.coach_user_id = %s")
        params = params + (current_user.id,)
        team_filter = ""
        teams = db.execute(
            "SELECT team_id, name FROM teams WHERE coach_user_id=%s ORDER BY name",
            (current_user.id,), fetch="all")
    else:
        team_filter = request.args.get("team_id", "")
        if team_filter:
            where.append("t.team_id = %s")
            params = params + (int(team_filter),)
        teams = db.execute("SELECT team_id, name FROM teams ORDER BY name", fetch="all")

    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY t.name, p.jersey_number"
    players = db.execute(sql, params, fetch="all")
    return players, teams, team_filter


def _form_teams():
    if current_user.role == "coach":
        return db.execute("SELECT team_id, name FROM teams WHERE coach_user_id=%s",
                          (current_user.id,), fetch="all")
    return db.execute("SELECT team_id, name FROM teams ORDER BY name", fetch="all")


def _render(player=None, editing=False):
    players, teams, team_filter = _list_data()
    return render_template("players/list.html", players=players, teams=teams,
                           team_filter=team_filter, player=player,
                           form_teams=_form_teams(), editing=editing)


@players_bp.route("/")
@login_required
def list_view():
    return _render()


@players_bp.route("/new", methods=["GET", "POST"])
@role_required(*WRITE)
def create():
    teams = _form_teams()
    if request.method == "POST":
        team_id = int(request.form["team_id"])
        if current_user.role == "coach" and team_id not in [t["team_id"] for t in teams]:
            flash("You can only add players to your own team.", "danger")
            return redirect(url_for("players.list_view"))
        try:
            db.execute(
                """INSERT INTO players(team_id,full_name,date_of_birth,position,
                                        jersey_number,nationality,height_cm)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (team_id,
                 request.form["full_name"],
                 request.form["date_of_birth"],
                 request.form.get("position"),
                 int(request.form["jersey_number"]) if request.form.get("jersey_number") else None,
                 request.form.get("nationality"),
                 int(request.form["height_cm"]) if request.form.get("height_cm") else None),
                commit=True)
            flash("Player added.", "success")
            return redirect(url_for("players.list_view"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
    return _render(player=None, editing=True)


def _can_manage_player(player):
    if current_user.role in ("admin", "organizer"):
        return True
    if current_user.role == "coach":
        return player["team_id"] == _coach_team_id()
    return False


@players_bp.route("/<int:pid>/edit", methods=["GET", "POST"])
@role_required(*WRITE)
def edit(pid):
    p = db.execute("SELECT * FROM players WHERE player_id=%s", (pid,), fetch="one")
    if not p:
        flash("Player not found.", "danger")
        return redirect(url_for("players.list_view"))
    if not _can_manage_player(p):
        flash("You can only edit players on your own team.", "danger")
        return redirect(url_for("players.list_view"))
    if request.method == "POST":
        db.execute(
            """UPDATE players SET team_id=%s, full_name=%s, date_of_birth=%s,
                       position=%s, jersey_number=%s, nationality=%s, height_cm=%s
                 WHERE player_id=%s""",
            (int(request.form["team_id"]),
             request.form["full_name"],
             request.form["date_of_birth"],
             request.form.get("position"),
             int(request.form["jersey_number"]) if request.form.get("jersey_number") else None,
             request.form.get("nationality"),
             int(request.form["height_cm"]) if request.form.get("height_cm") else None,
             pid),
            commit=True)
        flash("Player updated.", "success")
        return redirect(url_for("players.list_view"))
    return _render(player=p, editing=True)


@players_bp.route("/<int:pid>/delete", methods=["POST"])
@role_required(*WRITE)
def delete(pid):
    p = db.execute("SELECT * FROM players WHERE player_id=%s", (pid,), fetch="one")
    if not p or not _can_manage_player(p):
        flash("You cannot remove that player.", "danger")
        return redirect(url_for("players.list_view"))
    db.execute("DELETE FROM players WHERE player_id=%s", (pid,), commit=True)
    flash("Player removed.", "info")
    return redirect(url_for("players.list_view"))
