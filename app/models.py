# Werkzeug中的security模块能够方便实现密码散列值的计算。只需要两个函数在注册用户和验证用户阶段
# generate_password_hash(),这个函数将原始密码作为输入，以字符串形式输出密码的散列值，输出的值可保存在用户数据库中
# check_password_hash(),这个函数的参数是从数据库中取回的密码散列值和用户输入的密码。返回True表明密码正确。


from werkzeug.security import generate_password_hash, check_password_hash
from . import login_manager
from flask_login import UserMixin, AnonymousUserMixin
# 使用itsdangerous库生成令牌
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from . import db, login_manager
from datetime import datetime
import hashlib
from markdown import markdown
import bleach

# 权限常量
class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16 


# 定义模型
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    # 表名关系另一端是user，并向user模型中提供一个role属性
    users = db.relationship('User', backref='role', lazy='dynamic')
    default = db.Column(db.Boolean, default=False, index=True)
    # permissions表示位标志 role权限使用位

    permissions = db.Column(db.Integer)
    
    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    # 在数据库中创建角色
    @staticmethod
    def insert_roles():
        roles = {
            'User':[Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator':[Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE],
            'Administrator':[Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE, Permission.ADMIN]
        }
        default_role = 'User'
        for r in roles:
            # 查找角色名，只有当数据库没有这个角色才会创建
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        print(type(self.permissions))
        print(self.permissions,perm)
        return self.permissions & perm == perm

    # repr给机器用的，str显示给用户用的
    def __repr__(self):
        return '<Role %r>' % self.name

# 关注关联表模型 多对多
class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    

# flask-login 提供一个UserMixin类包含一些实现用户的方法的
# 字段index=True是要建立索引
class User(UserMixin ,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    # 什么时候注册的
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    # db.String 与 db.Text区别前面需要指定长度
    # 使用缓存的MD5散列值生成Gravatar URL
    avatar_hash = db.Column(db.String(32))
    # 用户和博客文章是一对多关系 backref对关系提供反向引用的声明
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    # followed 和 follower的都定义为单独的一对多关系
    followed = db.relationship('Follow',
                                foreign_keys=[Follow.follower_id],
                                backref=db.backref('follower', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    # 把用户设为自己关注者
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    # 定义默认的用户角色
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            # 管理员角色
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            # 默认角色 普通用户
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
    
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash() 
        # 将用户设为自己的关注者
        self.follow(self)

    # 生成改变邮箱的token
    def generate_email_change_token(self, new_emial, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps(
            {'change_email': self.id, 'new_email': new_email}).decode('utf-8')

    # 更新用户有效散列值 若用户改变邮箱
    def change_email(self, token):
        s = Serailizer(current_app.config['SECRET_KEY']) 
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        db.session.commit()
        return True

    # 角色验证
    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    # 刷新用户最后访问时间  因为auth蓝本钩子会在处理程序会在请求前执行，所以很容易刷新时间
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    # 生成Gravatar URL 随机头像（avatar阿凡达）
    # size大小  default没有注册的使用默认生成头像方式  rating图片等级
    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(url=url, hash=hash, size=size, default=default, rating=rating)


    def generate_confirmation_token(self, expiration=3600):
        # 上面那个很长的类的构造函数接收一个参数secret_key，dumps()方法指定的数据生成一个加密签名，再对数据和签名进行序列化，生成令牌字符串；序列化对象提供loads()方法解码令牌
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm' : self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    # 生成重设token
    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id}).decode('utf-8')

    # 重设密码
    @staticmethod
    def reset_password(token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        db.session.commit()
        return True
    
    # 关注关系的辅助方法
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(followed=user)
            self.followed.append(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            self.followed.remove(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

    # 获取所关注的用户的文章
    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id)\
            .filter(Follow.follower_id == self.id)

    # 生成用户认证token 使用编码后的用户id字段值生成一个签名令牌
    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('utf-8')

    # 验证用户认证的token 接收一个令牌参数，令牌可用反回对应的用户
    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SCRECT_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    # 把用户转换成json格式的序列化字典
    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts_url': url_for('api.get_user_posts', id=self.id),
            'followed_posts_url': url_for('api.get_user_followed_posts', id=self.id),
            'post_count': self.posts.count()
        }
        return json_user
     
        
    def __repr__(self):
        return '<User %r>' % self.username

    # @property 装饰器使得装饰的方法可以当作类的属性进行使用 getter
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        # 设置password将原始字符串输入，以字符串形式输出密码的散列值
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    # 加载用户的回调函数
    @login_manager.user_loader
    def load_user(user_id):
        # 加载用户的回调函数接收以unicode字符串形式表示的用户标识符。如果能找到用户，返回用户对象，若无，返回None
        return User.query.get(int(user_id))

    # 生成fake数据乱文假数 -- 用户
    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(True),
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError: 
                db.session.rollback()


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False
 
    def is_adminstrator(self):
        return False

login_manager.anonymous_user = AnonymousUser


# 提交文章模型
class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    body_html = db.Column(db.Text)
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    # 生成fake数据乱文假数 -- 用户
    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py

        seed()
        '''
        seed( ) 用于指定随机数生成时所用算法开始的整数值。 
        1.如果使用相同的seed( )值，则每次生成的随即数都相同； 
        2.如果不设置这个值，则系统根据时间来自己选择这个值，此时每次生成的随机数因时间差异而不同。 
        3.设置的seed()值仅一次有效
        '''
        user_count = User.query.count()
        for i in range(count):
            # offset设定随机偏移值
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
                     timestamp=forgery_py.date.date(True),
                     author=u)
            db.session.add(p)
            db.session.commit()

    # 服务器上处理富文本
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym',  'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    # 资源和json的序列化转化  json格式的序列化字典
    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
            'comments_url': url_for('api.get_post_comments', id=self.id),
            'comment_count': self.comments.count()
        }
        return json_post

    # 从json数据创建一篇博客
    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)
# 监听这个字段，设了新值自动调用上面这个函数  实现markdown到html的转换
db.event.listen(Post.body, 'set',Post.on_changed_body)

# 评论类
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # 协管员可以通过这个字段查禁不当评论
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id')) 

    # 把markdown文本转换成html
    @staticmethod
    def on_change_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i', 'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id),
            'post_url': url_for('api.get_post', id=self.post_id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)

db.event.listen(Comment.body, 'set', Comment.on_change_body)
    
