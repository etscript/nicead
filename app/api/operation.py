from datetime import datetime
from operator import itemgetter
import re
from flask import request, jsonify, url_for, g, current_app
from app.api import bp
from app.utils.auth import token_auth, permission_required, record_operation
from app.utils.core import db
from app.utils.code import ResponseCode
from app.utils.response import ResMsg
from app.models.model import Operation, User

@bp.route('/operation/', methods=['GET'])
@token_auth.login_required
@permission_required({"hello":"123"})
# @record_operation("请求了列出日志信息操作")
def get_operation():
    """
    返回用户合集，分页显示
    ---
    tags:
      - 操作日志接口
    description:
        操作日志接口，json格式
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
        description: 日期匹配 日期格式如:2020-05-22
      - name: operator_id
        in: path
        type: integer
        description: 用户id
    responses:
      200:
        description: 
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(
        request.args.get(
            'per_page', current_app.config['DEPARTMENTS_PER_PAGE'], type=int), 100)
    timestamp = request.args.get('timestamp')
    operator_id = request.args.get('operator_id')
    if timestamp and operator_id:
        query = Operation.query.filter(Operation.operator_id == operator_id, Operation.timestamp.like("%" + timestamp + "%"))
    elif not timestamp and operator_id:
        query = Operation.query.filter(Operation.operator_id == operator_id)
    elif timestamp and not operator_id:
        query = Operation.query.filter(Operation.timestamp.like("%" + timestamp + "%"))
    else:
        query = Operation.query
    data = Operation.to_collection_dict(query, page, per_page, 'api.get_operation', timestamp=timestamp, operator_id=operator_id, )
    return ResMsg(data=data).data

# @bp.route('/operation/operators/', methods=['GET'])
# @token_auth.login_required
# @permission_required({"hello":"123"})
# # @record_operation("请求了列出日志信息操作")
# def get_operation_operators():
#     '''返回用户集合，分页'''
#     # page = request.args.get('page', 1, type=int)
#     # per_page = min(
#     #     request.args.get(
#     #         'per_page', current_app.config['DEPARTMENTS_PER_PAGE'], type=int), 100)
#     # data = Operation.to_collection_dict(Operation.query, page, per_page, 'api.get_operation')
#     data = Operation.query.with_entities(Operation.timestamp[0:9]).distinct().all()
#     return ResMsg(data=data).data