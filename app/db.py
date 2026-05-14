"""Dialect-neutral DB layer (SQLite by default, PostgreSQL when DATABASE_URL is set)."""
import os
import sqlite3
from contextlib import contextmanager
from flask import current_app, g
from werkzeug.security import generate_password_hash

try:
    import psycopg2
    import psycopg2.extras
    _HAS_PG = True
except Exception:
    _HAS_PG = False


def _is_postgres() -> bool:
    url = current_app.config.get("DATABASE_URL") or ""
    return url.startswith("postgres")


def get_conn():
    if "db_conn" in g:
        return g.db_conn
    if _is_postgres():
        if not _HAS_PG:
            raise RuntimeError("psycopg2 not installed; cannot use PostgreSQL")
        conn = psycopg2.connect(current_app.config["DATABASE_URL"])
        conn.autocommit = False
    else:
        conn = sqlite3.connect(current_app.config["SQLITE_PATH"])
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
    g.db_conn = conn
    return conn


def close_conn(_err=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


def _translate(sql: str) -> str:
    return sql if _is_postgres() else sql.replace("%s", "?")


def execute(sql: str, params: tuple = (), *, commit: bool = False, fetch: str = None):
    """Run a query. ``fetch`` can be None, "one", or "all"."""
    conn   = get_conn()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if _is_postgres() else conn.cursor()
    cursor.execute(_translate(sql), params)
    result = None
    if fetch == "one":
        row = cursor.fetchone()
        result = dict(row) if row is not None else None
    elif fetch == "all":
        rows = cursor.fetchall()
        result = [dict(r) for r in rows]
    if commit:
        conn.commit()
    cursor.close()
    return result


@contextmanager
def transaction():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_app(app):
    app.teardown_appcontext(close_conn)

    @app.before_request
    def _ensure_schema():
        if app.config.get("_schema_ready"):
            return
        with app.app_context():
            _create_schema()
            _seed_if_empty()
        app.config["_schema_ready"] = True


def _create_schema():
    if _is_postgres():
        for fname in ("01_ddl.sql", "04_plpgsql.sql"):
            path = os.path.join(os.path.dirname(__file__), "..", "database", fname)
            with open(path, "r", encoding="utf-8") as f:
                get_conn().cursor().execute(f.read())
        get_conn().commit()
    else:
        path = os.path.join(os.path.dirname(__file__), "..", "database", "schema_sqlite.sql")
        with open(path, "r", encoding="utf-8") as f:
            get_conn().executescript(f.read())
        get_conn().commit()


def _seed_if_empty():
    row = execute("SELECT COUNT(*) AS n FROM users", fetch="one")
    if row and row["n"] > 0:
        return

    roles = [
        ("admin",     "System administrators with full access"),
        ("organizer", "Create tournaments, schedule matches, assign referees"),
        ("coach",     "Manages a single team and its roster"),
        ("referee",   "Officiates matches and records results"),
        ("player",    "Player accounts (limited, own data only)"),
    ]
    for r in roles:
        execute("INSERT INTO roles(role_name, description) VALUES (%s, %s)", r)

    def role_id(n):
        return execute("SELECT role_id FROM roles WHERE role_name=%s",
                       (n,), fetch="one")["role_id"]

    pw = generate_password_hash("pass123")
    users = [
        ("admin",   pw, "admin@tour.com",  "System Admin",     role_id("admin")),
        ("org1",    pw, "org1@tour.com",   "Olivia Turner",    role_id("organizer")),
        ("coach_a", pw, "coacha@tour.com", "Carlos Mendes",    role_id("coach")),
        ("coach_b", pw, "coachb@tour.com", "Bruno Silva",      role_id("coach")),
        ("coach_c", pw, "coachc@tour.com", "David Yilmaz",     role_id("coach")),
        ("ref1",    pw, "ref1@tour.com",   "Ruth Fischer",     role_id("referee")),
        ("ref2",    pw, "ref2@tour.com",   "Rafael Dominguez", role_id("referee")),
        ("player1", pw, "p1@tour.com",     "Leo Martinez",     role_id("player")),
    ]
    for u in users:
        execute("INSERT INTO users(username,password_hash,email,full_name,role_id) "
                "VALUES (%s,%s,%s,%s,%s)", u)

    for s in [("Football",   "11-a-side association football"),
              ("Basketball", "5-a-side basketball"),
              ("Volleyball", "6-a-side volleyball"),
              ("Tennis",     "Singles and doubles tennis")]:
        execute("INSERT INTO sports(name, description) VALUES (%s,%s)", s)

    for v in [("Olympic Stadium",     "Istanbul", "Turkey", 75000),
              ("Seaside Arena",       "Izmir",    "Turkey", 18000),
              ("Central Sports Hall", "Ankara",   "Turkey", 12000),
              ("Bosphorus Court",     "Istanbul", "Turkey",  8000)]:
        execute("INSERT INTO venues(name,city,country,capacity) VALUES (%s,%s,%s,%s)", v)

    def uid(u):  return execute("SELECT user_id  FROM users  WHERE username=%s", (u,), fetch="one")["user_id"]
    def sid(n):  return execute("SELECT sport_id FROM sports WHERE name=%s",     (n,), fetch="one")["sport_id"]
    def vid(n):  return execute("SELECT venue_id FROM venues WHERE name=%s",     (n,), fetch="one")["venue_id"]

    for t in [(sid("Football"),   uid("coach_a"), "Red Eagles",   "Istanbul", 1975),
              (sid("Football"),   uid("coach_b"), "Blue Tigers",  "Ankara",   1982),
              (sid("Football"),   uid("coach_c"), "Green Sharks", "Izmir",    1990),
              (sid("Basketball"), uid("coach_a"), "City Hoops",   "Istanbul", 2001)]:
        execute("INSERT INTO teams(sport_id,coach_user_id,name,city,founded_year) "
                "VALUES (%s,%s,%s,%s,%s)", t)

    def tid(n): return execute("SELECT team_id FROM teams WHERE name=%s", (n,), fetch="one")["team_id"]

    for p in [(tid("Red Eagles"),   uid("player1"), "Leo Martinez",  "1998-03-12", "Forward",    10, "Spain",     182),
              (tid("Red Eagles"),   None,           "Mark Keller",   "1996-07-04", "Midfielder",  8, "Germany",   178),
              (tid("Red Eagles"),   None,           "Anton Petrov",  "1999-11-23", "Goalkeeper",  1, "Russia",    190),
              (tid("Blue Tigers"),  None,           "Omar Hassan",   "1997-02-18", "Forward",     9, "Egypt",     180),
              (tid("Blue Tigers"),  None,           "Kaan Demir",    "1995-05-30", "Defender",    4, "Turkey",    185),
              (tid("Green Sharks"), None,           "Diego Sanchez", "2000-09-09", "Forward",    11, "Argentina", 176)]:
        execute("INSERT INTO players(team_id,user_id,full_name,date_of_birth,position,"
                "jersey_number,nationality,height_cm) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", p)

    from datetime import date, timedelta, datetime
    today = date.today()
    execute("INSERT INTO tournaments(sport_id,organizer_user_id,name,season,"
            "start_date,end_date,location,prize_pool,status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (sid("Football"), uid("org1"), "National Football Cup", "2025-26",
             (today - timedelta(days=30)).isoformat(),
             (today + timedelta(days=60)).isoformat(),
             "Turkey", 250000, "Ongoing"))
    execute("INSERT INTO tournaments(sport_id,organizer_user_id,name,season,"
            "start_date,end_date,location,prize_pool,status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (sid("Basketball"), uid("org1"), "Spring Basketball League", "2025-26",
             (today + timedelta(days=15)).isoformat(),
             (today + timedelta(days=120)).isoformat(),
             "Ankara", 75000, "Upcoming"))

    cup_id = execute("SELECT tournament_id FROM tournaments WHERE name='National Football Cup'",
                     fetch="one")["tournament_id"]
    bball_id = execute("SELECT tournament_id FROM tournaments WHERE name='Spring Basketball League'",
                       fetch="one")["tournament_id"]

    for reg in [(cup_id,   tid("Red Eagles"),   "Confirmed"),
                (cup_id,   tid("Blue Tigers"),  "Confirmed"),
                (cup_id,   tid("Green Sharks"), "Confirmed"),
                (bball_id, tid("City Hoops"),   "Pending")]:
        execute("INSERT INTO tournament_registrations(tournament_id,team_id,status) "
                "VALUES (%s,%s,%s)", reg)

    now = datetime.now()
    def fmt(dt): return dt.strftime("%Y-%m-%d %H:%M:%S")
    matches = [
        (cup_id, tid("Red Eagles"),  tid("Blue Tigers"),  vid("Olympic Stadium"),
         uid("ref1"), fmt(now - timedelta(days=10)), "Completed", 3, 1),
        (cup_id, tid("Blue Tigers"), tid("Green Sharks"), vid("Seaside Arena"),
         uid("ref2"), fmt(now - timedelta(days=3)),  "Completed", 2, 2),
        (cup_id, tid("Red Eagles"),  tid("Green Sharks"), vid("Olympic Stadium"),
         uid("ref1"), fmt(now + timedelta(days=5)),  "Scheduled", None, None),
    ]
    for m in matches:
        execute("INSERT INTO matches(tournament_id,home_team_id,away_team_id,venue_id,"
                "referee_user_id,scheduled_at,status,home_score,away_score) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", m)

    get_conn().commit()
