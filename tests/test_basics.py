import unittest
from flask import current_app
from app import create_app, db

class BasicsTestCase(unittest.TestCase):
    #测试前使用 -- 创建一个测试环境 
    def setUp(self):
        # 使用测试配置创建程序
        self.app = create_app('testing')
        # 激活上下文
        self.app_context = self.app.app_context()
        self.app_context.push()
        # 创建数据库
        db.create_all()
    
    #测试后使用
    def tearDown(self):
        # 移除session
        db.session.remove()
        # 删除数据库所有测试数据
        db.drop_all()
        # 删除app上下文
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(current_app is None)
 
    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])     
