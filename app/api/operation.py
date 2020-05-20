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
@permission_required({"hello":"789"})
# @record_operation("请求了列出日志信息操作")
def get_operation():
    '''返回用户集合，分页'''
    page = request.args.get('page', 1, type=int)
    per_page = min(
        request.args.get(
            'per_page', current_app.config['DEPARTMENTS_PER_PAGE'], type=int), 100)
    data = Operation.to_collection_dict(Operation.query, page, per_page, 'api.get_operation')
    return ResMsg(data=data).data