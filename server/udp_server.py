import socket
import redis
import threading
import json
import time
from datetime import datetime
import hashlib

# 初始化 Redis 客户端
r = redis.Redis(host='localhost', port=6379, db=0)

class ChatServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.server_address = (host, port)
        self.clients = {}
        self.last_heartbeat = {}
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.server_address)
        print("Server started on", host, ":", port)
        
        # Start a thread to monitor client heartbeats
        monitor_thread = threading.Thread(target=self.monitor_clients)
        monitor_thread.daemon = True
        monitor_thread.start()
    

    def register_user(self, username, password):
        if r.hexists("users", username):
            return False  # 用户名已存在
        # 保存加密后的密码
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        r.hset("users", username, hashed_password)
        return True
    
    def authenticate_user(self, username, password):
        stored_password = r.hget("users", username)
        if stored_password is None:
            return False  # 用户名不存在
        return stored_password.decode('utf-8') == hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    
    def handle_message(self, data, addr):
        message = json.loads(data.decode('utf-8'))
        username = message.get("username")
        msg_text = message.get("message")
        recipient = message.get("recipient")
        timestamp = datetime.now().timestamp()
    
        # 保存消息到 Redis，按频道记录
        r.lpush("chat_history", json.dumps({"username": username, "message": msg_text, "timestamp": timestamp}))
    
        # 解析私聊和广播
        if recipient:
            if recipient in self.clients:
                self.socket.sendto(f"{username} (private): {msg_text}".encode('utf-8'), self.clients[recipient])
                self.socket.sendto(f"{username} (private): {msg_text}".encode('utf-8'), addr)
        else:
            for client_addr in self.clients.values():
                self.socket.sendto(f"{username}: {msg_text}".encode('utf-8'), client_addr)

    def run(self):
        while True:
            data, addr = self.socket.recvfrom(1024)
            message = json.loads(data.decode('utf-8'))
            command = message.get("command")
            if command == "register":
                username = message.get("username")
                password = message.get("password")
                if self.register_user(username, password):
                    self.socket.sendto(b"Registration successful", addr)
                else:
                    self.socket.sendto(b"Username already taken", addr)
            elif command == "login":
                username = message.get("username")
                password = message.get("password")
                if self.authenticate_user(username, password):
                    self.clients[username] = addr
                    self.last_heartbeat[username] = time.time()
                    self.socket.sendto(b"Login successful", addr)
                else:
                    self.socket.sendto(b"Invalid username or password", addr)
            if command == "join":
                username = message.get("username")
                self.clients[username] = addr
                self.last_heartbeat[username] = time.time()
                for client_addr in self.clients.values():
                    if client_addr != addr:
                        self.socket.sendto(f"{username} 加入聊天".encode('utf-8'), client_addr)
                print(f"{username} joined from {addr}")
            elif command == "message":
                self.handle_message(data, addr)
            elif command == "history":
                history = r.lrange("chat_history", 0, -1)
                history = [json.loads(item) for item in history]
                self.socket.sendto(f"[History]{json.dumps(history)}".encode('utf-8'), addr)
            elif command == "heartbeat":
                username = message.get("username")
                self.last_heartbeat[username] = time.time()

    def monitor_clients(self):
        while True:
            current_time = time.time()
            for username, last_time in list(self.last_heartbeat.items()):
                if current_time - last_time > 30:  # 超过30秒未收到心跳包，认为客户端掉线
                    for client_addr in self.clients.values():
                        if client_addr != self.clients[username]:
                            self.socket.sendto(f"{username} 离开了我们".encode('utf-8'), client_addr)
                    print(f"{username} is offline")
                    del self.clients[username]
                    del self.last_heartbeat[username]
            time.sleep(10)

if __name__ == "__main__":
    server = ChatServer()
    server.run()