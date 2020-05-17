from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.core import db
from datetime import datetime, timedelta
from flask import current_app
from hashlib import md5
import jwt

class PaginatedAPIMixin(object):
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        # 如果当前没有任何资源时，或者前端请求的 page 越界时，都会抛出 404 错误
        # 由 @bp.app_errorhandler(404) 自动处理，即响应 JSON 数据：{ error: "Not Found" }
        resources = query.paginate(page, per_page)
        data = {
            'items': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total
            },
            '_links': {
                'self': url_for(endpoint, page=page, per_page=per_page,
                                **kwargs),
                'next': url_for(endpoint, page=page + 1, per_page=per_page,
                                **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page - 1, per_page=per_page,
                                **kwargs) if resources.has_prev else None
            }
        }
        return data

class User(PaginatedAPIMixin, db.Model):
    # 设置数据库表名，Post模型中的外键 user_id 会引用 users.id
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    name = db.Column(db.String(64), index=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))  # 不保存原始密码
    location = db.Column(db.String(64))
    # about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        '''设置用户密码，保存为 Hash 值'''
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        '''验证密码与保存的 Hash 值是否匹配'''
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        '''用户头像'''
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, size)

    def to_dict(self, include_email=False):
        data = {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'email': self.email,
            'location': self.location,
            # 'about_me': self.about_me,
            'member_since': self.member_since.isoformat() + 'Z',
            'last_seen': self.last_seen.isoformat() + 'Z'
        }
        return data

    def from_dict(self, data, new_user=False):
        for field in ['username', 'email', 'name', 'location']:
            if field in data:
                setattr(self, field, data[field])
        if new_user and 'password' in data:
            self.set_password(data['password'])

    def ping(self):
        '''更新用户的最后访问时间'''
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def get_jwt(self, expires_in=3600):
        '''用户登录后，发放有效的 JWT'''
        now = datetime.utcnow()
        payload = {
            'user_id': self.id,
            'user_name': self.username if self.username else self.name,
            'name': self.name if self.name else self.username,
            'exp': now + timedelta(seconds=expires_in),
            'iat': now
        }
        return jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_jwt(token):
        '''验证 JWT 的有效性'''
        try:
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256'])
        except (jwt.exceptions.ExpiredSignatureError,
                jwt.exceptions.InvalidSignatureError,
                jwt.exceptions.DecodeError) as e:
            # Token过期，或被人修改，那么签名验证也会失败
            return None
        return User.query.get(payload.get('user_id'))

class UserLoginMethod(db.Model):
    """
    用户登陆验证表
    """
    __tablename__ = 'user_login_method'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)  # 用户登陆方式主键ID
    # user_id = db.Column(db.Integer, nullable=False)  # 用户主键ID
    login_method = db.Column(db.String(36), nullable=False)  # 用户登陆方式，WX微信，P手机
    identification = db.Column(db.String(36), nullable=False)  # 用户登陆标识，微信ID或手机号
    access_code = db.Column(db.String(36), nullable=True)  # 用户登陆通行码，密码或token
    nickname    = db.Column(db.String(128), nullable=True, server_default="")
    sex         = db.Column(db.String(1), nullable=False, server_default="0")
    admin       = db.Column(db.String(1), nullable=False, server_default="0")

    def to_dict(self):
        return {
            'id': self.id,
            'login_method': self.login_method,
            'identification': self.identification,
            'access_code': self.access_code,
            'nickname': self.nickname,
            'sex': self.sex,
            'admin': self.admin
        }


class ChangeLogs(db.Model):
    """
    修改日志
    """
    __tablename__ = 'change_logs'
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # 作者
    article_id = db.Column(db.Integer)  # 文章
    modify_content = db.Column(db.String(255), nullable=False)  # 修改内容
    create_time = db.Column(db.DateTime, nullable=False)  # 创建日期

class WXUser(db.Model):
    # 设置数据库表名
    __tablename__ = 'wxuser'
    id = db.Column(db.Integer, index=True, autoincrement=True)
    nickname = db.Column(db.String(128))
    openid = db.Column(db.String(255), index=True, primary_key=True)
    gender = db.Column(db.String(64))  
    country = db.Column(db.String(128))
    province = db.Column(db.String(128))
    city = db.Column(db.String(128))
    email = db.Column(db.String(255), index=True)

    def to_dict(self):
        data = {
            'id': self.id,
            'nickname': self.nickname,
            'openid': self.openid,
            'gender': self.gender,
            'country': self.country,
            'province': self.province,
            'city': self.city
        }
        return data

    def from_dict(self, data):
        for field in ['nickname', 'openid', 'gender', 'country', 'province', 'city']:
            if field in data:
                setattr(self, field, data[field])
        self.openid = data["openId"]
        self.nickname = data["nickName"]

    def get_jwt(self, expires_in=3600):
        '''用户登录后，发放有效的 JWT'''
        payload = {
            "iss": 'wxapp',
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400 * 7,
            "aud": 'flask',
            "openid": self.openid,
            "nickname": self.nickname,
            "scopes": ['open']
        }
        return jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256')
    
    @staticmethod
    def verify_jwt(token):
        '''验证 JWT 的有效性'''
        try:
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256'],
                audience="flask")
        except (jwt.exceptions.ExpiredSignatureError,
                jwt.exceptions.InvalidSignatureError,
                jwt.exceptions.DecodeError) as e:
            # Token过期，或被人修改，那么签名验证也会失败
            return None
        return WXUser.query.get(payload.get('openid'))


class Order(db.Model):
    # 设置数据库表名
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    status = db.Column(db.String(128))
    company = db.Column(db.String(255))
    create = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    start = db.Column(db.DateTime, index=True)
    complete = db.Column(db.DateTime, index=True)
    price = db.Column(db.Float)
    email = db.Column(db.String(128))
    wxuser_openid = db.Column(db.String(255), db.ForeignKey('wxuser.openid'))  # 属于哪个用户
    code = db.Column(db.String(255), index=True)
    payid = db.Column(db.String(255))
    result = db.Column(db.String(255))

    def to_dict(self):
        data = {
            'id': self.id,
            'status': self.status,
            'company': self.company,
            'create': self.create,
            'start': self.start,
            'complete': self.complete,
            'price': self.price,
            'email': self.email,
            'code': self.code,
            'payid': self.payid,
            'result': self.result
        }
        return data

    def from_dict(self, data):
        for field in ['status', 'company', 'price', 'email', 'code', 'wxuser_openid', 'payid', 'result']:
            if field in data:
                setattr(self, field, data[field])
            if field == "status" and data["status"] == "complete":
                setattr(self, "complete", datetime.now())

    @staticmethod
    def to_collection_dict(query, page=1, per_page=10, **kwargs):
        # 如果当前没有任何资源时，或者前端请求的 page 越界时，都会抛出 404 错误
        # 由 @bp.app_errorhandler(404) 自动处理，即响应 JSON 数据：{ error: "Not Found" }
        # resources = query.paginate(page, per_page)
        return [item.to_dict() for item in query]
