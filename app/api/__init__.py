from flask import Blueprint
# 创建api蓝本
api = Blueprint('api', __name__)

from . import authentication, posts, users, comments, errors
