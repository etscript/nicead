import jwt
from jwt.exceptions import ExpiredSignatureError
from datetime import datetime, timedelta
from flask import current_app, request, session, g, jsonify, abort
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth
from functools import wraps
from app.utils.code import ResponseCode
from app.utils.util import ResMsg
from app.models.model import User, Department, Operation
from app.utils.core import db

token_auth = HTTPTokenAuth()

class Auth(object):
    key = 'super-man$&123das%qzq'

    @classmethod
    def generate_access_token(cls, user_id, algorithm: str = 'HS256', exp: float = 24):
        """
        生成access_token
        :param user_id:自定义部分
        :param algorithm:加密算法
        :param exp:过期时间
        :return:
        """

        key = current_app.config.get('SECRET_KEY', cls.key)
        now = datetime.utcnow()
        exp_datetime = now + timedelta(hours=exp)
        access_payload = {
            'exp': exp_datetime,
            'flag': 0,  # 标识是否为一次性token，0是，1不是
            'iat': now,  # 开始时间
            'iss': 'qin',  # 签名
            'user_id': user_id  # 自定义部分
        }
        access_token = jwt.encode(access_payload, key, algorithm=algorithm)
        return access_token

    @classmethod
    def generate_refresh_token(cls, user_id, algorithm: str = 'HS256', fresh: float = 30):
        """
        生成refresh_token

        :param user_id:自定义部分
        :param algorithm:加密算法
        :param fresh:过期时间
        :return:
        """
        key = current_app.config.get('SECRET_KEY', cls.key)

        now = datetime.utcnow()
        exp_datetime = now + timedelta(days=fresh)
        refresh_payload = {
            'exp': exp_datetime,
            'flag': 1,  # 标识是否为一次性token，0是，1不是
            'iat': now,  # 开始时间
            'iss': 'qin',  # 签名，
            'user_id': user_id  # 自定义部分
        }

        refresh_token = jwt.encode(refresh_payload, key, algorithm=algorithm)
        return refresh_token

    @classmethod
    def encode_auth_token(cls, user_id: str,
                          exp: float = 2,
                          fresh: float = 30,
                          algorithm: str = 'HS256') -> [str, str]:
        """
        :param user_id: 用户ID
        :param exp: access_token过期时间
        :param fresh:  refresh_token过期时间,刷新access_token使用
        :param algorithm: 加密算法
        :return:
        """
        access_token = cls.generate_access_token(user_id, algorithm, exp)
        refresh_token = cls.generate_refresh_token(user_id, algorithm, fresh)
        return access_token, refresh_token

    @classmethod
    def decode_auth_token(cls, token: str):
        """
        验证token
        :param token:
        :return:
        """
        key = current_app.config.get('SECRET_KEY', cls.key)

        try:
            # 取消过期时间验证
            # payload = jwt.decode(auth_token, config.SECRET_KEY, options={'verify_exp': False})
            payload = jwt.decode(token, key=key, )

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.InvalidSignatureError):
            return None
        else:
            return payload

    def identify(self, auth_header):
        """
        用户鉴权
        #TODO:暂时只起用户验证的功能,权限未完善
        :return: list
        """
        if auth_header:
            payload = self.decode_auth_token(auth_header)
            if payload is None:
                return False
            if "user_id" in payload and "flag" in payload:
                if payload["flag"] == 1:
                    # 用来获取新access_token的refresh_token无法获取数据
                    return False
                elif payload["flag"] == 0:

                    return payload["user_id"]
                else:
                    # 其他状态暂不允许
                    return False
            else:
                return False
        else:
            return False


def login_required(f):
    """
    登陆保护，验证用户是否登陆
    :param f:
    :return:
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        res = ResMsg()
        token = request.headers.get("access_token", default=None)
        if not token:
            res.update(code=ResponseCode.PleaseSignIn)
            return res.data

        auth = Auth()
        user_name = auth.identify(token)
        if not user_name:
            res.update(code=ResponseCode.PleaseSignIn)
            return res.data

        # 获取到用户并写入到session中,方便后续使用
        session["user_name"] = user_name
        return f(*args, **kwargs)

    return wrapper


def verify_jwt_token(f):
    """
    jwt保护，验证用户是否登陆
    :param f:
    :return:
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        res = ResMsg()
        token = request.headers.get("access_token", default=None)
        if not token:
            res.update(code=ResponseCode.PleaseSignIn)
            return res.data
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'],
                                algorithms=['HS256'])
            if payload["exp"] < int(time.time()):
                res.update(code=ResponseCode.PleaseReSignIn)
                return res.data
        except ExpiredSignatureError:
            res.update(code=ResponseCode.PleaseSignIn)
            return res.data
        if payload:
            # 获取到用户并写入到g.current_user中,方便后续使用
            g.current_user = WXUser.verify_jwt(token) if token else None
            return f(*args, **kwargs)
        res.update(code=ResponseCode.PleaseSignIn)
        return res.data
    return wrapper

@token_auth.verify_token
def verify_token(token):
    '''用于检查用户请求是否有token，并且token真实存在，还在有效期内'''
    g.current_user = User.verify_jwt(token) if token else None
    if g.current_user:
        # 每次认证通过后（即将访问资源API），更新 last_seen 时间
        g.current_user.ping()
        db.session.commit()
        # department_id = g.current_user.get('department_id')
        # g.current_auth = Department.query.get(department_id).get('auth')
    return g.current_user is not None

@token_auth.error_handler
def token_auth_error():
    '''用于在 Token Auth 认证失败的情况下返回错误响应'''
    res = ResMsg()
    res.update(code=ResponseCode.PleaseSignIn)
    return res.data
        
# 用户操作权限检测
def permission_required(permission):
    '''定义装饰器@permission_required(permission)'''
    def decorator(f):
        @wraps(f)
        def decorated_function(*args,**kwargs):
            if not g.current_user.can(permission):                        #如果当前用户不具有permission则抛出403错误。
                abort(403, "你没有权限进行这次的操作")
            return f(*args,**kwargs)
        return decorated_function
    return decorator

# 用户操作日志记录
def record_operation(describe):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args,**kwargs):
            operation = Operation()
            operation.from_dict({"operator_id":g.current_user.get("id"),\
                                "describe":describe, "ip":request.remote_addr})
            db.session.add(operation)
            db.session.commit()
            return f(*args,**kwargs)
        return decorated_function
    return decorator