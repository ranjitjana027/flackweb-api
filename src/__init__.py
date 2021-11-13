import os

from flask import Flask
from flask_cors import CORS
from flask_session import Session

from .db import db


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    CORS(app, supports_credentials=True)
    # Check for environment variable
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set")
    if not os.getenv("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set")
    # Configuration for session

    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_TYPE"] = 'filesystem'
    Session(app)
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

    # Configuartion for SQLAlchemy

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL").replace('postgres://', 'postgresql://')
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # app.config.from_mapping(
    #     SECRET_KEY='dev',
    #     DATABASE=os.path.join(app.instance_path, 'app.sqlite'),
    # )

    db.init_app(app)

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

    # # a simple page that says hello
    # @app.route('/hello')
    # def hello():
    #     return 'Hello, World!'

    from . import auth
    app.register_blueprint(auth.bp)

    from . import api
    app.register_blueprint(api.bp)

    from .chat import socketio
    socketio.init_app(app)

    return app
