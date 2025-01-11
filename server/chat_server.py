import socket
import json
import threading
import time
from datetime import datetime
import logging

from .config import HEARTBEAT_CONFIG, SERVER_CONFIG, DB_CONFIG, REDIS_CONFIG, CHANNEL_CONFIG
from .models.user import User, UserManager
from .models.message import Message, MessageManager
from .models.channel import Channel, ChannelManager
from .utils.database import DatabaseManager
from .utils.security import SecurityManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ChatServer:
    def __init__(self, host=SERVER_CONFIG['host'], port=SERVER_CONFIG['port']):
        self.server_address = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.server_address)
        
        # 客户端连接信息
        self.clients = {}  # username -> (address, channel)
        self.heartbeats = {}  # username -> timestamp
        
        # 初始化数据库管理器
        self.db = DatabaseManager(DB_CONFIG, REDIS_CONFIG)
        
        # 初始化各个管理器
        self.user_manager = UserManager(self.db)
        self.message_manager = MessageManager(self.db)
        self.channel_manager = ChannelManager(self.db)
        
        logging.info(f"服务器启动于 {host}:{port}")
        
        # 确保系统频道存在
        self._ensure_system_channels()
        
        # 启动心跳检测线程
        threading.Thread(target=self._monitor_heartbeats, daemon=True).start()

    def _ensure_system_channels(self):
        """确保系统默认频道存在"""
        for channel_name in CHANNEL_CONFIG['system_channels']:
            if not self.channel_manager.get_channel_by_name(channel_name):
                channel = Channel(
                    id=None,
                    name=channel_name,
                    description=f"System channel: {channel_name}",
                    created_at=datetime.now()
                )
                self.channel_manager.create_channel(channel)

    def _authenticate_user(self, username, password):
        """认证用户"""
        user = self.user_manager.get_user_by_username(username)
        if user and user.verify_password(password):
            self.user_manager.update_last_login(user.id)
            return user
        return None

    def _store_message(self, message: Message):
        """存储消息"""
        return self.message_manager.create_message(message)

    def _get_channel_messages(self, channel_name, limit=50):
        """获取频道消息"""
        channel = self.channel_manager.get_channel_by_name(channel_name)
        if channel:
            return self.message_manager.get_channel_messages(channel.id, limit)
        return []

    def _broadcast_message(self, sender, content, channel, exclude_username=None):
        """广播消息到频道"""
        message = {
            "type": "message",
            "sender": sender,
            "content": SecurityManager.sanitize_input(content),
            "timestamp": str(time.time()),
            "channel": channel
        }
        
        encoded_message = json.dumps(message).encode()
        
        for username, (addr, user_channel) in self.clients.items():
            if username != exclude_username and user_channel == channel:
                try:
                    self.socket.sendto(encoded_message, addr)
                except Exception as e:
                    logging.error(f"发送消息错误: {str(e)}")

    def _send_private_message(self, sender: User, recipient: User, content: str, channel: str):
        """发送私聊消息"""
        if recipient.username in self.clients:
            message = {
                "type": "message",
                "sender": sender.username,
                "content": SecurityManager.sanitize_input(content),
                "timestamp": str(time.time()),
                "channel": channel,
                "is_private": True
            }
            
            encoded_message = json.dumps(message).encode()
            
            try:
                # 发送给接收者
                self.socket.sendto(encoded_message, self.clients[recipient.username][0])
                # 发送给发送者（回显）
                self.socket.sendto(encoded_message, self.clients[sender.username][0])
                return True
            except Exception as e:
                logging.error(f"发送私聊消息错误: {str(e)}")
                return False
        return False
    def _monitor_heartbeats(self):
        """监控客户端心跳"""
        while True:
            current_time = time.time()
            for username, last_heartbeat in list(self.heartbeats.items()):
                # 如果超过心跳超时时间
                if current_time - last_heartbeat > HEARTBEAT_CONFIG['timeout']:
                    # 从客户端列表中移除
                    if username in self.clients:
                        addr, channel = self.clients.pop(username)
                        # 广播用户离开消息
                        self._broadcast_message(
                            "system", 
                            f"{username} 因心跳超时断开连接", 
                            channel
                        )
                        # 从心跳记录中移除
                        del self.heartbeats[username]
                        logging.info(f"用户 {username} 因心跳超时断开连接")
            
            # 每隔一段时间检查一次
            time.sleep(HEARTBEAT_CONFIG['interval'])
    def _register_user(self, username, password):
        """注册新用户"""
        # 1. 验证用户名
        if not SecurityManager.validate_username(username):
            return "INVALID_USERNAME"
        
        # 2. 验证密码强度
        if not SecurityManager.validate_password(password):
            return "WEAK_PASSWORD"
        
        # 3. 检查用户是否已存在
        if self.user_manager.get_user_by_username(username):
            return "USERNAME_EXISTS"
        
        # 4. 创建新用户
        try:
            user = self.user_manager.create_user(username, password)
            return "REGISTER_SUCCESS" if user else "REGISTER_FAILED"
        except Exception as e:
            logging.error(f"用户注册错误: {str(e)}")
            return "REGISTER_FAILED"


    def _handle_auth(self, message, addr):
        """处理认证请求"""
        username = message["username"]
        password = message["password"]
        
        # 验证用户名格式
        if not SecurityManager.validate_username(username):
            self.socket.sendto(b"INVALID_USERNAME", addr)
            return
            
        user = self._authenticate_user(username, password)
        if user:
            self.clients[username] = (addr, CHANNEL_CONFIG["default_channel"])
            self.heartbeats[username] = time.time()
            
            # 发送频道列表
            channels = self.channel_manager.get_public_channels()
            self.socket.sendto(
                json.dumps({
                    "type": "channel_list",
                    "channels": [c.to_dict() for c in channels]
                }).encode(),
                addr
            )
            
            # 发送历史消息
            history = self._get_channel_messages(CHANNEL_CONFIG["default_channel"])
            self.socket.sendto(
                json.dumps({
                    "type": "history",
                    "messages": [m.to_dict() for m in history]
                }).encode(),
                addr
            )
            
            # 广播用户加入消息
            self._broadcast_message(
                "system", 
                f"{username} 加入了聊天室", 
                CHANNEL_CONFIG["default_channel"],
                username
            )
            logging.info(f"用户认证成功: {username}")
        else:
            self.socket.sendto(b"AUTH_FAILED", addr)
            logging.warning(f"用户认证失败: {username}")

    def _handle_message(self, message):
        """处理消息请求"""
        username = message["username"]
        content = message["content"]
        channel_name = message.get("channel", CHANNEL_CONFIG["default_channel"])
        recipient_name = message.get("recipient")
        
        if username in self.clients:
            sender = self.user_manager.get_user_by_username(username)
            channel = self.channel_manager.get_channel_by_name(channel_name)
            
            if not channel:
                logging.error(f"频道不存在: {channel_name}")
                return
                
            if recipient_name:
                recipient = self.user_manager.get_user_by_username(recipient_name)
                if recipient:
                    if self._send_private_message(sender, recipient, content, channel_name):
                        # 创建并存储私聊消息
                        msg = Message(
                            id=None,
                            channel_id=channel.id,
                            sender_id=sender.id,
                            content=content,
                            created_at=datetime.now(),
                            is_private=True,
                            recipient_id=recipient.id
                        )
                        self._store_message(msg)
            else:
                self._broadcast_message(username, content, channel_name)
                # 创建并存储公共消息
                msg = Message(
                    id=None,
                    channel_id=channel.id,
                    sender_id=sender.id,
                    content=content,
                    created_at=datetime.now()
                )
                self._store_message(msg)

    def _handle_heartbeat(self, message):
        """处理心跳包"""
        username = message["username"]
        if username in self.clients:
            self.heartbeats[username] = time.time()
            
    def _handle_join_channel(self, message):
        """处理加入频道请求"""
        username = message["username"]
        new_channel_name = message["channel"]
        
        if username not in self.clients:
            logging.warning(f"未认证的用户尝试加入频道: {username}")
            return
            
        # 获取用户和频道信息
        user = self.user_manager.get_user_by_username(username)
        new_channel = self.channel_manager.get_channel_by_name(new_channel_name)
        
        if not new_channel:
            logging.error(f"尝试加入不存在的频道: {new_channel_name}")
            return
        
        addr = self.clients[username][0]
        old_channel_name = self.clients[username][1]
        
        # 更新用户频道
        self.clients[username] = (addr, new_channel_name)
        self.user_manager.update_user_channel(user.id, new_channel_name)
        
        try:
            # 获取新频道的历史消息
            history = self._get_channel_messages(new_channel_name)
            self.socket.sendto(
                json.dumps({
                    "type": "history",
                    "messages": [m.to_dict() for m in history]
                }).encode(),
                addr
            )
            
            # 在旧频道广播离开消息
            self._broadcast_message(
                "system",
                f"{username} 离开了频道",
                old_channel_name
            )
            
            # 在新频道广播加入消息
            self._broadcast_message(
                "system",
                f"{username} 加入了频道",
                new_channel_name
            )
            
            # 发送频道信息确认
            channel_info = {
                "type": "channel_joined",
                "channel": new_channel.to_dict()
            }
            self.socket.sendto(json.dumps(channel_info).encode(), addr)
            
            logging.info(f"用户 {username} 从 {old_channel_name} 切换到 {new_channel_name}")
            
        except Exception as e:
            logging.error(f"处理加入频道请求时出错: {str(e)}")
            # 出错时回退到原频道
            self.clients[username] = (addr, old_channel_name)
            self.user_manager.update_user_channel(user.id, old_channel_name)
    def run(self):
        """运行服务器主循环"""
        while True:
            try:
                data, addr = self.socket.recvfrom(SERVER_CONFIG['buffer_size'])
                message = json.loads(data.decode())
                command = message.get("command")
                
                if command == "auth":
                    self._handle_auth(message, addr)
                elif command == "register":  # 新增注册处理
                    username = message["username"]
                    password = message["password"]
                    
                    if self._register_user(username, password):
                        self.socket.sendto(b"REGISTER_SUCCESS", addr)
                    else:
                        self.socket.sendto(b"REGISTER_FAILED", addr)
                elif command == "message":
                    self._handle_message(message)
                elif command == "heartbeat":
                    self._handle_heartbeat(message)
                elif command == "join_channel":
                    self._handle_join_channel(message)
                else:
                    logging.warning(f"未知命令: {command}")
                
            except json.JSONDecodeError as e:
                logging.error(f"JSON解析错误: {str(e)}")
            except Exception as e:
                logging.error(f"处理消息错误: {str(e)}")
                continue

if __name__ == "__main__":
    try:
        server = ChatServer()
        server.run()
    except Exception as e:
        logging.error(f"服务器启动错误: {str(e)}")