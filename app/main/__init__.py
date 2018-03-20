#在单脚本程序中，程序实例在全局作用域中，共用一个app，此时flask 使用蓝本定义路由，定义路由后是出于休眠状态，知道蓝本注册到程序上后，路由才称为程序的一部分，为了获得更大的灵活性，程序包中创建一个子包，用于保存蓝本。
from flask import Blueprint
from ..models import Permission

# 实例化一个Blueprint类对象， 参数（蓝本名，蓝本所在bao或模块）
main = Blueprint('main', __name__)

# 路由保存在views包中，错误处理程序保存在errors包中，导入这两个模块就能与蓝本关联起来  注意要在脚本末尾导入避免循环导入
from . import views, errors

# 把Permission类加入模板上下文
@main.app_context_processor
def inject_permission():
    return dict(Permission=Permission)
