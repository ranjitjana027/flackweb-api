import os
import re
from flask import (
    Flask,
    session,
    request
)
from flask_session import Session
from flask_socketio import (
    SocketIO,
    emit,
    join_room,
    leave_room
)
from sqlalchemy import and_
from models import *

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")
if not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY is not set")
# Configuration for session

app.config["SESSION_PERMANENT"]=False
app.config["SESSION_TYPE"]='filesystem'
Session(app)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
socketio = SocketIO(app, cors_allowed_origins=['https://flackweb.netlify.app','https://ranjitjana027.github.io/flackweb-react/'])

# Configuartion for SQLAlchemy

app.config["SQLALCHEMY_DATABASE_URI"]= os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False

db.init_app(app)

# Event Handlers
@socketio.on("join all")
def on_join_all(data):
    user=User.exists(username=session.get("user"))
    if user is not None:
        for channel in user.channels:
            join_room(channel.id)
    print("socket connected")

@socketio.on("leave all")
def on_leave_all(data):
    user=User.exists(username=session.get("user"))
    if user is not None:
        for channel in user.channels:
            leave_room(channel.id)
    print("socket disconnected")

@socketio.on('join')
def on_join(data):
    print('join request') # debug
    username=session.get('user')
    user=User.exists(username=username)
    room=data.get('room')
    room_id=data.get('room_id')
    if user is not None and room_id is not None and room is not None:
        print(username,room, room_id)

        if user.verified and len(room)>0 and room!="undefined":
            print("socket connected") # Debug


            channel=Channel.exists(id=room_id)
            if not user.is_member(channel):

                if channel is None:
                    channel=Channel.create(id=room_id,title=room)

                member=Member.create(user_id=user.user_id,channel_id=channel.id)
                join_room(channel.id)
                data={'display_name':user.display_name, 'username':username, "room":channel.title}
                emit('join status', data, room=channel.id)
                print("joined successfully")


@socketio.on('leave')
def on_leave(data):
    username=session.get('user')
    room_id=data.get('room')
    user=User.exists(username=username)
    channel=Channel.exists(id=room_id)
    if user is not None and user.is_member(channel):
        member=Member.query.filter(and_(Member.user_id==user.user_id,
        Member.channel_id==channel.id  )).first()
        db.session.delete(member)
        db.session.commit()
        data = {'display_name':user.display_name, 'username':username, "room": channel.id}
        print("You left")
        emit('leave status', data, room=channel.id)
        leave_room(channel.id)
        print("status has been sent")


@socketio.on("send message")
def on_send_message(data):
    if 'user' in session:
        message=data["message"]
        username=session['user']
        room_id=data['room']
        channel=Channel.exists(id=room_id)
        user=User.exists(username=session['user'])
        print("Mesage received")
        if user is not None and channel is not None and user.is_member(channel):
            chat={}
            newMessage=Message.create(channel_id=channel.id,user_id=user.user_id,message=message)
            print("Debug: mesage will be sent")
            emit('receive message', newMessage.to_json(),room=room_id)
    else:
        raise ConnectionRefusedError


@app.route('/api/signup', methods=["POST"])
def signup_api():
    if 'user' in session:
        return {'success': False}

    username=request.form.get("username")
    password=request.form.get("password")
    display_name=request.form.get("display_name")
    emailPattern=re.compile("^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]+)*@([a-zA-Z][a-zA-Z0-9_]*)(\.[a-zA-Z0-9_]+)+$")
    try:
        if bool(emailPattern.match(username)):
            if username.lower()!='admin' and User.query.filter_by(username=username).first() is None:
                user=User.create(username=username,password=password,display_name=display_name,verified=True)

                return {'success': True}

            return {'success':False }
    except:
        return { 'success':False }

@app.route('/api/login',methods=['POST','GET'])
def login_api():
    if 'user' in session:
        return {
            'success': True,
            'user':{
                'username':session.get('user'),
                'display_name':session.get('display_name')
                }
            }

    if request.method=='POST':
        username=request.form.get("username")
        password=request.form.get("password")
        print(username, password) ## DEBUG
        user=User.auth(username=username, password=password)
        if user is not None:
            session['user']=user.username
            session['display_name']=user.display_name
            return {
                'success': True,
                'user':{
                    'username':user.username,
                    'display_name':user.display_name
                    }
                }

    return {'success': False}

@app.route('/api/logout', methods=["POST"])
def logout_api():
    session.clear()
    return {'success':True}


@app.route('/api/channel_list',methods=["POST"])
def channel_list():
    if 'user' in session:
        channels = User.get_channels(username=session['user'])
        channel_names = []
        for c in channels:
            channel_names.append(c.preview())
        if len(channel_names)==0:
            return {
            "success":False,
            'message': 'No Channel Found'
            }

        return {
            "success":True,
            "channels": channel_names
            }
    else:
        return { "success": False }


@app.route('/api/chats', methods=['POST'])
def chat():
    if 'user' in session:
        room=request.form.get("roomname")
        oldest=request.form.get("oldest")
        limit=request.form.get("limit")
        if limit is None:
            limit=50
        else:
            try:
                limit=int(limit)
            except:
                limit=50
        channel=Channel.exists(id=room)
        user=User.exists(session.get("user"))
        if channel is not None and user is not None and user.is_member(channel):
            messages=[]
            if oldest is None:
                messages=[m.to_json() for m in channel.messages[:limit]]
                return {
                    "success":True,
                    "message": messages
                }
            else:
                try:
                    oldest=int(oldest)
                    messages=[m.to_json() for m in channel.messages if m.id<oldest]
                    return {
                        "success":True,
                        "message": messages
                    }
                except:
                    return {
                        "success": False
                    }
        else:
            return {"success":False}
    else:
        return {"success":False}

@app.route('/api/channels/match_title', methods=['POST'])
def match_channel_title():
    if 'user' in session:
        title=request.form.get('title')
        if title is not None:
            return { 'success': True, **Channel.matches(title) }

    return { 'success': False }

def main():
    db.create_all()

if __name__ == '__main__':
    with app.app_context():
        main()
    socketio.run(app)
