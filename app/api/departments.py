from datetime import datetime
from operator import itemgetter
import re
from flask import request, jsonify, url_for, g, current_app
from app.api import bp
from app.utils.auth import token_auth
from app.utils.core import db
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.models.model import Department

@bp.route('/departments/', methods=['POST'])
def create_department():
    '''注册一个新部门'''
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
def get_departments():
    '''返回用户集合，分页'''
    page = request.args.get('page', 1, type=int)
    per_page = min(
        request.args.get(
            'per_page', current_app.config['DEPARTMENTS_PER_PAGE'], type=int), 100)
    data = Department.to_collection_dict(Department.query, page, per_page, 'api.get_departments')
    return ResMsg(data=data).data


@bp.route('/departments/<int:id>', methods=['GET'])
# @token_auth.login_required
def get_department(id):
    '''返回一个用户'''
    department = Department.query.get_or_404(id)
    # if g.current_user == user:
    #     return jsonify(user.to_dict(include_email=True))
    # 如果是查询其它用户，添加 是否已关注过该用户 的标志位
    data = department.to_dict()
    return ResMsg(data=data).data


@bp.route('/departments/<int:id>', methods=['PUT'])
# @token_auth.login_required
def update_department(id):
    '''修改一个用户'''
    department = Department.query.get_or_404(id)
    data = request.get_json()
    if not data:
        code = ResponseCode.InvalidParameter
        return ResMsg(code=code, data='You must post JSON data.').data

    department.from_dict(data)
    db.session.commit()
    return ResMsg(data=department.to_dict()).data

@bp.route('/departments/<int:id>', methods=['DELETE'])
# @token_auth.login_required
def delete_department(id):
    '''删除一个用户'''
    department = Department.query.get_or_404(id)
    # if g.current_user != user:
    #     return error_response(403)
    db.session.delete(department)
    db.session.commit()
    return '', 204