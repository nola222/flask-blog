from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import config
from flask_login import LoginManager
from flask_pagedown import PageDown

bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
pagedown = PageDown()
login_manager = LoginManager()
# session_protection属性可以设为None、'basic'或'strong'提供不同的安全等级，防止用户会话遭到篡改。为strong时，flask-login会记录ip和用户代理信息，若异动登出。
login_manager.session_protection = 'strong'
# login_view设置登陆的端点
login_manager.login_view = 'auth.login'

# 工厂函数
def create_app(config_name):
    app = Flask(__name__)
    # app.config的from_object()方法导入程序
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # 初始化插件
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)

    # 附加路由和自定义错误页面
    from .main import main as main_blueprint
    # 注册蓝本，注册前处于休眠状态
    app.register_blueprint(main_blueprint)
    # 注册auth蓝本
    from .auth import auth as auth_blueprint
    # url_prefix参数可选  路由加上的前缀是什么 登陆路由就会变成auth/login
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    # 注册api蓝本
    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')
    return app


    
