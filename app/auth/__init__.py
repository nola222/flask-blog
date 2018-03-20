# 把创建程序的过程移入工厂函数后，可以使用蓝本在全局作用域中定义路由。与用户认证系统相关的路由在auth蓝本中定义。对于不同的程序使用不同的蓝本。

from flask import Blueprint

auth = Blueprint('auth', __name__)

from . import views

 

