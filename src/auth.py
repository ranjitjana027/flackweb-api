import datetime
import functools
import re

import jwt
from flask import (
    Blueprint, request, session, current_app
)
from werkzeug.security import generate_password_hash

from .db import User

bp = Blueprint('auth', __name__)


def login_required(f):
    @functools.wraps(f)
    def decorator(*args, **kwargs):
        token = None
        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']

        if not token:
            return {
                'success': False,
                'message': 'valid token is missing'
            }
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.exists(user_id=data['user_id'])
        except:
            return {
                'success': False,
                'message': 'token is invalid'
            }
        return f(current_user, *args, **kwargs)

    return decorator


def get_token_user(token: str) -> 'User':
    try:
        data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        current_user = User.exists(user_id=data['user_id'])
        return current_user
    except:
        return None


@bp.route('/api/signup', methods=["POST"])
def signup_api():
    if 'user' in session:
        return {'success': False}

    username = request.form.get("username")
    password = request.form.get("password")
    display_name = request.form.get("display_name")
    emailPattern = re.compile("^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]+)*@([a-zA-Z][a-zA-Z0-9_]*)(\.[a-zA-Z0-9_]+)+$")
    try:
        if bool(emailPattern.match(username)):
            if username.lower() != 'admin' and User.query.filter_by(username=username).first() is None:
                user = User.create(username=username, password=generate_password_hash(password), display_name=display_name, verified=True)

                return {'success': True}

            return {'success': False}
    except:
        return {'success': False}


@bp.route('/api/login', methods=['POST', 'GET'])
def login_api():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.auth(username=username, password=password)
        if user is not None:
            token = jwt.encode({
                'user_id': user.user_id,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
            }, current_app.config['SECRET_KEY'], algorithm="HS256")
            return {
                'success': True,
                'user': {
                    'username': user.username,
                    'display_name': user.display_name
                },
                'token': token
            }

    return {'success': False}


@bp.route('/api/auth')
@login_required
def is_auth(current_user):
    if not current_user:
        return {'success': False}

    return {
        'success': True,
        'user': {
            'username': current_user.username,
            'display_name': current_user.display_name
        }
    }


# todo: remove this
@bp.route('/api/logout', methods=["POST"])
@login_required
def logout_api(current_user):
    return {'success': True}
