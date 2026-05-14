from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from .. import db
from ..auth import role_required

venues_bp = Blueprint("venues", __name__)

WRITE = ("admin", "organizer")


def _all_venues():
    return db.execute(
        """SELECT v.venue_id, v.name, v.city, v.country, v.capacity,
                  (SELECT COUNT(*) FROM matches m WHERE m.venue_id = v.venue_id) AS matches_hosted
             FROM venues v
            ORDER BY v.name""", fetch="all")


@venues_bp.route("/")
@login_required
def list_view():
    return render_template("venues/list.html", venues=_all_venues(),
                           venue=None, editing=False)


@venues_bp.route("/new", methods=["GET", "POST"])
@role_required(*WRITE)
def create():
    if request.method == "POST":
        try:
            db.execute(
                """INSERT INTO venues(name, city, country, capacity)
                   VALUES (%s,%s,%s,%s)""",
                (request.form["name"],
                 request.form["city"],
                 request.form.get("country") or "Turkey",
                 int(request.form["capacity"])),
                commit=True)
            flash("Venue added.", "success")
            return redirect(url_for("venues.list_view"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
    return render_template("venues/list.html", venues=_all_venues(),
                           venue=None, editing=True)


@venues_bp.route("/<int:vid>/edit", methods=["GET", "POST"])
@role_required(*WRITE)
def edit(vid):
    v = db.execute("SELECT * FROM venues WHERE venue_id=%s", (vid,), fetch="one")
    if not v:
        flash("Venue not found.", "danger")
        return redirect(url_for("venues.list_view"))
    if request.method == "POST":
        db.execute(
            """UPDATE venues SET name=%s, city=%s, country=%s, capacity=%s
                WHERE venue_id=%s""",
            (request.form["name"],
             request.form["city"],
             request.form.get("country") or "Turkey",
             int(request.form["capacity"]),
             vid),
            commit=True)
        flash("Venue updated.", "success")
        return redirect(url_for("venues.list_view"))
    return render_template("venues/list.html", venues=_all_venues(),
                           venue=v, editing=True)


@venues_bp.route("/<int:vid>/delete", methods=["POST"])
@role_required("admin")
def delete(vid):
    db.execute("DELETE FROM venues WHERE venue_id=%s", (vid,), commit=True)
    flash("Venue deleted.", "info")
    return redirect(url_for("venues.list_view"))
