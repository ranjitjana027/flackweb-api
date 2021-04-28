from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_

db=SQLAlchemy()

class BaseMixin(object):
    @classmethod
    def create(cls,**kwargs):
        obj=cls(**kwargs)
        db.session.add(obj)
        db.session.commit()
        return obj

class TimestampMixin(object):
    created=db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.current_timestamp())
    updated=db.Column(db.DateTime(timezone=True),onupdate=db.func.current_timestamp())


class User(BaseMixin, TimestampMixin, db.Model):
    __tablename__="users"
    user_id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String,unique=True, nullable=False) #Email ID
    password=db.Column(db.String,nullable=False)
    display_name=db.Column(db.String,nullable=False)
    verified=db.Column(db.Boolean,default=True)
    channels=db.relationship("Channel",secondary="members",backref=db.backref("users"))
    messages=db.relationship("Message",backref="user", lazy=True)

    def __repr__(self) -> str:
        return f"< {self.display_name} | {self.username} >"

    def is_member(self,channel:'Channel') -> bool:
        return channel in self.channels

    @classmethod
    def auth(cls, username : str, password : str) -> 'User':
        user=cls.query.filter(
            and_(cls.username==username,cls.password==password)
            ).first()
        return user

    @classmethod
    def exists(cls,username : str = None, user_id : int = None, display_name : str =None) -> 'User':
        if username is not None:
            return User.query.filter_by(username=username).first()
        elif user_id is not None:
            return User.query.filter_by(user_id=user_id).first()
        elif display_name is not None:
            return User.query.filter_by(display_name=display_name).first()
        else:
            return None

    @classmethod
    def get_channels(cls,username : str =None, user_id : int =None, display_name : str =None) -> list['Channel']:
        user =User.exists(username,user_id,display_name)
        if user is not None:
            return user.channels
        else:
            return []




class Member(BaseMixin, db.Model):
    __tablename__="members"
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("users.user_id"),nullable=False)
    channel_id=db.Column(db.String,db.ForeignKey("channels.id"),nullable=False)
    last_message_read=db.Column(db.Integer, db.ForeignKey("messages.id"), nullable=True)

    #user=db.relationship("User",backref=db.backref("members",cascade="all, delete-orphan"))
    #channel=db.relationship("Channel",backref=db.backref("members",cascade="all, delete-orphan"))


class Channel(BaseMixin, TimestampMixin, db.Model):
    __tablename__="channels"
    #username=db.Column(db.String,db.ForeignKey("users.username"),nullable=False)
    id=db.Column(db.String,primary_key=True) # channel id, public url
    title=db.Column(db.String, nullable=False) # change to title


    #users=db.relationship("User",secondary="members")

    messages=db.relationship('Message', backref="channel", lazy='dynamic', order_by="Message.dttm")

    def __repr__(self):
        return f"< {self.title} | {len(self.users)} Members >"

    def preview(self):
        last_message= None if self.messages.count()==0 else self.messages[-1]
        members_count=len(self.users)
        return {
        'channel_id':self.id,
        'channel_name': self.title,
        'last_message': None if last_message is None else last_message.to_json(),
        'members_count': members_count,
        'created_on': self.created
        }

    @classmethod
    def exists(cls,id:str=None, title: str=None) -> 'Channel':
        if id is not None:
            return Channel.query.get(id)
        return Channel.query.filter_by(title=title).first()

    @classmethod
    def matches(cls,title: str):
        channels=Channel.query.filter(Channel.title.ilike(f"%{title}%")).all()
        return {
            'title': title,
            'matches': [c.preview() for c in channels]
        }


class Message(BaseMixin, db.Model):
    __tablename__="messages"
    id=db.Column(db.Integer,primary_key=True)
    channel_id=db.Column(db.String,db.ForeignKey("channels.id"),nullable=True) # receiver channel
    user_id=db.Column(db.Integer,db.ForeignKey("users.user_id"),nullable=True)  # sender
    message=db.Column(db.String(255),nullable=False)
    dttm=db.Column(db.DateTime(timezone=True),server_default=db.func.current_timestamp())
    status=db.Column(db.Boolean,default=False)


    def __repr__(self):
        return f"< Message : {self.message}, Sender: {self.user}, Channel: {self.channel} >"

    def to_json(self):
        return {
        'mid':self.id,
        'room':self.channel.title,
        'room_id': self.channel_id,
        'user': self.user.display_name,
        'message': self.message,
        'dttm':self.dttm.__str__()
        }
