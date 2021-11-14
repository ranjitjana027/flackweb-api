import os

import sentry_sdk
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from sentry_sdk.integrations.flask import FlaskIntegration

from .db import db


def create_app(test_config=None):
    # create and configure the app
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0
    )
    app = Flask(__name__, instance_relative_config=True)
    CORS(app, supports_credentials=True)
    # Check for environment variable
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set")
    if not os.getenv("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set")

    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

    # Configuration for SQLAlchemy

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL").replace('postgres://', 'postgresql://')
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    migrate = Migrate()
    db.init_app(app)
    migrate.init_app(app, db)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import auth
    app.register_blueprint(auth.bp)

    from . import api
    app.register_blueprint(api.bp)

    from .chat import socketio
    socketio.init_app(app)

    return app
