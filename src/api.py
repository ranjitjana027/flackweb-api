from flask import (
    Blueprint,
    request
)

from .auth import login_required
from .db import Channel, User, Connection

bp = Blueprint('chat', __name__)


@bp.route('/api/channel_list', methods=["POST"])
@login_required
def channel_list(current_user):
    channels = current_user.channels
    channel_names = []
    for c in channels:
        channel_names.append(c.preview())
    return {
        "success": True,
        "channels": channel_names
    }


@bp.route('/api/chats', methods=['POST'])
@login_required
def chat(current_user):
    body = request.get_json()
    room = body.get("room")
    oldest = body.get("oldest")
    limit = body.get("limit")
    is_channel = body.get("isChannel") or False
    if limit is None:
        limit = 50
    else:
        try:
            limit = int(limit)
        except:
            limit = 50

    if not is_channel:
        return {
            "success": True,
            "messageList": [m.to_json() for m in current_user.get_dm_messages(peer=room)] # TODO: remove unnecessar details
        }
    channel = Channel.exists(id=room)
    user = current_user
    if channel is not None and user is not None and user.is_member(channel):
        messages = []
        if oldest is None:
            messages = [m.to_json() for m in channel.messages[:limit]]
            return {
                "success": True,
                "messageList": messages
            }
        else:
            try:
                oldest = int(oldest)
                messages = [m.to_json() for m in channel.messages if m.id < oldest]
                return {
                    "success": True,
                    "messageList": messages
                }
            except:
                return {
                    "success": False
                }
    else:
        return {"success": False}


@bp.route('/api/channels/match_title', methods=['POST'])
@login_required
def match_channel_title(current_user):
    try:
        title = request.form.get('title')
        if title is not None:
            return {'success': True, **Channel.matches(title)}
    except:
        return {'success': False}


@bp.route('/api/channels/match_id', methods=['POST'])
@login_required
def match_channel_id(current_user):
    try:
        id = request.form.get('id')
        print(id)
        if id is not None:
            return {'success': Channel.exists(id=id) is not None}
        else:
            return {'success': False}
    except:
        return {'success': False}


@bp.route('/api/users/find', methods=['POST'])
@login_required
def search_user(current_user):
    try:
        title = request.form.get('title')
        if title is not None:
            return {'success': True, **User.matches(title)}
    except:
        return {'success': False}


@bp.route('/api/demo', methods=['POST'])
@login_required
def demo(current_user):
    print(request.get_json())
    pass

@bp.route('/api/connections/list', methods=["GET"])
@login_required
def get_user_connections(current_user):
    connection_list = Connection.get_connection_list(user_id=current_user.user_id)
    return {
        'success': True,
        'connection_list': connection_list
    }

@bp.route('/api/connections/add', methods=["POST"])
@login_required
def add_connection(current_user):
    body = request.get_json()
    peer_username = body.get("peer")
    peer = User.exists(username=peer_username)
    if peer is not None and Connection().exists(user_id=current_user.user_id, peer_id=peer.user_id) is None:
        Connection.create_if_not_exists(user_id=current_user.user_id, peer_id=peer.user_id)
    return {'success': True}
