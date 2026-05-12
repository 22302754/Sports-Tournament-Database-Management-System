from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .. import db
from ..auth import role_required

teams_bp = Blueprint("teams", __name__)

WRITE = ("admin", "organizer", "coach")


def _all_teams():
    sql = """SELECT te.team_id, te.name, te.city, te.founded_year,
                    s.name AS sport,
                    COALESCE(u.full_name,'-') AS coach,
                    (SELECT COUNT(*) FROM players p WHERE p.team_id = te.team_id) AS player_count
               FROM teams te
               JOIN sports s    ON s.sport_id = te.sport_id
               LEFT JOIN users u ON u.user_id = te.coach_user_id"""
    params = ()
    if current_user.role == "coach":
        sql += " WHERE te.coach_user_id = %s"
        params = (current_user.id,)
    sql += " ORDER BY te.name"
    return db.execute(sql, params, fetch="all")


def _lookups():
    sports  = db.execute("SELECT sport_id, name FROM sports ORDER BY name", fetch="all")
    coaches = db.execute(
        """SELECT u.user_id, u.full_name FROM users u JOIN roles r ON r.role_id=u.role_id
            WHERE r.role_name IN ('coach','admin') ORDER BY u.full_name""",
        fetch="all")
    return sports, coaches


def _render(team=None, editing=False):
    sports, coaches = _lookups()
    return render_template("teams/list.html", teams=_all_teams(),
                           team=team, sports=sports, coaches=coaches,
                           editing=editing)


@teams_bp.route("/")
@login_required
def list_view():
    return _render()


@teams_bp.route("/new", methods=["GET", "POST"])
@role_required(*WRITE)
def create():
    if request.method == "POST":
        try:
            db.execute(
                """INSERT INTO teams(sport_id,coach_user_id,name,city,founded_year)
                   VALUES (%s,%s,%s,%s,%s)""",
                (int(request.form["sport_id"]),
                 int(request.form["coach_user_id"]) if request.form.get("coach_user_id") else None,
                 request.form["name"], request.form.get("city"),
                 int(request.form["founded_year"]) if request.form.get("founded_year") else None),
                commit=True)
            flash("Team created.", "success")
            return redirect(url_for("teams.list_view"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
    return _render(team=None, editing=True)


@teams_bp.route("/<int:team_id>/edit", methods=["GET", "POST"])
@role_required(*WRITE)
def edit(team_id):
    team = db.execute("SELECT * FROM teams WHERE team_id=%s", (team_id,), fetch="one")
    if not team:
        flash("Team not found.", "danger")
        return redirect(url_for("teams.list_view"))
    if current_user.role == "coach" and team["coach_user_id"] != current_user.id:
        flash("You can only edit your own team.", "danger")
        return redirect(url_for("teams.list_view"))
    if request.method == "POST":
        db.execute(
            """UPDATE teams SET sport_id=%s, coach_user_id=%s, name=%s,
                      city=%s, founded_year=%s
                WHERE team_id=%s""",
            (int(request.form["sport_id"]),
             int(request.form["coach_user_id"]) if request.form.get("coach_user_id") else None,
             request.form["name"], request.form.get("city"),
             int(request.form["founded_year"]) if request.form.get("founded_year") else None,
             team_id),
            commit=True)
        flash("Team updated.", "success")
        return redirect(url_for("teams.list_view"))
    return _render(team=team, editing=True)


@teams_bp.route("/<int:team_id>/delete", methods=["POST"])
@role_required("admin", "organizer")
def delete(team_id):
    db.execute("DELETE FROM teams WHERE team_id=%s", (team_id,), commit=True)
    flash("Team deleted.", "info")
    return redirect(url_for("teams.list_view"))
