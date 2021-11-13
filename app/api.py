from flask import (
    Blueprint,
    request
)

from app.auth import login_required
from .db import Channel

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
    room = request.form.get("roomname")
    oldest = request.form.get("oldest")
    limit = request.form.get("limit")
    if limit is None:
        limit = 50
    else:
        try:
            limit = int(limit)
        except:
            limit = 50
    channel = Channel.exists(id=room)
    user = current_user
    if channel is not None and user is not None and user.is_member(channel):
        messages = []
        if oldest is None:
            messages = [m.to_json() for m in channel.messages[:limit]]
            return {
                "success": True,
                "message": messages
            }
        else:
            try:
                oldest = int(oldest)
                messages = [m.to_json() for m in channel.messages if m.id < oldest]
                return {
                    "success": True,
                    "message": messages
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
