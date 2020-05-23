from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.core import db
from datetime import datetime, timedelta
from flask import current_app, url_for
from hashlib import md5
import jwt
import json

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
    email = db.Column(db.String(120), index=True)
    password_hash = db.Column(db.String(128))  # 不保存原始密码
    # about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.now)
    # onupdate=datetime.now 修改任何信息，自动修改时间
    # last_seen = db.Column(db.DateTime(), default=datetime.now, onupdate=datetime.now)
    last_seen = db.Column(db.DateTime(), default=datetime.now)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    remark = db.Column(db.Text())
    operation = db.relationship('Operation', backref='operator', lazy='dynamic',
                            cascade='all, delete-orphan')

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
            'remark': self.remark,
            'department_id': self.department_id,
            'department_name': self.department.name,
            # 'about_me': self.about_me,
            'member_since': self.member_since.isoformat() + 'Z',
            'last_seen': self.last_seen.isoformat() + 'Z'
        }
        return data

    def from_dict(self, data, new_user=False):
        for field in ['username', 'email', 'name', 'department_id', 'remark']:
            if field in data:
                setattr(self, field, data[field])
        if 'password' in data:
            self.set_password(data['password'])

    def ping(self):
        '''更新用户的最后访问时间'''
        self.last_seen = datetime.now()
        db.session.add(self)
    
    def get(self, field):
        return getattr(self, field)

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
    
    # def get_permissions(self):
    #     self.permissions = Department.query.get(self.department_id).get("permissions")

    def can(self, operate_permission):
        #这个方法用来传入一个权限来核实用户是否有这个权限,返回bool值，检查permissions要求的权限角色是否允许
        d = Department.query.get(self.department_id)
        if not d.get("active"):
            return False
        self.permissions = d.get("permissions")
        self.permissions = json.loads(self.permissions)
        (op_key, op_val), = operate_permission.items()
        return op_val in self.permissions[op_key]
        
        
    # def is_administrator(self):
    #     	#因为常用所以单独写成一个方法以方便调用，其它权限也可以这样写
    #     return self.can(Permission.ADMINISTRATOR)

class Department(PaginatedAPIMixin, db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True, unique=True)
    describe = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now)
    members = db.relationship('User', backref='department', lazy='dynamic',
                               cascade='all, delete-orphan')
    active = db.Column(db.Boolean, default=True)
    permissions = db.Column(db.Text)

    def __repr__(self):
        return '<Department {}>'.format(self.id)

    def to_dict(self):
        data = {
            'id': self.id,
            'name': self.name,
            'timestamp': self.timestamp,
            'describe': self.describe,
            'members_count': self.members.count(),
            'active': self.active,
            'permissions': self.permissions
        }
        return data
    
    def get(self, field):
        return getattr(self, field)

    def from_dict(self, data):
        for field in ['name', 'describe', 'permissions']:
            if field in data:
                setattr(self, field, data[field])

class Operation(PaginatedAPIMixin, db.Model):
    __tablename__ = 'operations'
    id = db.Column(db.Integer, primary_key=True)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    describe = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now)
    ip = db.Column(db.Text)

    def from_dict(self, data):
        for field in ['operator_id', 'describe', 'ip']:
            if field in data:
                setattr(self, field, data[field])

    def to_dict(self):
        data = {
            'id': self.id,
            'operator_name': self.operator.username,
            'timestamp': self.timestamp,
            'describe': self.describe,
            'ip': self.ip
        }
        return data