from datetime import datetime
from operator import itemgetter
import re
from flask import request, jsonify, url_for, g, current_app
from app.api import bp
from app.utils.auth import token_auth, permission_required, record_operation
from app.utils.core import db
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.models.model import Department, User

@bp.route('/departments/', methods=['POST'])
@token_auth.login_required
def create_department():
    """
    部门注册
    ---
    tags:
      - 部门相关接口
    description:
        部门注册接口，json格式
    parameters:
      - name: body
        description: 部门注册接口的body数据
        in: body
        type: object
        required: true
        schema:
          id: 部门
          required:
            - username
            - password
          properties:
            name:
              type: string
              description: 部门名字, 如销售部.
            describe:
              type: string
              description: 部门描述, 如销售部.
            permissions:
              type: string
              description: 权限, 如{"部门":"修改"}.
            active:
              type: boolean
              description: 是否使用, 如true.
    responses:
      200:
        description: 
    """
    data = request.get_json()
    if not data:
        code = ResponseCode.InvalidParameter
        return ResMsg(code = code, data='You must post JSON data.').data

    department = Department()
    department.from_dict(data)
    db.session.add(department)
    db.session.commit()

    return ResMsg(data='部门创建成功').data


@bp.route('/departments/', methods=['GET'])
@token_auth.login_required
@permission_required({"hello":"123"})
# @record_operation("操作了列出部门信息")
def get_departments():
    """
    返回部门合集，分页显示
    ---
    tags:
      - 部门相关接口
    description:
        部门信息接口，json格式
    parameters:
      - name: page
        in: path
        type: integer
        description: 第几页
      - name: per_page
        in: path
        type: integer
        description: 每页多少个
      - name: timestamp
        in: path
        type: string
        description: 部门创建时间升序(不写) 降序descending
    responses:
      200:
        description: 
    """
    page = request.args.get('page', 1, type=int)
    timestamp = request.args.get('timestamp')
    per_page = min(
        request.args.get(
            'per_page', current_app.config['DEPARTMENTS_PER_PAGE'], type=int), 100)
    query = Department.query
    if timestamp == 'descending':
        query = query.order_by(Department.timestamp.desc())
    data = Department.to_collection_dict(query, page, per_page, \
                    'api.get_departments',timestamp=timestamp)
    return ResMsg(data=data).data


@bp.route('/departments/<int:id>', methods=['GET'])
@token_auth.login_required
def get_department(id):
    """
    返回部门具体信息
    ---
    tags:
      - 部门相关接口
    description:
        部门信息接口
    parameters:
      - name: id
        in: path
        type: integer
        description: 部门id
    responses:
      200:
        description: 
    """
    department = Department.query.get_or_404(id)
    data = department.to_dict()
    return ResMsg(data=data).data

@bp.route('/departments/<int:id>/members/', methods=['GET'])
@token_auth.login_required
def get_department_members(id):
    """
    返回部门内用户具体信息
    ---
    tags:
      - 部门相关接口
    description:
        部门信息接口
    parameters:
      - name: id
        in: path
        type: integer
        description: 部门id
    responses:
      200:
        description: 
    """
    department = Department.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = min(
        request.args.get(
            'per_page', current_app.config['USERS_PER_PAGE'], type=int), 100)
    data = User.to_collection_dict(
        department.members.order_by(User.id.desc()), page, per_page,
        'api.get_department_members', id=id)
    return ResMsg(data=data).data


@bp.route('/departments/<int:id>', methods=['PUT'])
@token_auth.login_required
def update_department(id):
    """
    更新某个部门
    ---
    tags:
      - 部门相关接口
    description:
        部门信息接口
    parameters:
      - name: id
        in: path
        type: integer
        description: 用户id
      - name: body
        description: 部门的数据格式
        in: body
        type: string
        required: true
        schema:
          id: 部门
          required:
            - name
            - describe
            - members
            - active
            - permissions
          properties:
            name:
              type: string
              description: 部门名称.
            describe:
              type: string
              description: 部门描述.
            permissions:
              type: string
              description: 权限设置.
            active:
              type: boolean
              description: 是否启用.
    responses:
      200:
        description: 
    """
    department = Department.query.get_or_404(id)
    data = request.get_json()
    if not data:
        code = ResponseCode.InvalidParameter
        return ResMsg(code=code, data='You must post JSON data.').data

    department.from_dict(data)
    db.session.commit()
    return ResMsg(data=department.to_dict()).data

@bp.route('/departments/<int:id>', methods=['DELETE'])
@token_auth.login_required
def delete_department(id):
    """
    删除某个部门
    ---
    tags:
      - 部门相关接口
    description:
        部门信息接口
    parameters:
      - name: id
        in: path
        type: integer
        description: 部门id
    responses:
      200:
        description: 
    """
    department = Department.query.get_or_404(id)
    # if g.current_user != user:
    #     return error_response(403)
    db.session.delete(department)
    db.session.commit()
    return '', 204