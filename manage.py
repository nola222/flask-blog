# 此文件用于启动程序
# shebang(!#符号，也称sha-bang)声明，指明解释这个脚本文件的解释程序
#!/source/Flask111/bin/activate python3

import os
from app import create_app, db
from app.models import User, Role
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

# 从环境变量设置的配置指定程序的配置，若没设置，使用默认的开发环境的配置
app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)

# 指定shell的上下文
def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role)
manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command("db", MigrateCommand)

# 启动单元测试的命令
# 装饰器修饰的函数名为命令名 运行测试命令 python manage.py test
@manager.command
def test():
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)

if __name__ == '__main__':
    manager.run()

