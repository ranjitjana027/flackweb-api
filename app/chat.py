from flask_socketio import SocketIO, join_room, leave_room, emit
from sqlalchemy import and_

from app.auth import get_token_user
from .db import Channel, Member, db, Message

socketio = SocketIO(cors_allowed_origins='*')


# Event Handlers
@socketio.on("join all")
def on_join_all(data):
    current_user = get_token_user(data.get('token'))
    if current_user is not None:
        for channel in current_user.channels:
            join_room(channel.id)
        print("socket connected")


@socketio.on("leave all")
def on_leave_all(data):
    current_user = get_token_user(data.get('token'))
    if current_user is not None:
        for channel in current_user.channels:
            leave_room(channel.id)
            print("socket disconnected")


@socketio.on('join')
def on_join(data):
    print('join request')  # debug
    user = get_token_user(data.get('token'))
    room = data.get('room')
    room_id = data.get('room_id')
    if user is not None and room_id is not None and room is not None:
        print(user, room, room_id)

        if user.verified and len(room) > 0 and room != "undefined":
            print("socket connected")  # Debug
            channel = Channel.exists(id=room_id)
            if not user.is_member(channel):

                if channel is None:
                    channel = Channel.create(id=room_id, title=room)

                member = Member.create(user_id=user.user_id, channel_id=channel.id)
                join_room(channel.id)
                data = {'display_name': user.display_name, 'username': user.username, "room": channel.title}
                emit('join status', data, room=channel.id)
                print("joined successfully")


@socketio.on('leave')
def on_leave(data):
    room_id = data.get('room')
    user = get_token_user(data.get('token'))
    channel = Channel.exists(id=room_id)
    if user is not None and user.is_member(channel):
        # todo
        member = Member.query.filter(and_(Member.user_id == user.user_id,
                                          Member.channel_id == channel.id)).first()
        db.session.delete(member)
        db.session.commit()
        data = {'display_name': user.display_name, 'username': user.username, "room": channel.id}
        print("You left")
        emit('leave status', data, room=channel.id)
        leave_room(channel.id)
        print("status has been sent")


@socketio.on("send message")
def on_send_message(data):
    current_user = get_token_user(data.get('token'))
    if current_user is not None:
        message = data.get("message", '')
        room_id = data.get('room')
        channel = Channel.exists(id=room_id)
        print("Mesage received")
        if current_user is not None and channel is not None and message != '' and current_user.is_member(channel):
            chat = {}
            newMessage = Message.create(channel_id=channel.id, user_id=current_user.user_id, message=message)
            print("Debug: mesage will be sent")
            emit('receive message', newMessage.to_json(), room=room_id)
    else:
        print(current_user)
        raise ConnectionRefusedError
