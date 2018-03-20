# 自定义装饰器
# 导入python标准库的functools包
from functools import wraps
# abort使夭折
from flask import abort
from flask_login import current_user
from .models import Permission

# 检查用户
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return permission_required(Permission.ADMIN)(f)

