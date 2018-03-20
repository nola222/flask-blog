from flask import jsonify
from app.exceptions import ValidationError
from . import api

# api蓝本中403状态吗的错误处理程序
def forbidden(message):
    # 向客户端发送json格式响应
    response = jsonify({'error':'forbidden', 'message':message})
    response.status_code = 403
    return response

def bad_request(message):
    response = jsonify({'error':'bad_request', 'message':message})
    response.status_code = 400
    return response

def unauthorized(message):
    response = jsonify({'error':'unauthorized', 'message':message})
    response.status_code = 401
    return response

# 定义一个全局异常处理程序
@api.errorhandler(ValidationError)
def validation_error(e):
    return bad_request(e.args[0])
