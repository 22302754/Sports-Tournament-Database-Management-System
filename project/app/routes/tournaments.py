from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from .. import db
from ..auth import role_required

tournaments_bp = Blueprint("tournaments", __name__)

WRITE = ("admin", "organizer")


def _all_tournaments():
    return db.execute(
        """SELECT t.tournament_id, t.name, t.season, t.status,
                  t.start_date, t.end_date, t.prize_pool, t.location,
                  s.name AS sport,
                  COALESCE(u.full_name,'-') AS organizer
             FROM tournaments t
             JOIN sports s    ON s.sport_id = t.sport_id
             LEFT JOIN users u ON u.user_id = t.organizer_user_id
            ORDER BY t.start_date DESC""", fetch="all")


def _lookups():
    sports     = db.execute("SELECT sport_id, name FROM sports ORDER BY name", fetch="all")
    organizers = db.execute(
        """SELECT u.user_id, u.full_name FROM users u JOIN roles r ON r.role_id=u.role_id
            WHERE r.role_name IN ('organizer','admin') ORDER BY u.full_name""",
        fetch="all")
    return sports, organizers


def _render(tournament=None, editing=False):
    sports, organizers = _lookups()
    return render_template("tournaments/list.html",
                           tournaments=_all_tournaments(),
                           tournament=tournament, sports=sports,
                           organizers=organizers, editing=editing)


@tournaments_bp.route("/")
@login_required
def list_view():
    return _render()


@tournaments_bp.route("/new", methods=["GET", "POST"])
@role_required(*WRITE)
def create():
    if request.method == "POST":
        try:
            db.execute(
                """INSERT INTO tournaments(sport_id,organizer_user_id,name,season,
                         start_date,end_date,location,prize_pool,status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (int(request.form["sport_id"]),
                 int(request.form["organizer_user_id"]) if request.form.get("organizer_user_id") else None,
                 request.form["name"], request.form["season"],
                 request.form["start_date"], request.form["end_date"],
                 request.form.get("location"),
                 float(request.form.get("prize_pool") or 0),
                 request.form["status"]),
                commit=True)
            flash("Tournament created.", "success")
            return redirect(url_for("tournaments.list_view"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
    return _render(tournament=None, editing=True)


@tournaments_bp.route("/<int:tid>/edit", methods=["GET", "POST"])
@role_required(*WRITE)
def edit(tid):
    t = db.execute("SELECT * FROM tournaments WHERE tournament_id=%s", (tid,), fetch="one")
    if not t:
        flash("Tournament not found.", "danger")
        return redirect(url_for("tournaments.list_view"))
    if request.method == "POST":
        db.execute(
            """UPDATE tournaments SET sport_id=%s, organizer_user_id=%s, name=%s, season=%s,
                      start_date=%s, end_date=%s, location=%s, prize_pool=%s, status=%s
                WHERE tournament_id=%s""",
            (int(request.form["sport_id"]),
             int(request.form["organizer_user_id"]) if request.form.get("organizer_user_id") else None,
             request.form["name"], request.form["season"],
             request.form["start_date"], request.form["end_date"],
             request.form.get("location"),
             float(request.form.get("prize_pool") or 0),
             request.form["status"], tid),
            commit=True)
        flash("Tournament updated.", "success")
        return redirect(url_for("tournaments.list_view"))
    return _render(tournament=t, editing=True)


@tournaments_bp.route("/<int:tid>/delete", methods=["POST"])
@role_required("admin")
def delete(tid):
    db.execute("DELETE FROM tournaments WHERE tournament_id=%s", (tid,), commit=True)
    flash("Tournament deleted.", "info")
    return redirect(url_for("tournaments.list_view"))
