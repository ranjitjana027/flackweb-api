from flask_socketio import SocketIO, join_room, leave_room, emit

from .auth import get_token_user
from .db import Channel, Member, Message, User

socketio = SocketIO(cors_allowed_origins='*')


# Event Handlers
@socketio.on("join all")
def on_join_all(data):
    current_user = get_token_user(data.get('token'))
    if current_user is not None:
        # user joins a channel same as his/her username
        join_room(current_user.username)
        for channel in current_user.channels:
            join_room(channel.id)
            print("joined", channel.id)
        print("socket connected")


@socketio.on("leave all")
def on_leave_all(data):
    current_user = get_token_user(data.get('token'))
    if current_user is not None:
        leave_room(current_user.username)
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
                emit('join status', data, to=channel.id)
                print("joined successfully")


@socketio.on('leave')
def on_leave(data):
    room_id = data.get('room')
    user = get_token_user(data.get('token'))
    channel = Channel.exists(id=room_id)
    if user is not None and user.is_member(channel):
        Member.leave_channel(user.user_id, channel.id)
        data = {'display_name': user.display_name, 'username': user.username, "room": channel.id}
        print("You left")
        emit('leave status', data, to=channel.id)
        leave_room(channel.id)
        print("status has been sent")


@socketio.on('initiate_dm')
def on_initiate_dm(data):
    print('join request')  # debug
    user = get_token_user(data.get('token'))
    room = data.get('room')
    # room_id = data.get('room_id')
    # if user is not None and room_id is not None and room is not None:
    #     print(user, room, room_id)
    #
    #     if user.verified and len(room) > 0 and room != "undefined":
    #         print("socket connected")  # Debug
    #         channel = Channel.exists(id=room_id)
    #         if not user.is_member(channel):
    #
    #             if channel is None:
    #                 channel = Channel.create(id=room_id, title=room)
    #
    #             member = Member.create(user_id=user.user_id, channel_id=channel.id)
    #             join_room(channel.id)
    #             data = {'display_name': user.display_name, 'username': user.username, "room": channel.title}
    #             emit('join status', data, to=channel.id)
    #             print("joined successfully")


@socketio.on("send message")
def on_send_message(data):
    current_user = get_token_user(data.get('token'))
    if current_user is not None:
        message = data.get("message", '')
        room_id = data.get('room')
        is_channel = data.get('isChannel')
        if not is_channel:
            channel = current_user.get_dm_channel(peer=room_id)
        else:
            channel = Channel.exists(id=room_id)
        print("Mesage received")
        if current_user is not None and channel is not None and message != '' and ((not is_channel and Connection.exists(current_user.user_id, room_id)) or current_user.is_member(channel)):
            new_message = Message.create(channel_id=channel.id, user_id=current_user.user_id, message=message)
            print("Debug: mesage will be sent")
            if is_channel:
                emit('receive message', new_message.to_json(), to=room_id)
            else:
                emit('receive_dm_message', new_message.to_user_json(username=room_id), to=room_id)
                emit('receive_dm_message', new_message.to_user_json(username=current_user.username), to=current_user.username)
    else:
        print(current_user)
        raise ConnectionRefusedError
