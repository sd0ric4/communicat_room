import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from server.models.user import User, UserManager
from server.models.message import Message, MessageManager
from server.models.channel import Channel, ChannelManager
from server.utils.security import SecurityManager
from server.utils.database import DatabaseManager
from server.config import DB_CONFIG, TEST_CONFIG

class TestChatServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """初始化测试环境，只运行一次"""
        # 使用测试配置
        cls.db = DatabaseManager(TEST_CONFIG)
        cls.user_manager = UserManager(cls.db)
        cls.message_manager = MessageManager(cls.db)
        cls.channel_manager = ChannelManager(cls.db)

    def setUp(self):
        """每个测试用例开始前运行"""
        # 创建测试用户
        self.test_user = User.create("testuser", "password123")
        self.test_user = self.user_manager.create_user(
            self.test_user.username,
            "password123"
        )

    def tearDown(self):
        """每个测试用例结束后运行"""
        # 清理测试数据
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages")
            cursor.execute("DELETE FROM users WHERE username LIKE 'test%'")
            cursor.execute("DELETE FROM channels WHERE name LIKE 'test%'")
            conn.commit()

    def test_user_authentication(self):
        """测试用户认证"""
        self.assertTrue(self.test_user.verify_password("password123"))
        self.assertFalse(self.test_user.verify_password("wrongpassword"))

    def test_message_creation(self):
        """测试消息创建"""
        # 创建测试频道
        channel = Channel(
            id=None,
            name="test_channel",
            description="Test Channel",
            created_at=datetime.now()
        )
        channel = self.channel_manager.create_channel(channel)
        
        # 创建测试消息
        message = Message(
            id=None,
            channel_id=channel.id,
            sender_id=self.test_user.id,
            content="Test message",
            created_at=datetime.now()
        )
        
        # 保存消息并验证
        saved_message = self.message_manager.create_message(message)
        self.assertIsNotNone(saved_message)
        self.assertEqual(saved_message.content, "Test message")
        
        # 获取并验证频道消息
        messages = self.message_manager.get_channel_messages(channel.id)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].content, "Test message")

    def test_private_messaging(self):
        """测试私聊功能"""
        # 创建第二个测试用户
        other_user = User.create("testuser2", "password123")
        other_user = self.user_manager.create_user(
            other_user.username,
            "password123"
        )
        
        # 创建私聊消息
        channel = self.channel_manager.get_channel_by_name("general")
        message = Message(
            id=None,
            channel_id=channel.id,
            sender_id=self.test_user.id,
            content="Private test message",
            created_at=datetime.now(),
            is_private=True,
            recipient_id=other_user.id
        )
        
        # 保存并验证私聊消息
        saved_message = self.message_manager.create_message(message)
        self.assertIsNotNone(saved_message)
        
        # 获取并验证私聊记录
        messages = self.message_manager.get_private_messages(
            self.test_user.id,
            other_user.id
        )
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].content, "Private test message")

    def test_channel_management(self):
        """测试频道管理"""
        # 创建频道
        channel = Channel(
            id=None,
            name="test_channel",
            description="Test Channel",
            created_at=datetime.now(),
            owner_id=self.test_user.id
        )
        
        # 保存并验证频道
        saved_channel = self.channel_manager.create_channel(channel)
        self.assertIsNotNone(saved_channel)
        
        # 获取并验证频道
        found_channel = self.channel_manager.get_channel_by_name("test_channel")
        self.assertIsNotNone(found_channel)
        self.assertEqual(found_channel.name, "test_channel")
        
        # 删除并验证频道
        self.assertTrue(
            self.channel_manager.delete_channel(
                saved_channel.id,
                self.test_user.id
            )
        )
        
        # 确认频道已删除
        deleted_channel = self.channel_manager.get_channel_by_name("test_channel")
        self.assertIsNone(deleted_channel)

    def test_security_features(self):
        """测试安全功能"""
        # 测试密码哈希
        password = "testpassword123"
        hashed, salt = SecurityManager.hash_password(password)
        self.assertTrue(SecurityManager.verify_password(password, hashed, salt))
        
        # 测试输入清理
        dirty_input = '<script>alert("xss")</script>'
        clean_input = SecurityManager.sanitize_input(dirty_input)
        self.assertNotIn("<script>", clean_input)
        
        # 测试令牌生成
        token = SecurityManager.generate_token()
        self.assertGreater(len(token), 32)

if __name__ == '__main__':
    unittest.main()