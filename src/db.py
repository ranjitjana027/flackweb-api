from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, or_
from werkzeug.security import check_password_hash

db = SQLAlchemy()


class BaseMixin(object):
    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        db.session.add(obj)
        db.session.commit()
        return obj


class TimestampMixin(object):
    created = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.current_timestamp())
    updated = db.Column(db.DateTime(timezone=True), onupdate=db.func.current_timestamp())


class User(BaseMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)  # Email ID
    password = db.Column(db.String, nullable=False)
    display_name = db.Column(db.String, nullable=False)
    verified = db.Column(db.Boolean, default=True)
    channels = db.relationship("Channel", secondary="members", backref=db.backref("users"))
    messages = db.relationship("Message", backref="user", lazy=True)

    def __repr__(self) -> str:
        return f"< {self.display_name} | {self.username} >"

    def is_member(self, channel: 'Channel') -> bool:
        return channel in self.channels

    def preview(self):
        return {
            'username': self.username,
            'display_name': self.display_name
        }

    def get_dm_channel(self, peer: str) -> 'Channel':
        # TODO: expand to multiple user
        user = User.exists(username=peer)
        # TODO: use better hashing mechnaism
        channel_id = f"{self.username}_{user.username}" if self.username < user.username else f"{user.username}_{self.username}"
        channel = Channel.exists(id=channel_id)
        if channel is None:
            channel_name = f"{self.display_name}_{user.display_name}" if self.username < user.username else f"{user.display_name}_{self.display_name}"
            channel = Channel.create(id=channel_id, title=channel_name, is_channel=False)
        return channel

    def get_dm_messages(self, peer: str):
        dm_channel = self.get_dm_channel(peer)
        return dm_channel.messages

    @classmethod
    def auth(cls, username: str, password: str) -> 'User':
        user = cls.query.filter_by(username=username).first()
        if (user is not None) and (check_password_hash(user.password, password)):
            return user
        return None

    @classmethod
    def exists(cls, username: str = None, user_id: int = None, display_name: str = None) -> 'User':
        if username is not None:
            return User.query.filter_by(username=username).first()
        elif user_id is not None:
            return User.query.filter_by(user_id=user_id).first()
        elif display_name is not None:
            return User.query.filter_by(display_name=display_name).first()
        else:
            return None

    @classmethod
    def get_channels(cls, username: str = None, user_id: int = None, display_name: str = None):
        user = User.exists(username, user_id, display_name)
        if user is not None:
            return user.channels
        else:
            return []

    @classmethod
    def matches(cls, title: str):
        users = cls.query.filter(or_(cls.username.ilike(f"%{title}%"), cls.display_name.ilike(f"%{title}%"))).all()
        return {
            'title': title,
            'matches': [c.preview() for c in users]
        }


class Member(BaseMixin, db.Model):
    __tablename__ = "members"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    channel_id = db.Column(db.String, db.ForeignKey("channels.id"), nullable=False)
    last_message_read = db.Column(db.Integer, db.ForeignKey("messages.id"), nullable=True)

    # user=db.relationship("User",backref=db.backref("members",cascade="all, delete-orphan"))
    # channel=db.relationship("Channel",backref=db.backref("members",cascade="all, delete-orphan"))

    @classmethod
    def leave_channel(cls, user_id: int, channel_id: str):
        member = cls.query.filter(and_(cls.user_id == user_id, cls.channel_id == channel_id)).first()
        db.session.delete(member)
        db.session.commit()


class Channel(BaseMixin, TimestampMixin, db.Model):
    __tablename__ = "channels"
    id = db.Column(db.String, primary_key=True)  # channel id, public url
    title = db.Column(db.String, nullable=False)  # change to title
    is_channel = db.Column(db.Boolean, default=True)

    # users=db.relationship("User",secondary="members")

    messages = db.relationship('Message', backref="channel", lazy='dynamic', order_by="Message.dttm")

    def __repr__(self):
        return f"< {self.title} | {len(self.users)} Members >"

    def preview(self):
        last_message = None if self.messages.count() == 0 else self.messages[-1]
        members = list(map(lambda user: user.preview(), self.users))
        members_count = len(members)
        return {
            'channel_id': self.id,
            'channel_name': self.title,
            'last_message': None if last_message is None else last_message.to_json(),
            'is_channel': self.is_channel or True,
            'members': members,
            'members_count': members_count,
            'created_on': self.created
        }


    @classmethod
    def exists(cls, id: str = None, title: str = None) -> 'Channel':
        if id is not None:
            return Channel.query.get(id)
        return Channel.query.filter_by(title=title).first()

    @classmethod
    def matches(cls, title: str):
        channels = Channel.query.filter(Channel.title.ilike(f"%{title}%")).all()
        return {
            'title': title,
            'matches': [c.preview() for c in channels if c.is_channel]
        }


class Message(BaseMixin, db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.String, db.ForeignKey("channels.id"), nullable=True)  # receiver channel
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)  # sender
    message = db.Column(db.Text, nullable=False)
    dttm = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp())
    status = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"< Message : {self.message}, Sender: {self.user}, Channel: {self.channel} >"

    def to_json(self):
        """Converts message to a json object"""
        return {
            'mid': self.id,
            'room': self.channel.title,
            'room_id': self.channel_id,
            'user': self.user.display_name,
            'message': self.message,
            'timestamp': self.dttm.__str__()
        }

    def to_user_json(self, username: str):
        """Converts to a json object for sender of dm"""
        json_message = self.to_json() 
        user = User().exists(username)
        if user is None:
            return self.to_json()
        room = ", ".join(list(filter(lambda x: x != user.display_name, json_message["room"].split("_"))))
        room_id = ", ".join(list(filter(lambda x: x != user.username, json_message["room_id"].split("_"))))
        return {
            **json_message,
            'room': room,
            'room_id': room_id,
        }


class Connection(BaseMixin, TimestampMixin, db.Model):
    __tablename__ = "connections"
    __table_args__ = (
        db.UniqueConstraint('user_id', 'peer_id', name='unique_user_peer'),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    peer_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    is_blocked = db.Column(db.Boolean, default=False)

    @classmethod
    def get_connection_list(cls, user_id: int):
        connections = cls.query.filter(and_(cls.user_id == user_id, cls.is_blocked == False)).all()
        connection_list = []
        for connection in connections:
            peer = User.exists(user_id=connection.peer_id)
            if peer is not None:
                connection_list.append(peer.preview())
        return connection_list

    @classmethod
    def exists(cls, user_id: int, peer_id: int):
        return cls.query.filter(and_(cls.user_id==user_id, cls.peer_id==peer_id)).first()

    @classmethod
    def create_if_not_exists(cls, user_id: int, peer_id: int):
        connection = cls.exists(user_id, peer_id)
        if connection is None:
            conection = cls.create(user_id=user_id, peer_id=peer_id)
        return connection
