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

# Configuration for session

app.config["SESSION_PERMANENT"]=False
app.config["SESSION_TYPE"]='filesystem'
Session(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins='*') # need to update | security issue

# Configuartion for SQLAlchemy

app.config["SQLALCHEMY_DATABASE_URI"]= os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]=False

db.init_app(app)

# Event Handlers

@socketio.on('join')
def on_join(data):
    print('join request') # debug
    username=session.get('user')
    room=data.get('room')
    
    if 'user' in session and username is not None and room is not None:
        print(username,room)
        if User.query.filter_by(username=session['user']).first().verified and len(room)>0 and room!="undefined":
            print("socket connected")
            join_room(room)
            user_id=User.query.filter_by(username=username).first().user_id
            channel=Channel.query.filter_by(channel=room).first()
            if channel is None:
                channel=Channel.create(channel=room)
            channel_id=channel.id
            if Member.query.filter(and_(Member.user_id==user_id,Member.channel_id==channel_id)).first() is None:
                member=Member(user_id=user_id,channel_id=channel_id)
                db.session.add(member)
                db.session.commit()
                data={'display_name':User.query.filter_by(username=username).first().display_name, 'username':username, "room":room}
                emit('join status', data, room=room)


@socketio.on('leave')
def on_leave(data):
    username=session['user']
    room=data['room']
    if User.query.filter_by(username=username).first().verified and room in [c.channel for c in User.query.filter_by(username=session['user']).first().channels]:
        member=Member.query.filter(and_(Member.user_id==(User.query.filter_by(username=username).first().user_id),
        Member.channel_id==(Channel.query.filter_by(channel=room).first().id ) )).first()
        db.session.delete(member)
        db.session.commit()
        data = {'display_name':User.query.filter_by(username=session['user']).first().display_name, 'username':username, "room": room}
        print("You left")
        emit('leave status', data, room=room)
        leave_room(room)
        print("status has been sent")


@socketio.on("send message")
def on_send_message(data):
    if 'user' in session:
        message=data["message"]
        username=session['user']
        room=data['room']
        print("Mesage received")
        if User.query.filter_by(username=session['user']).first().verified and room in [c.channel for c in User.query.filter_by(username=session['user']).first().channels]:
            chat={}

            channel_id=Channel.query.filter_by(channel=data['room']).first().id
            user_id=User.query.filter_by(username=username).first().user_id
            newMessage=Message(channel_id=channel_id,user_id=user_id,message=message)
            db.session.add(newMessage)
            db.session.commit()
            chat={"message":newMessage.message,"user":User.query.get(newMessage.user_id).display_name, "room":Channel.query.get(newMessage.channel_id).channel,"time":newMessage.dttm.strftime("%I:%M %p") }
            print("Debug: mesage will be sent")
            join_room(room)
            emit('receive message', chat,room=room)


@app.route('/api/signup', methods=["POST"])
def signup():
    if 'user' in session:
        return {'success': False}        

    username=request.form.get("username")
    password=request.form.get("password")
    display_name=request.form.get("display_name")
    emailPattern=re.compile("^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z0-9_]+)*@([a-zA-Z][a-zA-Z0-9_]*)(\.[a-zA-Z0-9_]+)+$")
    try:
        if bool(emailPattern.match(username)):
            if username.lower()!='admin' and User.query.filter_by(username=username).first() is None:
                user=User(username=username,password=password,display_name=display_name,verified=True)
                db.session.add(user)
                db.session.commit()
                session['user']=username
                return {'success': True}
            else:
                return {'success': False}
        else:
            return {'success':False }
    except:
        return { 'success':False }

@app.route('/api/login',methods=['POST','GET'])
def login_api():
    if 'user' in session:
        return {
            'success': True, 
            'user':{
                'username':session['user'], 
                'display_name':session['display_name']
                }
            }

    if request.method=='POST':
        username=request.form.get("username")
        password=request.form.get("password")
        print(username, password)
        user=User.query.filter(and_(User.username==username,User.password==password)).first() 
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


@app.route('/channel_list',methods=["POST"])
def channel_list():
    if 'user' in session:
        channels = User.get_channels(username=session['user'])
        channel_names = []
        for c in channels:
            channel_names.append(c.channel)
        if len(channel_names)==0:
            return {"success":False}

        return {
            "success":True, 
            "channels": channel_names 
            }
    else:
        return { "success": False }


@app.route('/chats', methods=['POST'])
def chat():
    if 'user' in session:
        room=request.form.get("roomname")
        oldest=request.form.get("oldest")
        channel=Channel.exists(room)
        user=User.exists(session.get("user"))
        if channel is not None and user is not None and user.is_member(channel):
            messages=[]
            if oldest is None:
                for m in channel.messages:
                    messages.append({
                        "mid": m.id,
                        "message":m.message,
                        "user":m.user.display_name,
                        "room":m.channel.channel,
                        "time":m.dttm.strftime("%I:%M %p")
                        })
                return {
                    "success":True, 
                    "message": messages 
                    }  
            else:
                try:
                    oldest=int(oldest)
                    for m in channel.messages:
                        if m.id < oldest:
                            messages.append({
                                "mid": m.id,
                                "message":m.message,
                                "user":m.user.display_name,
                                "room":m.channel.channel,
                                "time":m.dttm.strftime("%I:%M %p")
                                })  
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


def main():
    db.create_all()

if __name__ == '__main__':
    with app.app_context():
        main()
    socketio.run(app)
