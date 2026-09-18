from datetime import datetime, timezone  # noqa: I001
from time import time
from typing import Optional
from flask_login import UserMixin
from hashlib import md5
# handles database connections, SQL generations and low-level operations
# how to talk to the DB
import sqlalchemy as sa
# provides support for using models, maps classes to DB tables and manages relationships
# how to represent DB as Python objects
import sqlalchemy.orm as so
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from flask import current_app
from app.search import add_to_index, remove_from_index, query_index


class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return [], 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        query = sa.select(cls).where(cls.id.in_(ids)).order_by(
            db.case(*when, value=cls.id))
        return db.session.scalars(query), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in db.session.scalars(sa.select(cls)):
            add_to_index(cls.__tablename__, obj)

db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


followers = sa.Table(
    'followers',
    db.metadata, # data about data, describes structure, org, rules of a DB
    sa.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True), # ID of the user who is following
    sa.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True) # ID of the user who is being followed
)

class User(UserMixin, db.Model): # inherits from db.Model, a base class turns classes into DB table
    ''' so.Mapped[str] maps the attribute email, id to a database column by type hints
    so.mapped_column declares the database column.
    Mapped[] declares what type of python value it is, mapped_column() declares attr. is database column with
    specific options'''
    id: so.Mapped[int] = so.mapped_column(primary_key=True) 
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    following: so.WriteOnlyMapped['User'] = so.relationship( # defines users I follow
        secondary=followers, # use follower association table as the link 
        primaryjoin=(followers.c.follower_id == id), # I'm the follower, my ID is follower_id
        secondaryjoin=(followers.c.followed_id == id), # They're the followed, ID is followed_id
        back_populates='followers')
    followers: so.WriteOnlyMapped['User'] = so.relationship( # defines users that follow me
        secondary=followers, # use follower association table as the link 
        primaryjoin=(followers.c.followed_id == id),# I'm the followed, my ID is followed_id
        secondaryjoin=(followers.c.follower_id == id),# They're the follower,the ID is follower_id
        back_populates='following')

    # methods
    def __repr__(self): # tells Py how to print objects of this class
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password) # type: ignore
    
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest() # encode string as bytes for md5 support
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
    
    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None

    def followers_count(self):
        query = sa.select(sa.func.count()).select_from(self.followers.select().subquery())
        return db.session.scalar(query)

    def following_count(self):
        query = sa.select(sa.func.count()).select_from(self.following.select().subquery())
        return db.session.scalar(query)

    def following_posts(self):
        Author = so.aliased(User) # person who wrote the post
        Follower = so.aliased(User) # person who follows the author
        return (
        sa.select(Post) # select from Post table
        .join(Post.author.of_type(Author)) # link post to the author(who wrote the post)
        .join(Author.followers.of_type(Follower), isouter=True) # link author to followers of that author
        .where(sa.or_(
            Follower.id == self.id,
            Author.id == self.id,
        ))# filter I am the follower, also get my own post
        .group_by(Post) # type: ignore
        .order_by(Post.timestamp.desc()) # sort by newest first
        )

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode( {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except Exception:
            return
        return db.session.get(User, id) 
                  
@login.user_loader # takes the ID of a user and return corresponding user object
def load_user(id):
    return db.session.get(User, int(id))

class Post(SearchableMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True) # a foreign key on the many side
    author: so.Mapped[User] = so.relationship(back_populates='posts')
    language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))
    __searchable__ = ['body']
    
    def __repr__(self):
        return f'<Post {self.body}>'

