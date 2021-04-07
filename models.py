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

class User(BaseMixin, db.Model):
    __tablename__="users"
    user_id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String,unique=True, nullable=False) #add nullable=False
    password=db.Column(db.String,nullable=False)
    display_name=db.Column(db.String)
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
    channel_id=db.Column(db.Integer,db.ForeignKey("channels.id"),nullable=False)

    #user=db.relationship("User",backref=db.backref("members",cascade="all, delete-orphan"))
    #channel=db.relationship("Channel",backref=db.backref("members",cascade="all, delete-orphan"))


class Channel(BaseMixin, db.Model):
    __tablename__="channels"
    #username=db.Column(db.String,db.ForeignKey("users.username"),nullable=False)
    id=db.Column(db.Integer,primary_key=True)
    channel=db.Column(db.String, nullable=False)
    #users=db.relationship("User",secondary="members")

    messages=db.relationship('Message', backref="channel", lazy=True)

    def __repr__(self):
        return f"< {self.channel} | {len(self.users)} Members >"

    @classmethod
    def exists(cls, room: str) -> 'Channel':
        channel=Channel.query.filter_by(channel=room).first()
        return channel

class Message(BaseMixin, db.Model):
    __tablename__="messages"
    id=db.Column(db.Integer,primary_key=True)
    channel_id=db.Column(db.Integer,db.ForeignKey("channels.id"),nullable=False) # receiver
    user_id=db.Column(db.Integer,db.ForeignKey("users.user_id"),nullable=False)  # sender
    message=db.Column(db.String(255),nullable=False)
    dttm=db.Column(db.DateTime,server_default=db.func.current_timestamp())

    def __repr__(self):
        return f"< Message : {self.message}, Sender: {self.user}, Channel: {self.channel} >"

