#!/usr/bin/env python
#-*- coding: utf-8 -*-
from flask import request, jsonify, url_for, g, current_app
from app.utils.core import db
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.models.model import User, Department
import logging
from app.api import bp
logger = logging.getLogger(__name__)

@bp.route('/login/', methods=['POST'])
def login():
    """
    用户登录
    ---
    tags:
      - 用户相关接口
    description:
        用户登录接口，json格式
    parameters:
      - name: body
        in: body
        type: string
        required: true
        schema:
          id: 用户登录
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: 用户名.
            password:
              type: string
              description: 未加密过的密码.
    responses:
      200:
        description: 
    """
    
    # 创建返回内容模板
    data = request.get_json()
    if not data:
        code = ResponseCode.InvalidParameter
        return ResMsg(code = code, data = '没有收到账号密码').data
    user = User.query.filter_by(username=data["username"]).first()
    if not user:
        code = ResponseCode.InvalidParameter
        return ResMsg(code = code, data = '没有这个账号').data
    
    user = User.query.filter_by(username=data["username"]).first()
    is_validate = user.check_password(data["password"])
    if not is_validate:
        code = ResponseCode.InvalidParameter
        return ResMsg(code = code, data = '用户认证环节出错').data
    data = user.to_dict()
    data['token'] = user.get_jwt()
    data['permissions'] = Department.query.get(data['department_id']).get('permissions')
    return ResMsg(data=data).data

