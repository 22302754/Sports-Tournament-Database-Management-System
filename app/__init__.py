import os
from flask import Flask
from dotenv import load_dotenv
from flask_login import LoginManager

from . import db as db_module
from .auth import auth_bp, User

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"]   = os.getenv("FLASK_SECRET_KEY", "dev-secret")
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL", "")

    os.makedirs(app.instance_path, exist_ok=True)
    app.config["SQLITE_PATH"] = os.path.join(app.instance_path, "tournament.sqlite3")

    db_module.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def _load_user(user_id: str):
        return User.get(int(user_id))

    # Blueprints
    from .routes.dashboard   import dashboard_bp
    from .routes.tournaments import tournaments_bp
    from .routes.teams       import teams_bp
    from .routes.players     import players_bp
    from .routes.matches     import matches_bp
    from .routes.venues      import venues_bp
    from .routes.reports     import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tournaments_bp, url_prefix="/tournaments")
    app.register_blueprint(teams_bp,       url_prefix="/teams")
    app.register_blueprint(players_bp,     url_prefix="/players")
    app.register_blueprint(matches_bp,     url_prefix="/matches")
    app.register_blueprint(venues_bp,      url_prefix="/venues")
    app.register_blueprint(reports_bp,     url_prefix="/reports")

    return app
