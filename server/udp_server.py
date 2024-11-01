import socket
import redis
import threading
import json
import time
from datetime import datetime

# 初始化 Redis 客户端
r = redis.Redis(host='localhost', port=6379, db=0)

class ChatServer:
    def __init__(self, host='localhost', port=12345):
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
        else:
            for client_addr in self.clients.values():
                self.socket.sendto(f"{username}: {msg_text}".encode('utf-8'), client_addr)

    def run(self):
        while True:
            data, addr = self.socket.recvfrom(1024)
            message = json.loads(data.decode('utf-8'))
            command = message.get("command")

            if command == "join":
                username = message.get("username")
                self.clients[username] = addr
                self.last_heartbeat[username] = time.time()
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
                    print(f"{username} is offline")
                    del self.clients[username]
                    del self.last_heartbeat[username]
            time.sleep(10)

if __name__ == "__main__":
    server = ChatServer()
    server.run()