from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth
from ..models import User
from . import api
from .errors import unauthorized, forbidden

# HTTP基本认证的扩展扩展前 创建一个HTTPBasicAuth类对象
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(email_or_token, password):
    if email_or_token == '':
        return False
    if password == '':
        # 验证回调函数把认证通过的用户保存在flask的全局对象中。
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    return user.verify_password(password)

# 认证错误处理程序
@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


# 蓝本的路由都有使用login_required修饰 所以在钩子中加入修饰
@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous and \
        not g.current_user.confirmed:
        return forbidden('Unconfirmed accocunt')

# 基于令牌的认证 生成认证令牌 
@api.route('tokens/', methods=['GET', 'POST'])
def get_token():
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized('Invalid credentials')
    return jsonify({'token': g.current_user.generate_auth_token(
        expiration=3600), 'expiration': 3600})

